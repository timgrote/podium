from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db
from ..models.time_entry import TimeEntryCreate, TimeEntryResponse, TimeEntryUpdate
from ..utils import generate_id

router = APIRouter()


@router.get("")
def list_time_entries(
    employee_id: str | None = Query(None),
    project_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db=Depends(get_db),
):
    conditions = ["te.deleted_at IS NULL"]
    params: list = []

    if employee_id:
        conditions.append("te.employee_id = %s")
        params.append(employee_id)
    if project_id:
        conditions.append("te.project_id = %s")
        params.append(project_id)
    if date_from:
        conditions.append("te.date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("te.date <= %s")
        params.append(date_to)

    where = " AND ".join(conditions)
    rows = db.execute(
        f"SELECT te.*, "
        f"(e.first_name || ' ' || e.last_name) AS employee_name, "
        f"p.name AS project_name, "
        f"ct.name AS contract_task_name "
        f"FROM time_entries te "
        f"LEFT JOIN employees e ON te.employee_id = e.id "
        f"LEFT JOIN projects p ON te.project_id = p.id "
        f"LEFT JOIN contract_tasks ct ON te.contract_task_id = ct.id "
        f"WHERE {where} "
        f"ORDER BY te.date DESC, te.created_at DESC",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/summary")
def time_summary(
    project_id: str = Query(...),
    db=Depends(get_db),
):
    by_employee = db.execute(
        "SELECT te.employee_id, (e.first_name || ' ' || e.last_name) AS employee_name, "
        "SUM(te.hours) AS total_hours "
        "FROM time_entries te "
        "LEFT JOIN employees e ON te.employee_id = e.id "
        "WHERE te.project_id = %s AND te.deleted_at IS NULL "
        "GROUP BY te.employee_id, e.first_name, e.last_name "
        "ORDER BY total_hours DESC",
        (project_id,),
    ).fetchall()

    by_task = db.execute(
        "SELECT te.contract_task_id, ct.name AS task_name, "
        "SUM(te.hours) AS total_hours "
        "FROM time_entries te "
        "LEFT JOIN contract_tasks ct ON te.contract_task_id = ct.id "
        "WHERE te.project_id = %s AND te.deleted_at IS NULL "
        "GROUP BY te.contract_task_id, ct.name "
        "ORDER BY total_hours DESC",
        (project_id,),
    ).fetchall()

    total = db.execute(
        "SELECT COALESCE(SUM(hours), 0) AS total_hours "
        "FROM time_entries WHERE project_id = %s AND deleted_at IS NULL",
        (project_id,),
    ).fetchone()

    return {
        "total_hours": total["total_hours"] if total else 0,
        "by_employee": [dict(r) for r in by_employee],
        "by_task": [dict(r) for r in by_task],
    }


@router.get("/{entry_id}")
def get_time_entry(entry_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT te.*, "
        "(e.first_name || ' ' || e.last_name) AS employee_name, "
        "p.name AS project_name, "
        "ct.name AS contract_task_name "
        "FROM time_entries te "
        "LEFT JOIN employees e ON te.employee_id = e.id "
        "LEFT JOIN projects p ON te.project_id = p.id "
        "LEFT JOIN contract_tasks ct ON te.contract_task_id = ct.id "
        "WHERE te.id = %s AND te.deleted_at IS NULL",
        (entry_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Time entry not found")
    return dict(row)


@router.post("", status_code=201)
def create_time_entry(data: TimeEntryCreate, db=Depends(get_db)):
    entry_id = generate_id("te-")
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO time_entries (id, employee_id, project_id, contract_task_id, hours, date, description, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (entry_id, data.employee_id, data.project_id, data.contract_task_id, float(data.hours), str(data.date), data.description, now, now),
    )
    db.commit()

    row = db.execute(
        "SELECT te.*, "
        "(e.first_name || ' ' || e.last_name) AS employee_name, "
        "p.name AS project_name, "
        "ct.name AS contract_task_name "
        "FROM time_entries te "
        "LEFT JOIN employees e ON te.employee_id = e.id "
        "LEFT JOIN projects p ON te.project_id = p.id "
        "LEFT JOIN contract_tasks ct ON te.contract_task_id = ct.id "
        "WHERE te.id = %s",
        (entry_id,),
    ).fetchone()
    return dict(row)


@router.patch("/{entry_id}")
def update_time_entry(entry_id: str, data: TimeEntryUpdate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM time_entries WHERE id = %s AND deleted_at IS NULL", (entry_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Time entry not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return get_time_entry(entry_id, db)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [entry_id]
    db.execute(f"UPDATE time_entries SET {set_clause} WHERE id = %s", values)
    db.commit()
    return get_time_entry(entry_id, db)


@router.delete("/{entry_id}")
def delete_time_entry(entry_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM time_entries WHERE id = %s AND deleted_at IS NULL", (entry_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Time entry not found")

    now = datetime.now().isoformat()
    db.execute("UPDATE time_entries SET deleted_at = %s WHERE id = %s", (now, entry_id))
    db.commit()
    return {"success": True}
