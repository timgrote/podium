from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db
from ..events import event_bus
from ..models.task import (
    TaskBulkRequest,
    TaskCreate,
    TaskNoteCreate,
    TaskNoteResponse,
    TaskNoteUpdate,
    TaskResponse,
    TaskUpdate,
)
from ..utils import generate_id

STALE_DAYS = 30
BULK_ALLOWED_FIELDS = {"due_date", "status", "assignee_ids", "priority"}

router = APIRouter()


# --- Helpers ---

def _get_assignees_for_task(db, task_id: str) -> list[dict]:
    rows = db.execute(
        "SELECT e.id, e.first_name, e.last_name, e.email "
        "FROM project_task_assignees a "
        "JOIN employees e ON a.employee_id = e.id "
        "WHERE a.task_id = %s AND e.deleted_at IS NULL",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_notes_for_task(db, task_id: str) -> list[dict]:
    rows = db.execute(
        "SELECT n.id, n.task_id, n.author_id, n.content, n.created_at, "
        "e.first_name || ' ' || e.last_name AS author_name "
        "FROM project_task_notes n "
        "LEFT JOIN employees e ON n.author_id = e.id "
        "WHERE n.task_id = %s ORDER BY n.created_at ASC",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _compute_is_stale(task: dict) -> bool:
    if task.get("status") in ("done", "archived", "canceled"):
        return False
    updated_at = task.get("updated_at")
    if not updated_at:
        return False
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at)
        except ValueError:
            return False
    if updated_at.tzinfo is not None:
        threshold = datetime.now(updated_at.tzinfo) - timedelta(days=STALE_DAYS)
    else:
        threshold = datetime.now() - timedelta(days=STALE_DAYS)
    return updated_at < threshold


def _get_subtasks(db, parent_id: str) -> list[dict]:
    rows = db.execute(
        "SELECT * FROM project_tasks WHERE parent_id = %s AND deleted_at IS NULL "
        "ORDER BY sort_order, created_at",
        (parent_id,),
    ).fetchall()
    result = []
    for row in rows:
        task = dict(row)
        task["assignees"] = _get_assignees_for_task(db, task["id"])
        task["notes"] = _get_notes_for_task(db, task["id"])
        task["subtasks"] = []  # only one level deep
        task["is_stale"] = _compute_is_stale(task)
        result.append(task)
    return result


def _build_task_response(db, task_row) -> dict:
    task = dict(task_row)
    task["assignees"] = _get_assignees_for_task(db, task["id"])
    task["notes"] = _get_notes_for_task(db, task["id"])
    task["subtasks"] = _get_subtasks(db, task["id"])
    task["is_stale"] = _compute_is_stale(task)
    return task


def _set_assignees(db, task_id: str, assignee_ids: list[str]):
    db.execute("DELETE FROM project_task_assignees WHERE task_id = %s", (task_id,))
    for emp_id in assignee_ids:
        db.execute(
            "INSERT INTO project_task_assignees (task_id, employee_id) VALUES (%s, %s)",
            (task_id, emp_id),
        )


# --- Project-scoped endpoints ---

def _parse_status_csv(status: str | None) -> list[str] | None:
    if not status:
        return None
    parts = [s.strip() for s in status.split(",") if s.strip()]
    return parts or None


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
def list_project_tasks(
    project_id: str,
    due_before: date | None = Query(None),
    due_after: date | None = Query(None),
    stale: bool | None = Query(None),
    status: str | None = Query(None),
    assignee: str | None = Query(None),
    db=Depends(get_db),
):
    sql = (
        "SELECT t.* FROM project_tasks t "
        "WHERE t.project_id = %s AND t.parent_id IS NULL AND t.deleted_at IS NULL"
    )
    params: list = [project_id]
    if due_before is not None:
        sql += " AND t.due_date <= %s"
        params.append(str(due_before))
    if due_after is not None:
        sql += " AND t.due_date >= %s"
        params.append(str(due_after))
    statuses = _parse_status_csv(status)
    if statuses:
        sql += " AND t.status = ANY(%s)"
        params.append(statuses)
    if stale is True:
        cutoff = (datetime.now() - timedelta(days=STALE_DAYS)).isoformat()
        sql += " AND t.updated_at < %s AND t.status NOT IN ('done','archived','canceled')"
        params.append(cutoff)
    if assignee:
        sql += (
            " AND EXISTS (SELECT 1 FROM project_task_assignees a "
            "WHERE a.task_id = t.id AND a.employee_id = %s)"
        )
        params.append(assignee)
    sql += " ORDER BY t.sort_order, t.created_at"
    rows = db.execute(sql, tuple(params)).fetchall()
    return [_build_task_response(db, row) for row in rows]


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
def create_task(project_id: str, data: TaskCreate, db=Depends(get_db)):
    # Verify project exists
    proj = db.execute(
        "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL", (project_id,)
    ).fetchone()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    task_id = generate_id("task-")
    now = datetime.now().isoformat()
    start_date = str(data.start_date) if data.start_date else now[:10]  # default to today
    db.execute(
        "INSERT INTO project_tasks "
        "(id, project_id, parent_id, title, description, status, priority, start_date, due_date, reminder_at, sort_order, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (task_id, project_id, data.parent_id, data.title, data.description,
         data.status, data.priority, start_date,
         str(data.due_date) if data.due_date else None,
         str(data.reminder_at) if data.reminder_at else None,
         data.sort_order, now, now),
    )

    if data.assignee_ids:
        _set_assignees(db, task_id, data.assignee_ids)

    db.commit()
    event_bus.publish(project_id, "task_created", task_id)

    row = db.execute("SELECT * FROM project_tasks WHERE id = %s", (task_id,)).fetchone()
    return _build_task_response(db, row)


# --- Cross-project "My Tasks" endpoint (before /tasks/{task_id} to avoid shadowing) ---

@router.get("/tasks/my")
def list_my_tasks(
    employee_id: str,
    due_before: date | None = Query(None),
    due_after: date | None = Query(None),
    stale: bool | None = Query(None),
    status: str | None = Query(None),
    no_due_date: bool | None = Query(None),
    db=Depends(get_db),
):
    sql = (
        "SELECT t.*, p.name AS project_name, p.job_code "
        "FROM project_tasks t "
        "JOIN project_task_assignees a ON a.task_id = t.id "
        "JOIN projects p ON p.id = t.project_id "
        "WHERE a.employee_id = %s "
        "AND t.deleted_at IS NULL "
        "AND p.deleted_at IS NULL "
        "AND t.parent_id IS NULL"
    )
    params: list = [employee_id]
    if due_before is not None:
        sql += " AND t.due_date <= %s"
        params.append(str(due_before))
    if due_after is not None:
        sql += " AND t.due_date >= %s"
        params.append(str(due_after))
    if no_due_date is True:
        sql += " AND t.due_date IS NULL"
    statuses = _parse_status_csv(status)
    if statuses:
        sql += " AND t.status = ANY(%s)"
        params.append(statuses)
    if stale is True:
        cutoff = (datetime.now() - timedelta(days=STALE_DAYS)).isoformat()
        sql += " AND t.updated_at < %s AND t.status NOT IN ('done','archived','canceled')"
        params.append(cutoff)
    sql += " ORDER BY t.due_date ASC NULLS LAST, t.created_at DESC"
    rows = db.execute(sql, tuple(params)).fetchall()
    result = []
    for row in rows:
        task = dict(row)
        task["assignees"] = _get_assignees_for_task(db, task["id"])
        task["notes"] = _get_notes_for_task(db, task["id"])
        task["subtasks"] = _get_subtasks(db, task["id"])
        task["is_stale"] = _compute_is_stale(task)
        result.append(task)
    return result


@router.get("/tasks/done-today")
def list_done_today(
    employee_id: str,
    today: date | None = Query(None, description="Client local date (YYYY-MM-DD); defaults to server today"),
    db=Depends(get_db),
):
    day = today or date.today()
    rows = db.execute(
        "SELECT t.*, p.name AS project_name, p.job_code "
        "FROM project_tasks t "
        "JOIN project_task_assignees a ON a.task_id = t.id "
        "JOIN projects p ON p.id = t.project_id "
        "WHERE a.employee_id = %s "
        "AND t.deleted_at IS NULL "
        "AND p.deleted_at IS NULL "
        "AND t.parent_id IS NULL "
        "AND t.completed_at >= %s "
        "AND t.completed_at < %s "
        "ORDER BY t.completed_at DESC",
        (employee_id, str(day), str(day + timedelta(days=1))),
    ).fetchall()
    result = []
    for row in rows:
        task = dict(row)
        task["assignees"] = _get_assignees_for_task(db, task["id"])
        task["notes"] = _get_notes_for_task(db, task["id"])
        task["subtasks"] = _get_subtasks(db, task["id"])
        task["is_stale"] = _compute_is_stale(task)
        result.append(task)
    return result


@router.patch("/tasks/bulk")
def bulk_update_tasks(data: TaskBulkRequest, db=Depends(get_db)):
    if not data.task_ids:
        raise HTTPException(status_code=400, detail="task_ids cannot be empty")

    fields_set = data.patch.model_fields_set
    extra = fields_set - BULK_ALLOWED_FIELDS
    if extra:
        raise HTTPException(status_code=400, detail=f"Disallowed fields: {sorted(extra)}")
    if not fields_set:
        raise HTTPException(status_code=400, detail="patch must include at least one field")

    rows = db.execute(
        "SELECT id, status FROM project_tasks WHERE id = ANY(%s) AND deleted_at IS NULL",
        (data.task_ids,),
    ).fetchall()
    found = {r["id"]: dict(r) for r in rows}
    missing = [tid for tid in data.task_ids if tid not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"Tasks not found: {missing}")

    patch = data.patch
    now = datetime.now().isoformat()
    updated_ids: list[str] = []

    for tid in data.task_ids:
        updates: dict = {}
        if "due_date" in fields_set:
            updates["due_date"] = str(patch.due_date) if patch.due_date else None
        if "priority" in fields_set:
            updates["priority"] = patch.priority
        if "status" in fields_set:
            updates["status"] = patch.status
            existing_status = found[tid]["status"]
            if patch.status == "done" and existing_status != "done":
                updates["completed_at"] = now
            elif patch.status and patch.status != "done" and existing_status == "done":
                updates["completed_at"] = None
        if updates:
            updates["updated_at"] = now
            set_clause = ", ".join(f"{k} = %s" for k in updates)
            values = list(updates.values()) + [tid]
            db.execute(f"UPDATE project_tasks SET {set_clause} WHERE id = %s", values)
        if "assignee_ids" in fields_set and patch.assignee_ids is not None:
            _set_assignees(db, tid, patch.assignee_ids)
            db.execute(
                "UPDATE project_tasks SET updated_at = %s WHERE id = %s",
                (now, tid),
            )
        updated_ids.append(tid)

    db.commit()

    project_rows = db.execute(
        "SELECT id, project_id FROM project_tasks WHERE id = ANY(%s)",
        (updated_ids,),
    ).fetchall()
    for r in project_rows:
        event_bus.publish(r["project_id"], "task_updated", r["id"])

    result_rows = db.execute(
        "SELECT * FROM project_tasks WHERE id = ANY(%s)",
        (updated_ids,),
    ).fetchall()
    return [_build_task_response(db, r) for r in result_rows]


# --- Task Notes (registered before /tasks/{task_id} to avoid route shadowing) ---

@router.post("/tasks/{task_id}/notes", response_model=TaskNoteResponse, status_code=201)
def add_note(task_id: str, data: TaskNoteCreate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM project_tasks WHERE id = %s AND deleted_at IS NULL", (task_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    note_id = generate_id("note-")
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO project_task_notes (id, task_id, author_id, content, created_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (note_id, task_id, data.author_id, data.content, now),
    )
    db.commit()
    task_row = db.execute("SELECT project_id FROM project_tasks WHERE id = %s", (task_id,)).fetchone()
    if task_row:
        event_bus.publish(task_row["project_id"], "task_updated", task_id)

    # Fetch with author name
    row = db.execute(
        "SELECT n.id, n.task_id, n.author_id, n.content, n.created_at, "
        "e.first_name || ' ' || e.last_name AS author_name "
        "FROM project_task_notes n "
        "LEFT JOIN employees e ON n.author_id = e.id "
        "WHERE n.id = %s",
        (note_id,),
    ).fetchone()
    return dict(row)


@router.patch("/tasks/notes/{note_id}", response_model=TaskNoteResponse)
def update_note(note_id: str, data: TaskNoteUpdate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT n.id, n.task_id, t.project_id FROM project_task_notes n "
        "JOIN project_tasks t ON n.task_id = t.id WHERE n.id = %s", (note_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    db.execute(
        "UPDATE project_task_notes SET content = %s WHERE id = %s",
        (data.content, note_id),
    )
    db.commit()
    event_bus.publish(existing["project_id"], "task_updated", existing["task_id"])

    row = db.execute(
        "SELECT n.id, n.task_id, n.author_id, n.content, n.created_at, "
        "e.first_name || ' ' || e.last_name AS author_name "
        "FROM project_task_notes n "
        "LEFT JOIN employees e ON n.author_id = e.id "
        "WHERE n.id = %s",
        (note_id,),
    ).fetchone()
    return dict(row)


@router.delete("/tasks/notes/{note_id}")
def delete_note(note_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT n.id, n.task_id, t.project_id FROM project_task_notes n "
        "JOIN project_tasks t ON n.task_id = t.id WHERE n.id = %s", (note_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    task_id = existing["task_id"]
    project_id = existing["project_id"]
    db.execute("DELETE FROM project_task_notes WHERE id = %s", (note_id,))
    db.commit()
    event_bus.publish(project_id, "task_updated", task_id)
    return {"success": True}


# --- Single-task endpoints ---

@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM project_tasks WHERE id = %s AND deleted_at IS NULL", (task_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return _build_task_response(db, row)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: str, data: TaskUpdate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM project_tasks WHERE id = %s AND deleted_at IS NULL", (task_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = {}
    dump = data.model_dump(exclude_unset=True)
    for k, v in dump.items():
        if k == "assignee_ids":
            continue
        if v is None:
            updates[k] = None
        elif k in ("start_date", "due_date", "reminder_at"):
            updates[k] = str(v)
        else:
            updates[k] = v

    # Handle status → completed_at
    if data.status == "done" and existing["status"] != "done":
        updates["completed_at"] = datetime.now().isoformat()
    elif data.status and data.status != "done" and existing["status"] == "done":
        updates["completed_at"] = None

    if updates:
        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [task_id]
        db.execute(f"UPDATE project_tasks SET {set_clause} WHERE id = %s", values)

    if data.assignee_ids is not None:
        _set_assignees(db, task_id, data.assignee_ids)

    db.commit()
    project_id = existing["project_id"]
    event_bus.publish(project_id, "task_updated", task_id)

    row = db.execute("SELECT * FROM project_tasks WHERE id = %s", (task_id,)).fetchone()
    return _build_task_response(db, row)


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM project_tasks WHERE id = %s AND deleted_at IS NULL", (task_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    now = datetime.now().isoformat()
    # Soft delete subtasks too
    db.execute(
        "UPDATE project_tasks SET deleted_at = %s WHERE parent_id = %s AND deleted_at IS NULL",
        (now, task_id),
    )
    db.execute("UPDATE project_tasks SET deleted_at = %s WHERE id = %s", (now, task_id))
    db.commit()
    project_id = existing["project_id"]
    event_bus.publish(project_id, "task_deleted", task_id)
    return {"success": True}
