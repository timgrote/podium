import os
import re
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..database import get_db
from ..models.invoice import InvoiceUpdate

router = APIRouter()


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
    """Export the invoice's Google Sheet as a PDF."""
    from ..google_sheets import export_sheet_as_pdf

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

    # Save PDF locally
    invoice_dir = os.path.join(settings.upload_dir, "invoices")
    os.makedirs(invoice_dir, exist_ok=True)
    filename = f"{invoice['invoice_number']}.pdf"
    pdf_path = os.path.join(invoice_dir, filename)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    relative_path = f"/uploads/invoices/{filename}"
    now = datetime.now().isoformat()
    db.execute(
        "UPDATE invoices SET pdf_path = ?, updated_at = ? WHERE id = ?",
        (relative_path, now, invoice_id),
    )
    db.commit()

    return {"success": True, "pdf_path": relative_path}


@router.post("/{invoice_id}/send")
def send_invoice(invoice_id: str, db: sqlite3.Connection = Depends(get_db)):
    """Export PDF and email the invoice to the client."""
    from ..google_sheets import export_sheet_as_pdf, send_invoice_email

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

    # 1. Export PDF
    spreadsheet_id = _extract_spreadsheet_id(invoice["data_path"])
    pdf_bytes = export_sheet_as_pdf(spreadsheet_id)

    invoice_dir = os.path.join(settings.upload_dir, "invoices")
    os.makedirs(invoice_dir, exist_ok=True)
    filename = f"{invoice['invoice_number']}.pdf"
    pdf_path = os.path.join(invoice_dir, filename)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    relative_path = f"/uploads/invoices/{filename}"

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
        (now, relative_path, now, invoice_id),
    )
    db.commit()

    return {"success": True, "sent_to": to_emails, "pdf_path": relative_path}

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

    now = datetime.now().isoformat()
    db.execute("UPDATE invoices SET deleted_at = ? WHERE id = ?", (now, invoice_id))
    db.commit()
    return {"success": True}


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
