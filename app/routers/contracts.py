import logging
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..models.contract import ContractCreate, ContractTaskCreate, ContractTaskUpdate
from ..models.invoice import InvoiceFromContract
from ..utils import generate_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{contract_id}")
def get_contract(contract_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT * FROM contracts WHERE id = ? AND deleted_at IS NULL", (contract_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")

    contract = dict(row)
    tasks = db.execute(
        "SELECT * FROM contract_tasks WHERE contract_id = ? ORDER BY sort_order",
        (contract_id,),
    ).fetchall()
    contract["tasks"] = [dict(t) for t in tasks]
    return contract


@router.post("", status_code=201)
def create_contract(data: ContractCreate, db: sqlite3.Connection = Depends(get_db)):
    # Verify project exists
    project = db.execute(
        "SELECT id FROM projects WHERE id = ? AND deleted_at IS NULL", (data.project_id,)
    ).fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now().isoformat()
    contract_id = generate_id("con-")
    db.execute(
        "INSERT INTO contracts (id, project_id, total_amount, signed_at, file_path, notes, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (contract_id, data.project_id, data.total_amount, data.signed_at, data.file_path, data.notes, now, now),
    )
    db.commit()
    return get_contract(contract_id, db)


@router.delete("/{contract_id}")
def delete_contract(contract_id: str, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM contracts WHERE id = ? AND deleted_at IS NULL", (contract_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Contract not found")

    now = datetime.now().isoformat()
    db.execute("UPDATE contracts SET deleted_at = ? WHERE id = ?", (now, contract_id))
    db.commit()
    return {"success": True}


# --- Contract Tasks ---

@router.post("/{contract_id}/tasks")
def add_contract_task(
    contract_id: str,
    data: ContractTaskCreate,
    db: sqlite3.Connection = Depends(get_db),
):
    contract = db.execute(
        "SELECT * FROM contracts WHERE id = ? AND deleted_at IS NULL", (contract_id,)
    ).fetchone()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    now = datetime.now().isoformat()
    task_id = generate_id("ctask-")

    # Get next sort_order
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) as max_order FROM contract_tasks WHERE contract_id = ?",
        (contract_id,),
    ).fetchone()["max_order"]

    db.execute(
        "INSERT INTO contract_tasks (id, contract_id, sort_order, name, description, amount, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (task_id, contract_id, max_order + 1, data.name, data.description, data.amount, now, now),
    )

    # Update contract total
    _update_contract_total(db, contract_id)
    db.commit()

    return get_contract(contract_id, db)


@router.patch("/{contract_id}/tasks/{task_id}")
def update_contract_task(
    contract_id: str,
    task_id: str,
    data: ContractTaskUpdate,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM contract_tasks WHERE id = ? AND contract_id = ?",
        (task_id, contract_id),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return get_contract(contract_id, db)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]
    db.execute(f"UPDATE contract_tasks SET {set_clause} WHERE id = ?", values)

    _update_contract_total(db, contract_id)
    db.commit()
    return get_contract(contract_id, db)


@router.delete("/{contract_id}/tasks/{task_id}")
def delete_contract_task(
    contract_id: str,
    task_id: str,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM contract_tasks WHERE id = ? AND contract_id = ?",
        (task_id, contract_id),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    db.execute("DELETE FROM contract_tasks WHERE id = ?", (task_id,))
    _update_contract_total(db, contract_id)
    db.commit()
    return {"success": True}


# --- Invoice from Contract ---

@router.post("/{contract_id}/invoices")
def create_invoice_from_contract(
    contract_id: str,
    data: InvoiceFromContract,
    db: sqlite3.Connection = Depends(get_db),
):
    contract = db.execute(
        "SELECT * FROM contracts WHERE id = ? AND deleted_at IS NULL", (contract_id,)
    ).fetchone()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    project_id = contract["project_id"]
    now = datetime.now().isoformat()
    inv_id = generate_id("inv-")

    # Determine invoice number
    count = db.execute(
        "SELECT COUNT(*) as cnt FROM invoices WHERE project_id = ?", (project_id,)
    ).fetchone()["cnt"]
    invoice_number = f"{project_id}-{count + 1}"

    # Find previous invoice in chain
    prev_invoice = db.execute(
        "SELECT id FROM invoices WHERE project_id = ? AND contract_id = ? AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1",
        (project_id, contract_id),
    ).fetchone()
    previous_invoice_id = prev_invoice["id"] if prev_invoice else None

    # Calculate line items from tasks
    total_due = 0.0
    line_items = []

    for task_spec in data.tasks:
        task_id = task_spec["task_id"]
        percent_this = task_spec["percent_this_invoice"]

        task = db.execute(
            "SELECT * FROM contract_tasks WHERE id = ? AND contract_id = ?",
            (task_id, contract_id),
        ).fetchone()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        current_billing = task["amount"] * percent_this / 100
        previous_billing = task["billed_amount"] or 0

        line_items.append({
            "task_id": task_id,
            "name": task["name"],
            "description": task["description"],
            "unit_price": task["amount"],
            "quantity": percent_this,
            "amount": current_billing,
            "previous_billing": previous_billing,
        })
        total_due += current_billing

        # Update task billed amounts
        new_billed = previous_billing + current_billing
        new_percent = (new_billed / task["amount"] * 100) if task["amount"] > 0 else 0
        db.execute(
            "UPDATE contract_tasks SET billed_amount = ?, billed_percent = ?, updated_at = ? WHERE id = ?",
            (new_billed, new_percent, now, task_id),
        )

    # Create invoice
    db.execute(
        "INSERT INTO invoices (id, invoice_number, project_id, contract_id, previous_invoice_id, "
        "type, total_due, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'task', ?, ?, ?)",
        (inv_id, invoice_number, project_id, contract_id, previous_invoice_id, total_due, now, now),
    )

    # Create line items
    for i, li in enumerate(line_items):
        li_id = generate_id("li-")
        db.execute(
            "INSERT INTO invoice_line_items (id, invoice_id, sort_order, name, description, "
            "quantity, unit_price, amount, previous_billing, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (li_id, inv_id, i + 1, li["name"], li["description"],
             li["quantity"], li["unit_price"], li["amount"], li["previous_billing"], now),
        )

    # Set as current invoice on project
    db.execute("UPDATE projects SET current_invoice_id = ? WHERE id = ?", (inv_id, project_id))

    db.commit()

    # Try to create Google Sheet for this invoice
    sheet_url = None
    try:
        from ..google_sheets import create_invoice_sheet

        project = db.execute(
            "SELECT p.*, c.name as client_name, c.company as client_company, "
            "c.address as client_address "
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

        # Use PM email from request or project, fall back to company email
        pm_email = data.pm_email or dict(project).get("pm_email") or company_email

        client_display = (
            dict(project).get("client_company")
            or dict(project).get("client_name")
            or ""
        )

        p_dict = dict(project)
        sheet_url = create_invoice_sheet(
            invoice_number=invoice_number,
            project_name=project["name"],
            project_id=project_id,
            invoice_date=now[:10],
            company_email=pm_email,
            client_name=client_display,
            tasks=line_items,
            folder_id=drive_folder_id,
            template_id=template_id,
            client_contact=p_dict.get("client_name") or "",
            client_company=p_dict.get("client_company") or "",
            client_address=p_dict.get("client_address") or "",
            client_project_number=p_dict.get("client_project_number") or "",
        )
        db.execute(
            "UPDATE invoices SET data_path = ?, updated_at = ? WHERE id = ?",
            (sheet_url, datetime.now().isoformat(), inv_id),
        )
        db.commit()
    except Exception as e:
        logger.warning("Google Sheet creation skipped: %s", e)

    invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (inv_id,)).fetchone()
    return dict(invoice)


def _update_contract_total(db: sqlite3.Connection, contract_id: str):
    total = db.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM contract_tasks WHERE contract_id = ?",
        (contract_id,),
    ).fetchone()["total"]
    db.execute(
        "UPDATE contracts SET total_amount = ?, updated_at = ? WHERE id = ?",
        (total, datetime.now().isoformat(), contract_id),
    )
