from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db
from ..models.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from ..utils import generate_id

router = APIRouter()


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    q: str | None = Query(None, description="Search by name or email"),
    db=Depends(get_db),
):
    if q:
        like = f"%{q}%"
        rows = db.execute(
            "SELECT * FROM employees WHERE deleted_at IS NULL "
            "AND (first_name ILIKE %s OR last_name ILIKE %s OR email ILIKE %s) ORDER BY first_name, last_name",
            (like, like, like),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM employees WHERE deleted_at IS NULL ORDER BY first_name, last_name"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM employees WHERE id = %s AND deleted_at IS NULL", (employee_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    return dict(row)


@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(data: EmployeeCreate, db=Depends(get_db)):
    emp_id = generate_id("emp-")
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, bot_id, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (emp_id, data.first_name, data.last_name, data.email, data.bot_id, now, now),
    )
    db.commit()
    return {
        "id": emp_id, "first_name": data.first_name, "last_name": data.last_name,
        "email": data.email, "bot_id": data.bot_id, "is_active": True,
        "created_at": now, "updated_at": now,
    }


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: str, data: EmployeeUpdate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM employees WHERE id = %s AND deleted_at IS NULL", (employee_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return dict(existing)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [employee_id]
    db.execute(f"UPDATE employees SET {set_clause} WHERE id = %s", values)
    db.commit()

    row = db.execute("SELECT * FROM employees WHERE id = %s", (employee_id,)).fetchone()
    return dict(row)


@router.delete("/{employee_id}")
def delete_employee(employee_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM employees WHERE id = %s AND deleted_at IS NULL", (employee_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")

    now = datetime.now().isoformat()
    db.execute("UPDATE employees SET deleted_at = %s WHERE id = %s", (now, employee_id))
    db.commit()
    return {"success": True}
