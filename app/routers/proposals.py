import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..models.proposal import (
    ProposalCreate,
    ProposalTaskCreate,
    ProposalTaskUpdate,
    ProposalUpdate,
)
from ..utils import generate_id

router = APIRouter()


@router.get("/{proposal_id}")
def get_proposal(proposal_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT * FROM proposals WHERE id = ? AND deleted_at IS NULL", (proposal_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal = dict(row)
    tasks = db.execute(
        "SELECT * FROM proposal_tasks WHERE proposal_id = ? ORDER BY sort_order",
        (proposal_id,),
    ).fetchall()
    proposal["tasks"] = [dict(t) for t in tasks]
    return proposal


@router.post("", status_code=201)
def create_proposal(data: ProposalCreate, db: sqlite3.Connection = Depends(get_db)):
    # Verify project exists
    project = db.execute(
        "SELECT id FROM projects WHERE id = ? AND deleted_at IS NULL", (data.project_id,)
    ).fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now().isoformat()
    proposal_id = generate_id("prop-")

    # Auto-sum total_fee from tasks if not provided
    total_fee = data.total_fee
    if total_fee == 0 and data.tasks:
        total_fee = sum(t.amount for t in data.tasks)

    db.execute(
        "INSERT INTO proposals (id, project_id, client_company, client_contact_email, "
        "total_fee, status, data_path, pdf_path, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (proposal_id, data.project_id, data.client_company, data.client_contact_email,
         total_fee, data.status, data.data_path, data.pdf_path, now, now),
    )

    # Create inline tasks
    if data.tasks:
        for i, task in enumerate(data.tasks):
            task_id = generate_id("ptask-")
            db.execute(
                "INSERT INTO proposal_tasks (id, proposal_id, sort_order, name, description, amount, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, proposal_id, i + 1, task.name, task.description, task.amount, now),
            )

    db.commit()
    return get_proposal(proposal_id, db)


@router.patch("/{proposal_id}")
def update_proposal(
    proposal_id: str,
    data: ProposalUpdate,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM proposals WHERE id = ? AND deleted_at IS NULL", (proposal_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return get_proposal(proposal_id, db)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [proposal_id]
    db.execute(f"UPDATE proposals SET {set_clause} WHERE id = ?", values)
    db.commit()
    return get_proposal(proposal_id, db)


@router.delete("/{proposal_id}")
def delete_proposal(proposal_id: str, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM proposals WHERE id = ? AND deleted_at IS NULL", (proposal_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    now = datetime.now().isoformat()
    db.execute("UPDATE proposals SET deleted_at = ? WHERE id = ?", (now, proposal_id))
    db.commit()
    return {"success": True}


# --- Proposal Tasks ---

@router.post("/{proposal_id}/tasks")
def add_proposal_task(
    proposal_id: str,
    data: ProposalTaskCreate,
    db: sqlite3.Connection = Depends(get_db),
):
    proposal = db.execute(
        "SELECT * FROM proposals WHERE id = ? AND deleted_at IS NULL", (proposal_id,)
    ).fetchone()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    now = datetime.now().isoformat()
    task_id = generate_id("ptask-")

    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) as max_order FROM proposal_tasks WHERE proposal_id = ?",
        (proposal_id,),
    ).fetchone()["max_order"]

    db.execute(
        "INSERT INTO proposal_tasks (id, proposal_id, sort_order, name, description, amount, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (task_id, proposal_id, max_order + 1, data.name, data.description, data.amount, now),
    )

    _update_proposal_total(db, proposal_id)
    db.commit()
    return get_proposal(proposal_id, db)


@router.patch("/{proposal_id}/tasks/{task_id}")
def update_proposal_task(
    proposal_id: str,
    task_id: str,
    data: ProposalTaskUpdate,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM proposal_tasks WHERE id = ? AND proposal_id = ?",
        (task_id, proposal_id),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return get_proposal(proposal_id, db)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]
    db.execute(f"UPDATE proposal_tasks SET {set_clause} WHERE id = ?", values)

    _update_proposal_total(db, proposal_id)
    db.commit()
    return get_proposal(proposal_id, db)


@router.delete("/{proposal_id}/tasks/{task_id}")
def delete_proposal_task(
    proposal_id: str,
    task_id: str,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM proposal_tasks WHERE id = ? AND proposal_id = ?",
        (task_id, proposal_id),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    db.execute("DELETE FROM proposal_tasks WHERE id = ?", (task_id,))
    _update_proposal_total(db, proposal_id)
    db.commit()
    return {"success": True}


# --- Promote to Contract ---

@router.post("/{proposal_id}/promote")
def promote_to_contract(
    proposal_id: str,
    signed_at: str | None = None,
    file_path: str | None = None,
    db: sqlite3.Connection = Depends(get_db),
):
    proposal = db.execute(
        "SELECT * FROM proposals WHERE id = ? AND deleted_at IS NULL", (proposal_id,)
    ).fetchone()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    now = datetime.now().isoformat()
    contract_id = generate_id("con-")
    project_id = proposal["project_id"]

    # 1. Create contract from proposal
    db.execute(
        "INSERT INTO contracts (id, project_id, total_amount, signed_at, file_path, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (contract_id, project_id, proposal["total_fee"],
         signed_at or now, file_path, now, now),
    )

    # 2. Copy proposal_tasks → contract_tasks
    tasks = db.execute(
        "SELECT * FROM proposal_tasks WHERE proposal_id = ? ORDER BY sort_order",
        (proposal_id,),
    ).fetchall()

    for task in tasks:
        ctask_id = generate_id("ctask-")
        db.execute(
            "INSERT INTO contract_tasks (id, contract_id, sort_order, name, description, amount, "
            "billed_amount, billed_percent, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?)",
            (ctask_id, contract_id, task["sort_order"], task["name"],
             task["description"], task["amount"], now, now),
        )

    # 3. Mark proposal as accepted
    db.execute(
        "UPDATE proposals SET status = 'accepted', updated_at = ? WHERE id = ?",
        (now, proposal_id),
    )

    # 4. Update project status to 'contract'
    db.execute(
        "UPDATE projects SET status = 'contract', updated_at = ? WHERE id = ?",
        (now, project_id),
    )

    db.commit()

    # Return the new contract with tasks
    contract = db.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,)).fetchone()
    result = dict(contract)
    contract_tasks = db.execute(
        "SELECT * FROM contract_tasks WHERE contract_id = ? ORDER BY sort_order",
        (contract_id,),
    ).fetchall()
    result["tasks"] = [dict(t) for t in contract_tasks]
    return result


def _update_proposal_total(db: sqlite3.Connection, proposal_id: str):
    total = db.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM proposal_tasks WHERE proposal_id = ?",
        (proposal_id,),
    ).fetchone()["total"]
    db.execute(
        "UPDATE proposals SET total_fee = ?, updated_at = ? WHERE id = ?",
        (total, datetime.now().isoformat(), proposal_id),
    )
