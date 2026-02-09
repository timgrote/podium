import logging
import re
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..models.invoice import InvoiceUpdate
from ..utils import generate_id, next_invoice_number

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Lookup by invoice_number (used by frontend) ---

@router.get("/by-number/{invoice_number}")
def get_invoice_by_number(invoice_number: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT * FROM invoices WHERE invoice_number = ? AND deleted_at IS NULL",
        (invoice_number,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = dict(row)
    line_items = db.execute(
        "SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY sort_order",
        (invoice["id"],),
    ).fetchall()
    invoice["line_items"] = [dict(li) for li in line_items]
    return invoice


@router.get("/{invoice_id}")
def get_invoice(invoice_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT * FROM invoices WHERE id = ? AND deleted_at IS NULL", (invoice_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = dict(row)
    line_items = db.execute(
        "SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY sort_order",
        (invoice_id,),
    ).fetchall()
    invoice["line_items"] = [dict(li) for li in line_items]
    return invoice


def _extract_spreadsheet_id(data_path: str) -> str:
    """Extract Google Sheets spreadsheet ID from a URL or raw ID."""
    if not data_path:
        raise ValueError("No sheet URL stored for this invoice")
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", data_path)
    if match:
        return match.group(1)
    return data_path


# --- Google Sheets integration endpoints ---


@router.post("/{invoice_id}/export-pdf")
def export_invoice_pdf(invoice_id: str, db: sqlite3.Connection = Depends(get_db)):
    """Export the invoice's Google Sheet as a PDF to Google Drive."""
    from ..google_sheets import export_sheet_as_pdf, upload_pdf_to_drive

    invoice = db.execute(
        "SELECT * FROM invoices WHERE id = ? AND deleted_at IS NULL", (invoice_id,)
    ).fetchone()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = dict(invoice)
    if not invoice.get("data_path"):
        raise HTTPException(status_code=400, detail="No Google Sheet linked to this invoice")

    spreadsheet_id = _extract_spreadsheet_id(invoice["data_path"])
    pdf_bytes = export_sheet_as_pdf(spreadsheet_id)

    # Upload PDF to Google Drive
    folder_row = db.execute(
        "SELECT value FROM company_settings WHERE key = 'invoice_drive_folder_id'"
    ).fetchone()
    folder_id = folder_row["value"] if folder_row else ""

    filename = f"{invoice['invoice_number']}.pdf"
    drive_url = upload_pdf_to_drive(pdf_bytes, filename, folder_id)

    now = datetime.now().isoformat()
    db.execute(
        "UPDATE invoices SET pdf_path = ?, updated_at = ? WHERE id = ?",
        (drive_url, now, invoice_id),
    )
    db.commit()

    return {"success": True, "pdf_path": drive_url}


@router.post("/{invoice_id}/finalize")
def finalize_invoice(invoice_id: str, db: sqlite3.Connection = Depends(get_db)):
    """Finalize an invoice: read amounts from Google Sheet, snapshot to DB, generate PDF."""
    from ..google_sheets import export_sheet_as_pdf, read_invoice_sheet, upload_pdf_to_drive

    invoice = db.execute(
        "SELECT * FROM invoices WHERE id = ? AND deleted_at IS NULL", (invoice_id,)
    ).fetchone()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = dict(invoice)

    if not invoice.get("data_path") or "google.com" not in invoice["data_path"]:
        raise HTTPException(status_code=400, detail="No Google Sheet linked to this invoice")

    spreadsheet_id = _extract_spreadsheet_id(invoice["data_path"])

    # 1. Read current task amounts from Google Sheet
    sheet_tasks = read_invoice_sheet(spreadsheet_id)

    # 2. Update invoice_line_items in DB with actual Sheet values
    existing_items = db.execute(
        "SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY sort_order",
        (invoice_id,),
    ).fetchall()

    now = datetime.now().isoformat()
    total_due = 0.0

    for i, item in enumerate(existing_items):
        if i < len(sheet_tasks):
            sheet_row = sheet_tasks[i]
            amount = sheet_row.get("amount", 0) or 0
            quantity = sheet_row.get("quantity", 0) or 0
            previous_billing = sheet_row.get("previous_billing", 0) or 0
            total_due += amount
            db.execute(
                "UPDATE invoice_line_items SET quantity = ?, amount = ?, previous_billing = ? WHERE id = ?",
                (quantity, amount, previous_billing, item["id"]),
            )

    # 3. Update invoice total
    db.execute(
        "UPDATE invoices SET total_due = ?, updated_at = ? WHERE id = ?",
        (total_due, now, invoice_id),
    )

    # 4. Export Google Sheet as PDF
    pdf_bytes = export_sheet_as_pdf(spreadsheet_id)

    # 5. Upload PDF to Google Drive
    folder_row = db.execute(
        "SELECT value FROM company_settings WHERE key = 'invoice_drive_folder_id'"
    ).fetchone()
    folder_id = folder_row["value"] if folder_row else ""

    filename = f"{invoice['invoice_number']}.pdf"
    drive_url = upload_pdf_to_drive(pdf_bytes, filename, folder_id)

    # 6. Update invoice: set pdf_path, keep data_path as sheet URL
    db.execute(
        "UPDATE invoices SET pdf_path = ?, updated_at = ? WHERE id = ?",
        (drive_url, now, invoice_id),
    )
    db.commit()

    logger.info("Finalized invoice %s: total=$%.2f, pdf=%s", invoice["invoice_number"], total_due, drive_url)
    return {"success": True, "total_due": total_due, "pdf_path": drive_url}


@router.post("/{invoice_id}/send")
def send_invoice(invoice_id: str, db: sqlite3.Connection = Depends(get_db)):
    """Export PDF and email the invoice to the client."""
    from ..google_sheets import export_sheet_as_pdf, send_invoice_email, upload_pdf_to_drive

    invoice = db.execute(
        "SELECT * FROM invoices WHERE id = ? AND deleted_at IS NULL", (invoice_id,)
    ).fetchone()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = dict(invoice)
    if not invoice.get("data_path"):
        raise HTTPException(status_code=400, detail="No Google Sheet linked to this invoice")

    # Get project and client info
    project = db.execute(
        "SELECT p.*, c.name as client_name, c.email as client_email, c.company as client_company "
        "FROM projects p LEFT JOIN clients c ON p.client_id = c.id "
        "WHERE p.id = ?",
        (invoice["project_id"],),
    ).fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project = dict(project)

    # Get company info
    company_name = ""
    company_email = ""
    for key in ("company_name", "company_email"):
        row = db.execute(
            "SELECT value FROM company_settings WHERE key = ?", (key,)
        ).fetchone()
        if row:
            if key == "company_name":
                company_name = row["value"]
            else:
                company_email = row["value"]

    # 1. Export PDF and upload to Google Drive
    spreadsheet_id = _extract_spreadsheet_id(invoice["data_path"])
    pdf_bytes = export_sheet_as_pdf(spreadsheet_id)

    folder_row = db.execute(
        "SELECT value FROM company_settings WHERE key = 'invoice_drive_folder_id'"
    ).fetchone()
    folder_id = folder_row["value"] if folder_row else ""

    filename = f"{invoice['invoice_number']}.pdf"
    drive_url = upload_pdf_to_drive(pdf_bytes, filename, folder_id)

    # 2. Determine recipients
    to_emails = []
    if project.get("client_email"):
        to_emails.append(project["client_email"])
    if not to_emails:
        raise HTTPException(
            status_code=400,
            detail="No client email address found. Add an email to the client record.",
        )

    # 3. Build email
    subject = f"Invoice {invoice['invoice_number']} from {company_name}" if company_name else f"Invoice {invoice['invoice_number']}"
    body = (
        f"Please find attached invoice {invoice['invoice_number']} "
        f"for {project['name']}.\n\n"
        f"Amount due: ${invoice['total_due']:,.2f}\n\n"
    )
    if company_name:
        body += f"Thank you,\n{company_name}\n"
    if company_email:
        body += f"{company_email}\n"

    # 4. Send
    send_invoice_email(
        to_emails=to_emails,
        subject=subject,
        body_text=body,
        pdf_bytes=pdf_bytes,
        pdf_filename=filename,
        from_email=company_email or None,
    )

    # 5. Update invoice status
    now = datetime.now().isoformat()
    db.execute(
        "UPDATE invoices SET sent_status = 'sent', sent_at = ?, pdf_path = ?, updated_at = ? WHERE id = ?",
        (now, drive_url, now, invoice_id),
    )
    db.commit()

    return {"success": True, "sent_to": to_emails, "pdf_path": drive_url}

@router.post("/{invoice_id}/create-next")
def create_next_invoice(invoice_id: str, db: sqlite3.Connection = Depends(get_db)):
    """Create the next invoice in the chain, carrying forward previous billing."""
    invoice = db.execute(
        "SELECT * FROM invoices WHERE id = ? AND deleted_at IS NULL", (invoice_id,)
    ).fetchone()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = dict(invoice)

    if invoice["sent_status"] != "sent":
        raise HTTPException(status_code=400, detail="Invoice must be sent before creating next")

    # Read line items from the current (finalized) invoice
    line_items = db.execute(
        "SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY sort_order",
        (invoice_id,),
    ).fetchall()
    if not line_items:
        raise HTTPException(status_code=400, detail="No line items on current invoice")

    project_id = invoice["project_id"]
    contract_id = invoice["contract_id"]
    now = datetime.now().isoformat()

    # Determine new invoice number
    new_invoice_number = next_invoice_number(db, project_id)

    new_inv_id = generate_id("inv-")

    # Build new line items: previous_billing = old previous_billing + old amount, amount = 0
    new_line_items = []
    for li in line_items:
        li = dict(li)
        new_previous_billing = (li.get("previous_billing") or 0) + (li.get("amount") or 0)
        new_line_items.append({
            "name": li["name"],
            "description": li.get("description"),
            "unit_price": li.get("unit_price", 0),
            "quantity": 0,
            "amount": 0,
            "previous_billing": new_previous_billing,
        })

    # Update contract_tasks billing totals based on the finalized invoice amounts
    if contract_id:
        for li in line_items:
            li = dict(li)
            # Find matching contract task by name
            task = db.execute(
                "SELECT * FROM contract_tasks WHERE contract_id = ? AND name = ?",
                (contract_id, li["name"]),
            ).fetchone()
            if task:
                new_billed = (li.get("previous_billing") or 0) + (li.get("amount") or 0)
                new_percent = (new_billed / task["amount"] * 100) if task["amount"] > 0 else 0
                db.execute(
                    "UPDATE contract_tasks SET billed_amount = ?, billed_percent = ?, updated_at = ? WHERE id = ?",
                    (new_billed, new_percent, now, task["id"]),
                )

    # Create new invoice record
    db.execute(
        "INSERT INTO invoices (id, invoice_number, project_id, contract_id, previous_invoice_id, "
        "type, total_due, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'task', 0, ?, ?)",
        (new_inv_id, new_invoice_number, project_id, contract_id, invoice_id, now, now),
    )

    # Create new line items
    for i, li in enumerate(new_line_items):
        li_id = generate_id("li-")
        db.execute(
            "INSERT INTO invoice_line_items (id, invoice_id, sort_order, name, description, "
            "quantity, unit_price, amount, previous_billing, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (li_id, new_inv_id, i + 1, li["name"], li["description"],
             li["quantity"], li["unit_price"], li["amount"], li["previous_billing"], now),
        )

    # Set as current invoice on project
    db.execute(
        "UPDATE projects SET current_invoice_id = ?, updated_at = ? WHERE id = ?",
        (new_inv_id, now, project_id),
    )
    db.commit()

    # Try to create Google Sheet for new invoice
    sheet_url = None
    try:
        from ..google_sheets import create_invoice_sheet

        project_row = db.execute(
            "SELECT p.*, c.name as client_name, c.company as client_company "
            "FROM projects p LEFT JOIN clients c ON p.client_id = c.id "
            "WHERE p.id = ?",
            (project_id,),
        ).fetchone()

        company_email = ""
        drive_folder_id = ""
        template_id = ""
        for key in ("company_email", "invoice_drive_folder_id", "invoice_template_id"):
            row = db.execute(
                "SELECT value FROM company_settings WHERE key = ?", (key,)
            ).fetchone()
            if row and row["value"]:
                if key == "company_email":
                    company_email = row["value"]
                elif key == "invoice_drive_folder_id":
                    drive_folder_id = row["value"]
                elif key == "invoice_template_id":
                    template_id = row["value"]

        client_display = (
            dict(project_row).get("client_company")
            or dict(project_row).get("client_name")
            or ""
        )

        sheet_url = create_invoice_sheet(
            invoice_number=new_invoice_number,
            project_name=project_row["name"],
            project_id=project_id,
            invoice_date=now[:10],
            company_email=company_email,
            client_name=client_display,
            tasks=new_line_items,
            folder_id=drive_folder_id,
            template_id=template_id,
        )
        db.execute(
            "UPDATE invoices SET data_path = ?, updated_at = ? WHERE id = ?",
            (sheet_url, datetime.now().isoformat(), new_inv_id),
        )
        db.commit()
    except FileNotFoundError:
        logger.info("Google Sheet creation skipped: no credentials configured")
    except Exception as e:
        logger.error("Google Sheet creation failed: %s", e)
        sheet_url = None

    new_invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (new_inv_id,)).fetchone()
    logger.info("Created next invoice %s (chain from %s)", new_invoice_number, invoice["invoice_number"])
    result = dict(new_invoice)
    if not result.get("data_path"):
        result["_warning"] = "Invoice created but Google Sheet could not be generated"
    return result


@router.patch("/{invoice_id}")
def update_invoice(
    invoice_id: str,
    data: InvoiceUpdate,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM invoices WHERE id = ? AND deleted_at IS NULL", (invoice_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Invoice not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return dict(existing)

    now = datetime.now().isoformat()
    updates["updated_at"] = now

    # Auto-set timestamps based on status changes
    if "sent_status" in updates and updates["sent_status"] == "sent":
        updates["sent_at"] = now
    if "paid_status" in updates and updates["paid_status"] == "paid":
        updates["paid_at"] = now

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [invoice_id]
    db.execute(f"UPDATE invoices SET {set_clause} WHERE id = ?", values)
    db.commit()

    row = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    return dict(row)


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: str, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM invoices WHERE id = ? AND deleted_at IS NULL", (invoice_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Invoice not found")

    inv = dict(existing)
    now = datetime.now().isoformat()

    # Reverse billing on contract tasks for this invoice's line items
    line_items = db.execute(
        "SELECT * FROM invoice_line_items WHERE invoice_id = ?", (invoice_id,)
    ).fetchall()
    for li in line_items:
        li = dict(li)
        if not li.get("name"):
            continue
        # Find matching contract task and subtract this invoice's billing
        if inv.get("contract_id"):
            tasks = db.execute(
                "SELECT * FROM contract_tasks WHERE contract_id = ? AND name = ?",
                (inv["contract_id"], li["name"]),
            ).fetchall()
            for task in tasks:
                task = dict(task)
                new_billed = max(0, (task["billed_amount"] or 0) - (li.get("amount") or 0))
                new_percent = (new_billed / task["amount"] * 100) if task["amount"] > 0 else 0
                db.execute(
                    "UPDATE contract_tasks SET billed_amount = ?, billed_percent = ?, updated_at = ? WHERE id = ?",
                    (new_billed, new_percent, now, task["id"]),
                )

    # Soft-delete the invoice
    db.execute("UPDATE invoices SET deleted_at = ? WHERE id = ?", (now, invoice_id))

    # Clear current_invoice_id if this was the current invoice
    if inv.get("project_id"):
        db.execute(
            "UPDATE projects SET current_invoice_id = NULL WHERE id = ? AND current_invoice_id = ?",
            (inv["project_id"], invoice_id),
        )

    db.commit()
    return {"success": True}
