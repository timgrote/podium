"""Kanban board for projects.

Projects are rendered as cards grouped into columns by status. The column set
reflects the engineering-consultant project lifecycle and is the canonical
ordering for the board:

    lead -> proposal -> contract -> active -> complete -> archive

Each card carries a compact project summary so the board needs no N+1 detail
fetches. Moving a card updates its status (cross-column) and its board_order
(within-column).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..database import get_db
from ..utils import generate_id  # noqa: F401  (kept for future board templates)

router = APIRouter()

# Canonical column order + human labels. Status values match projects.status.
KANBAN_COLUMNS: list[dict[str, str]] = [
    {"status": "lead", "label": "Lead"},
    {"status": "proposal", "label": "Proposal"},
    {"status": "contract", "label": "Contract"},
    {"status": "active", "label": "Active"},
    {"status": "complete", "label": "Complete"},
    {"status": "archive", "label": "Archive"},
]

_COLUMN_STATUSES = {c["status"] for c in KANBAN_COLUMNS}

# Task board columns. Values match project_tasks.status.
TASK_COLUMNS: list[dict[str, str]] = [
    {"status": "todo", "label": "To Do"},
    {"status": "in_progress", "label": "In Progress"},
    {"status": "blocked", "label": "Blocked"},
    {"status": "done", "label": "Done"},
    {"status": "canceled", "label": "Canceled"},
]

_TASK_COLUMN_STATUSES = {c["status"] for c in TASK_COLUMNS}


class KanbanMove(BaseModel):
    project_id: str
    status: str
    board_order: int = 0


class KanbanTaskMove(BaseModel):
    task_id: str
    status: str
    sort_order: int = 0


def _board_rows(db):
    """All non-deleted projects with the compact fields the board needs."""
    return db.execute(
        """
        SELECT
            p.id,
            p.project_number,
            p.job_code,
            p.name AS project_name,
            p.status,
            p.board_order,
            p.client_id,
            p.location,
            p.data_path,
            c.name AS client_name,
            (e.first_name || ' ' || e.last_name) AS pm_name,
            e.avatar_url AS pm_avatar_url,
            (SELECT MIN(pt.due_date) FROM project_tasks pt
             WHERE pt.project_id = p.id AND pt.completed_at IS NULL
               AND pt.due_date IS NOT NULL AND pt.deleted_at IS NULL
            ) AS next_task_deadline,
            p.updated_at AS last_activity,
            COALESCE((SELECT SUM(i.total_due) FROM invoices i
                      WHERE i.project_id = p.id AND i.deleted_at IS NULL
                        AND i.paid_status = 'paid'), 0) AS total_paid,
            COALESCE((SELECT SUM(i.total_due) FROM invoices i
                      WHERE i.project_id = p.id AND i.deleted_at IS NULL
                        AND i.paid_status != 'paid'), 0) AS total_outstanding,
            (SELECT COUNT(*) FROM contracts con
             WHERE con.project_id = p.id AND con.deleted_at IS NULL) AS contract_count,
            (SELECT COUNT(*) FROM invoices inv
             WHERE inv.project_id = p.id AND inv.deleted_at IS NULL) AS invoice_count,
            (SELECT COUNT(*) FROM proposals prop
             WHERE prop.project_id = p.id AND prop.deleted_at IS NULL) AS proposal_count
        FROM projects p
        LEFT JOIN clients c ON p.client_id = c.id
        LEFT JOIN employees e ON p.pm_id = e.id
        WHERE p.deleted_at IS NULL
        ORDER BY p.status, p.board_order ASC, p.name
        """
    ).fetchall()


def _serialize_card(row) -> dict:
    p = dict(row)
    return {
        "id": p["id"],
        "project_number": p.get("project_number"),
        "job_code": p.get("job_code"),
        "project_name": p.get("project_name"),
        "status": p["status"],
        "board_order": p.get("board_order") or 0,
        "client_id": p.get("client_id"),
        "client_name": p.get("client_name"),
        "pm_name": p.get("pm_name"),
        "pm_avatar_url": p.get("pm_avatar_url"),
        "location": p.get("location"),
        "data_path": p.get("data_path"),
        "next_task_deadline": str(p["next_task_deadline"]) if p.get("next_task_deadline") else None,
        "last_activity": str(p["last_activity"]) if p.get("last_activity") else None,
        "total_paid": float(p.get("total_paid") or 0),
        "total_outstanding": float(p.get("total_outstanding") or 0),
        "contract_count": p.get("contract_count") or 0,
        "invoice_count": p.get("invoice_count") or 0,
        "proposal_count": p.get("proposal_count") or 0,
    }


def _build_board(db) -> dict:
    """Group project rows into an ordered board payload."""
    buckets = {c["status"]: [] for c in KANBAN_COLUMNS}
    for row in _board_rows(db):
        status = row["status"]
        if status in buckets:
            buckets[status].append(_serialize_card(row))
        else:
            # Unknown statuses appear in their own trailing column so nothing
            # is ever hidden from the board.
            buckets.setdefault(status, [])
            buckets[status].append(_serialize_card(row))

    columns = [
        {"status": c["status"], "label": c["label"], "projects": buckets[c["status"]]}
        for c in KANBAN_COLUMNS
    ]
    extras = [s for s in buckets if s not in _COLUMN_STATUSES]
    for status in extras:
        columns.append({"status": status, "label": status, "projects": buckets[status]})
    return {"columns": columns}


@router.get("")
def get_board(db=Depends(get_db)):
    """Return the full Kanban board: columns with ordered project cards."""
    return _build_board(db)


@router.post("/move")
def move_card(data: KanbanMove, db=Depends(get_db)):
    """Move a project card to a status column (and reorder within it).

    - Sets the project's status (the column it lives in).
    - Sets board_order to place it at the given slot in that column.
    - Reindexes the source and destination columns so board_order stays dense
      (0..n) after the move.
    """
    existing = db.execute(
        "SELECT id, status, board_order FROM projects WHERE id = %s AND deleted_at IS NULL",
        (data.project_id,),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    target_status = data.status
    if target_status not in _COLUMN_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unknown status '{target_status}'")

    source_status = existing["status"]
    now = datetime.now().isoformat()

    # Shift destination column open at the requested slot.
    db.execute(
        "UPDATE projects SET board_order = board_order + 1 "
        "WHERE deleted_at IS NULL AND status = %s AND board_order >= %s AND id != %s",
        (target_status, data.board_order, data.project_id),
    )
    db.execute(
        "UPDATE projects SET status = %s, board_order = %s, updated_at = %s WHERE id = %s",
        (target_status, data.board_order, now, data.project_id),
    )
    db.commit()

    # Reindex source column (if it changed) to keep board_order dense.
    if source_status != target_status:
        _reindex_column(db, source_status)
    _reindex_column(db, target_status)
    db.commit()

    return _build_board(db)


def _reindex_column(db, status: str):
    rows = db.execute(
        "SELECT id FROM projects WHERE deleted_at IS NULL AND status = %s ORDER BY board_order ASC, name",
        (status,),
    ).fetchall()
    for i, row in enumerate(rows):
        db.execute("UPDATE projects SET board_order = %s WHERE id = %s", (i, row["id"]))


# --- Task board ---


def _task_rows(db, assignee: str | None = None):
    """Top-level tasks (not subtasks) with the compact fields the board needs."""
    params: list = []
    assignee_sql = ""
    if assignee:
        assignee_sql = (
            " AND EXISTS (SELECT 1 FROM project_task_assignees a "
            "WHERE a.task_id = t.id AND a.employee_id = %s)"
        )
        params.append(assignee)
    sql = f"""
        SELECT
            t.id,
            t.title,
            t.status,
            t.sort_order,
            t.priority,
            t.due_date,
            t.is_pinned,
            t.tags,
            t.parent_id,
            p.id AS project_id,
            p.project_number,
            p.job_code,
            p.name AS project_name,
            (SELECT COUNT(*) FROM project_tasks sub
             WHERE sub.parent_id = t.id AND sub.deleted_at IS NULL) AS subtask_count,
            COALESCE((
                SELECT e.first_name || ' ' || e.last_name
                FROM project_task_assignees a
                JOIN employees e ON a.employee_id = e.id
                WHERE a.task_id = t.id AND e.deleted_at IS NULL
                ORDER BY e.id
                LIMIT 1
            ), NULL) AS assignee_name
        FROM project_tasks t
        JOIN projects p ON p.id = t.project_id
        WHERE t.deleted_at IS NULL
          AND t.parent_id IS NULL
          AND p.deleted_at IS NULL
        {assignee_sql}
        ORDER BY t.status, t.is_pinned DESC, t.sort_order ASC, t.created_at
    """
    return db.execute(sql, tuple(params)).fetchall()


def _serialize_task(row) -> dict:
    t = dict(row)
    return {
        "id": t["id"],
        "title": t.get("title"),
        "status": t["status"],
        "sort_order": t.get("sort_order") or 0,
        "priority": t.get("priority"),
        "due_date": str(t["due_date"]) if t.get("due_date") else None,
        "is_pinned": bool(t.get("is_pinned")),
        "tags": t.get("tags") or [],
        "parent_id": t.get("parent_id"),
        "project_id": t.get("project_id"),
        "project_number": t.get("project_number"),
        "job_code": t.get("job_code"),
        "project_name": t.get("project_name"),
        "subtask_count": t.get("subtask_count") or 0,
        "assignee_name": t.get("assignee_name"),
    }


def _build_task_board(db, assignee: str | None = None) -> dict:
    buckets = {c["status"]: [] for c in TASK_COLUMNS}
    for row in _task_rows(db, assignee=assignee):
        status = row["status"]
        if status in buckets:
            buckets[status].append(_serialize_task(row))
        else:
            buckets.setdefault(status, [])
            buckets[status].append(_serialize_task(row))

    columns = [
        {"status": c["status"], "label": c["label"], "tasks": buckets[c["status"]]}
        for c in TASK_COLUMNS
    ]
    extras = [s for s in buckets if s not in _TASK_COLUMN_STATUSES]
    for status in extras:
        columns.append({"status": status, "label": status, "tasks": buckets[status]})
    return {"columns": columns}


@router.get("/tasks")
def get_task_board(
    assignee: str | None = Query(None, description="Filter by assignee employee ID"),
    db=Depends(get_db),
):
    """Return the task board: columns with ordered task cards (all projects)."""
    return _build_task_board(db, assignee=assignee)


@router.post("/tasks/move")
def move_task_card(data: KanbanTaskMove, db=Depends(get_db)):
    """Move a task card to a status column (and reorder within it)."""
    existing = db.execute(
        "SELECT id, status, project_id FROM project_tasks WHERE id = %s AND deleted_at IS NULL",
        (data.task_id,),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    target_status = data.status
    if target_status not in _TASK_COLUMN_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unknown status '{target_status}'")

    source_status = existing["status"]
    now = datetime.now().isoformat()

    # Shift destination column open at the requested slot.
    db.execute(
        "UPDATE project_tasks SET sort_order = sort_order + 1 "
        "WHERE deleted_at IS NULL AND parent_id IS NULL AND status = %s "
        "AND sort_order >= %s AND id != %s",
        (target_status, data.sort_order, data.task_id),
    )
    updates: dict = {"status": target_status, "sort_order": data.sort_order, "updated_at": now}
    if target_status == "done" and source_status != "done":
        updates["completed_at"] = now
    elif target_status != "done" and source_status == "done":
        updates["completed_at"] = None
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    db.execute(
        f"UPDATE project_tasks SET {set_clause} WHERE id = %s",
        list(updates.values()) + [data.task_id],
    )
    db.commit()

    # Reindex source (if it changed) and destination columns to keep sort_order dense.
    if source_status != target_status:
        _reindex_task_column(db, source_status)
    _reindex_task_column(db, target_status)
    db.commit()

    return _build_task_board(db)


def _reindex_task_column(db, status: str):
    rows = db.execute(
        "SELECT id FROM project_tasks "
        "WHERE deleted_at IS NULL AND parent_id IS NULL AND status = %s "
        "ORDER BY is_pinned DESC, sort_order ASC, created_at",
        (status,),
    ).fetchall()
    for i, row in enumerate(rows):
        db.execute("UPDATE project_tasks SET sort_order = %s WHERE id = %s", (i, row["id"]))
