import logging

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_employee
from ..database import get_db
from ..events import event_bus
from ..models.deliverable import DeliverableCreate, DeliverableResponse, DeliverableUpdate
from ..utils import generate_id

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_STATUSES = {"not_started", "in_progress", "sent", "accepted"}


def _attach_employee_name(db, row: dict) -> dict:
    """Add updated_by_name (first + last) by joining employees table."""
    if row.get("updated_by"):
        emp = db.execute(
            "SELECT first_name, last_name FROM employees WHERE id = %s",
            (row["updated_by"],),
        ).fetchone()
        if emp:
            row["updated_by_name"] = f"{emp['first_name']} {emp['last_name']}".strip()
    return row


def auto_create_deliverables(db, project_id: str, contract_id: str, now: str | None = None):
    """Create a deliverable for each contract task that doesn't have one yet.
    Called when a contract is signed/accepted (via update or promote).
    Idempotent — skips contract tasks that already have a deliverable."""
    if now is None:
        now = datetime.now().isoformat()

    tasks = db.execute(
        "SELECT * FROM contract_tasks WHERE contract_id = %s ORDER BY sort_order",
        (contract_id,),
    ).fetchall()

    for task in tasks:
        existing = db.execute(
            "SELECT 1 FROM project_deliverables WHERE contract_task_id = %s AND deleted_at IS NULL",
            (task["id"],),
        ).fetchone()
        if existing:
            continue

        del_id = generate_id("del-")
        db.execute(
            "INSERT INTO project_deliverables (id, project_id, contract_task_id, name, "
            "sort_order, status, progress_percent, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, 'not_started', 0, %s, %s)",
            (del_id, project_id, task["id"], task["name"], task["sort_order"], now, now),
        )

    event_bus.publish(project_id, "deliverable_updated", contract_id)


# --- List deliverables for a project ---

@router.get("/projects/{project_id}/deliverables")
def list_deliverables(project_id: str, db=Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM project_deliverables "
        "WHERE project_id = %s AND deleted_at IS NULL "
        "ORDER BY sort_order, created_at",
        (project_id,),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        _attach_employee_name(db, d)
        result.append(d)
    return result


# --- Create deliverable ---

@router.post("/projects/{project_id}/deliverables", status_code=201)
def create_deliverable(project_id: str, data: DeliverableCreate, db=Depends(get_db)):
    proj = db.execute(
        "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL", (project_id,)
    ).fetchone()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")

    now = datetime.now().isoformat()
    del_id = generate_id("del-")

    deadline = str(data.deadline) if data.deadline else None

    db.execute(
        "INSERT INTO project_deliverables (id, project_id, contract_task_id, name, "
        "sort_order, status, progress_percent, deadline, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (del_id, project_id, data.contract_task_id, data.name,
         data.sort_order, data.status, data.progress_percent, deadline, now, now),
    )
    db.commit()
    event_bus.publish(project_id, "deliverable_updated", del_id)

    row = db.execute("SELECT * FROM project_deliverables WHERE id = %s", (del_id,)).fetchone()
    result = dict(row)
    _attach_employee_name(db, result)
    return result


# --- Update deliverable ---

@router.patch("/deliverables/{deliverable_id}")
def update_deliverable(
    deliverable_id: str,
    data: DeliverableUpdate,
    db=Depends(get_db),
    current_employee: dict | None = Depends(get_current_employee),
):
    existing = db.execute(
        "SELECT * FROM project_deliverables WHERE id = %s AND deleted_at IS NULL",
        (deliverable_id,),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    raw = data.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None}

    # Allow explicitly clearing updated_by (null is filtered by the check above
    # but we need to distinguish "not sent" from "explicitly null").
    if "updated_by" in raw and raw["updated_by"] is None:
        updates["updated_by"] = None

    if not updates:
        return dict(existing)

    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")

    now = datetime.now().isoformat()

    # Stamp sent_at when status first transitions to 'sent'
    if updates.get("status") == "sent" and not existing["sent_at"]:
        updates["sent_at"] = now

    # Clear sent_at if reverting from sent/accepted back to in_progress
    if updates.get("status") in ("not_started", "in_progress") and existing["sent_at"]:
        updates["sent_at"] = None

    if "deadline" in updates and updates["deadline"]:
        updates["deadline"] = str(updates["deadline"])

    # Auto-stamp updated_by with the logged-in employee unless caller
    # explicitly passed a value (including null to clear it).
    if "updated_by" not in updates and current_employee:
        updates["updated_by"] = current_employee["id"]

    updates["updated_at"] = now
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [deliverable_id]
    db.execute(f"UPDATE project_deliverables SET {set_clause} WHERE id = %s", values)
    db.commit()
    event_bus.publish(existing["project_id"], "deliverable_updated", deliverable_id)

    row = db.execute("SELECT * FROM project_deliverables WHERE id = %s", (deliverable_id,)).fetchone()
    result = dict(row)
    _attach_employee_name(db, result)
    return result


# --- Delete deliverable (soft) ---

@router.delete("/deliverables/{deliverable_id}")
def delete_deliverable(deliverable_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM project_deliverables WHERE id = %s AND deleted_at IS NULL",
        (deliverable_id,),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    now = datetime.now().isoformat()
    db.execute("UPDATE project_deliverables SET deleted_at = %s WHERE id = %s", (now, deliverable_id))
    db.commit()
    event_bus.publish(existing["project_id"], "deliverable_updated", deliverable_id)
    return {"success": True}
