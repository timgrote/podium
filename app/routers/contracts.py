import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..models.contract import ContractCreate, ContractTaskCreate, ContractTaskUpdate, ContractUpdate
from ..models.invoice import InvoiceFromContract
from ..utils import generate_id, next_invoice_number

logger = logging.getLogger(__name__)

router = APIRouter()


def _compute_task_billing(db, contract_id: str, tasks: list[dict]) -> list[dict]:
    """Compute billed_amount and billed_percent from active invoice line items."""
    # Sum line item amounts per task name from non-deleted invoices
    rows = db.execute(
        "SELECT li.name, COALESCE(SUM(li.amount), 0) as total_billed "
        "FROM invoice_line_items li "
        "JOIN invoices inv ON li.invoice_id = inv.id "
        "WHERE inv.contract_id = %s AND inv.deleted_at IS NULL "
        "GROUP BY li.name",
        (contract_id,),
    ).fetchall()
    billed_by_name = {r["name"]: float(r["total_billed"]) for r in rows}

    for task in tasks:
        billed = billed_by_name.get(task["name"], 0)
        task["billed_amount"] = billed
        task["billed_percent"] = (billed / float(task["amount"]) * 100) if task["amount"] else 0
    return tasks


@router.get("/{contract_id}")
def get_contract(contract_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM contracts WHERE id = %s AND deleted_at IS NULL", (contract_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")

    contract = dict(row)
    tasks = db.execute(
        "SELECT * FROM contract_tasks WHERE contract_id = %s ORDER BY sort_order",
        (contract_id,),
    ).fetchall()
    contract["tasks"] = _compute_task_billing(db, contract_id, [dict(t) for t in tasks])
    return contract


@router.post("", status_code=201)
def create_contract(data: ContractCreate, db=Depends(get_db)):
    # Verify project exists
    project = db.execute(
        "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL", (data.project_id,)
    ).fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now().isoformat()
    contract_id = generate_id("con-")

    # If tasks provided, compute total from tasks
    total = data.total_amount
    if data.tasks:
        total = sum(t.get("amount", 0) for t in data.tasks)

    db.execute(
        "INSERT INTO contracts (id, project_id, total_amount, signed_at, file_path, notes, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (contract_id, data.project_id, total, data.signed_at, data.file_path, data.notes, now, now),
    )

    # Create inline tasks if provided
    if data.tasks:
        for i, task in enumerate(data.tasks):
            task_id = generate_id("ctask-")
            db.execute(
                "INSERT INTO contract_tasks (id, contract_id, sort_order, name, description, amount, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (task_id, contract_id, i + 1, task["name"], task.get("description"), task.get("amount", 0), now, now),
            )

    db.commit()
    return get_contract(contract_id, db)


@router.patch("/{contract_id}")
def update_contract(contract_id: str, data: ContractUpdate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM contracts WHERE id = %s AND deleted_at IS NULL", (contract_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Contract not found")

    now = datetime.now().isoformat()

    # Update contract-level fields
    field_updates = {}
    if data.signed_at is not None:
        field_updates["signed_at"] = data.signed_at
    if data.file_path is not None:
        field_updates["file_path"] = data.file_path
    if data.notes is not None:
        field_updates["notes"] = data.notes

    if field_updates:
        field_updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = %s" for k in field_updates)
        values = list(field_updates.values()) + [contract_id]
        db.execute(f"UPDATE contracts SET {set_clause} WHERE id = %s", values)

    # Replace tasks if provided — delete existing and re-create
    if data.tasks is not None:
        db.execute("DELETE FROM contract_tasks WHERE contract_id = %s", (contract_id,))
        for i, task in enumerate(data.tasks):
            task_id = generate_id("ctask-")
            db.execute(
                "INSERT INTO contract_tasks (id, contract_id, sort_order, name, description, amount, "
                "billed_amount, billed_percent, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (task_id, contract_id, i + 1, task["name"], task.get("description"),
                 task.get("amount", 0), task.get("billed_amount", 0), task.get("billed_percent", 0),
                 now, now),
            )
        _update_contract_total(db, contract_id)

    db.commit()
    return get_contract(contract_id, db)


@router.delete("/{contract_id}")
def delete_contract(contract_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM contracts WHERE id = %s AND deleted_at IS NULL", (contract_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Contract not found")

    now = datetime.now().isoformat()
    db.execute("UPDATE contracts SET deleted_at = %s WHERE id = %s", (now, contract_id))
    db.commit()
    return {"success": True}


# --- Contract Tasks ---

@router.post("/{contract_id}/tasks")
def add_contract_task(
    contract_id: str,
    data: ContractTaskCreate,
    db=Depends(get_db),
):
    contract = db.execute(
        "SELECT * FROM contracts WHERE id = %s AND deleted_at IS NULL", (contract_id,)
    ).fetchone()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    now = datetime.now().isoformat()
    task_id = generate_id("ctask-")

    # Get next sort_order
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) as max_order FROM contract_tasks WHERE contract_id = %s",
        (contract_id,),
    ).fetchone()["max_order"]

    db.execute(
        "INSERT INTO contract_tasks (id, contract_id, sort_order, name, description, amount, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
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
    db=Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM contract_tasks WHERE id = %s AND contract_id = %s",
        (task_id, contract_id),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return get_contract(contract_id, db)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [task_id]
    db.execute(f"UPDATE contract_tasks SET {set_clause} WHERE id = %s", values)

    _update_contract_total(db, contract_id)
    db.commit()
    return get_contract(contract_id, db)


@router.delete("/{contract_id}/tasks/{task_id}")
def delete_contract_task(
    contract_id: str,
    task_id: str,
    db=Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM contract_tasks WHERE id = %s AND contract_id = %s",
        (task_id, contract_id),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    db.execute("DELETE FROM contract_tasks WHERE id = %s", (task_id,))
    _update_contract_total(db, contract_id)
    db.commit()
    return {"success": True}


# --- Invoice from Contract ---

@router.post("/{contract_id}/invoices")
def create_invoice_from_contract(
    contract_id: str,
    data: InvoiceFromContract,
    db=Depends(get_db),
):
    contract = db.execute(
        "SELECT * FROM contracts WHERE id = %s AND deleted_at IS NULL", (contract_id,)
    ).fetchone()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    project_id = contract["project_id"]
    now = datetime.now().isoformat()
    inv_id = generate_id("inv-")

    # Determine invoice number (use override if provided)
    invoice_number = data.invoice_number or next_invoice_number(db, project_id)

    # Find previous invoice in chain
    prev_invoice = db.execute(
        "SELECT id FROM invoices WHERE project_id = %s AND contract_id = %s AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1",
        (project_id, contract_id),
    ).fetchone()
    previous_invoice_id = prev_invoice["id"] if prev_invoice else None

    # Calculate line items from tasks
    total_due = Decimal(0)
    line_items = []

    for task_spec in data.tasks:
        task_id = task_spec["task_id"]
        percent_this = task_spec["percent_this_invoice"]

        task = db.execute(
            "SELECT * FROM contract_tasks WHERE id = %s AND contract_id = %s",
            (task_id, contract_id),
        ).fetchone()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        current_billing = task["amount"] * percent_this / 100

        # Compute previous billing from active invoices (not stored column)
        prev_row = db.execute(
            "SELECT COALESCE(SUM(li.amount), 0) as total "
            "FROM invoice_line_items li JOIN invoices inv ON li.invoice_id = inv.id "
            "WHERE inv.contract_id = %s AND inv.deleted_at IS NULL AND li.name = %s",
            (contract_id, task["name"]),
        ).fetchone()
        previous_billing = float(prev_row["total"])

        line_items.append({
            "task_id": task_id,
            "name": task["name"],
            "description": task["description"],
            "unit_price": float(task["amount"]),
            "quantity": float(percent_this),
            "amount": float(current_billing),
            "previous_billing": previous_billing,
        })
        total_due += current_billing

    # Create invoice
    db.execute(
        "INSERT INTO invoices (id, invoice_number, project_id, contract_id, previous_invoice_id, "
        "type, total_due, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, 'task', %s, %s, %s)",
        (inv_id, invoice_number, project_id, contract_id, previous_invoice_id, total_due, now, now),
    )

    # Create line items
    for i, li in enumerate(line_items):
        li_id = generate_id("li-")
        db.execute(
            "INSERT INTO invoice_line_items (id, invoice_id, sort_order, name, description, "
            "quantity, unit_price, amount, previous_billing, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (li_id, inv_id, i + 1, li["name"], li["description"],
             li["quantity"], li["unit_price"], li["amount"], li["previous_billing"], now),
        )

    # Set as current invoice on project
    db.execute("UPDATE projects SET current_invoice_id = %s WHERE id = %s", (inv_id, project_id))

    db.commit()

    # Try to create Google Sheet for this invoice (unless skipped)
    sheet_url = None
    sheet_error = None
    if not data.skip_sheet:
        try:
            from ..google_sheets import create_invoice_sheet

            project = db.execute(
                "SELECT p.*, c.name as client_name, c.company as client_company, "
                "c.address as client_address "
                "FROM projects p LEFT JOIN clients c ON p.client_id = c.id "
                "WHERE p.id = %s",
                (project_id,),
            ).fetchone()

            company_email = ""
            drive_folder_id = ""
            template_id = ""
            for key in ("company_email", "invoice_drive_folder_id", "invoice_template_id"):
                row = db.execute(
                    "SELECT value FROM company_settings WHERE key = %s", (key,)
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
                project_data_path=p_dict.get("data_path") or "",
            )
            db.execute(
                "UPDATE invoices SET data_path = %s, updated_at = %s WHERE id = %s",
                (sheet_url, datetime.now().isoformat(), inv_id),
            )
            db.commit()
        except FileNotFoundError:
            logger.info("Google Sheet creation skipped: no credentials configured")
            sheet_error = "Google credentials not configured"
        except Exception as e:
            logger.error("Google Sheet creation failed: %s", e, exc_info=True)
            sheet_url = None
            sheet_error = str(e)

    invoice = db.execute("SELECT * FROM invoices WHERE id = %s", (inv_id,)).fetchone()
    result = dict(invoice)
    if not result.get("data_path") and sheet_error:
        result["_warning"] = f"Invoice created but Google Sheet failed: {sheet_error}"
    return result


def _update_contract_total(db, contract_id: str):
    total = db.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM contract_tasks WHERE contract_id = %s",
        (contract_id,),
    ).fetchone()["total"]
    db.execute(
        "UPDATE contracts SET total_amount = %s, updated_at = %s WHERE id = %s",
        (total, datetime.now().isoformat(), contract_id),
    )
