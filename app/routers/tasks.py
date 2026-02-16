from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..models.task import TaskCreate, TaskNoteCreate, TaskNoteResponse, TaskResponse, TaskUpdate
from ..utils import generate_id

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
        result.append(task)
    return result


def _build_task_response(db, task_row) -> dict:
    task = dict(task_row)
    task["assignees"] = _get_assignees_for_task(db, task["id"])
    task["notes"] = _get_notes_for_task(db, task["id"])
    task["subtasks"] = _get_subtasks(db, task["id"])
    return task


def _set_assignees(db, task_id: str, assignee_ids: list[str]):
    db.execute("DELETE FROM project_task_assignees WHERE task_id = %s", (task_id,))
    for emp_id in assignee_ids:
        db.execute(
            "INSERT INTO project_task_assignees (task_id, employee_id) VALUES (%s, %s)",
            (task_id, emp_id),
        )


# --- Project-scoped endpoints ---

@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
def list_project_tasks(project_id: str, db=Depends(get_db)):
    # Top-level tasks only (no parent)
    rows = db.execute(
        "SELECT * FROM project_tasks "
        "WHERE project_id = %s AND parent_id IS NULL AND deleted_at IS NULL "
        "ORDER BY sort_order, created_at",
        (project_id,),
    ).fetchall()
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
        "(id, project_id, parent_id, title, description, status, start_date, due_date, reminder_at, sort_order, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (task_id, project_id, data.parent_id, data.title, data.description,
         data.status, start_date,
         str(data.due_date) if data.due_date else None,
         str(data.reminder_at) if data.reminder_at else None,
         data.sort_order, now, now),
    )

    if data.assignee_ids:
        _set_assignees(db, task_id, data.assignee_ids)

    db.commit()

    row = db.execute("SELECT * FROM project_tasks WHERE id = %s", (task_id,)).fetchone()
    return _build_task_response(db, row)


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


@router.delete("/tasks/notes/{note_id}")
def delete_note(note_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM project_task_notes WHERE id = %s", (note_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    db.execute("DELETE FROM project_task_notes WHERE id = %s", (note_id,))
    db.commit()
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
    return {"success": True}
