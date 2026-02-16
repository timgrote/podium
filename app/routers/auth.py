import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..auth import (
    SESSION_COOKIE,
    consume_reset_token,
    create_reset_token,
    create_session,
    hash_password,
    require_auth,
    verify_password,
)
from ..config import settings
from ..database import get_db
from ..utils import generate_id

router = APIRouter()


class AuthRequest(BaseModel):
    email: str
    password: str


@router.post("/signup")
def signup(data: AuthRequest, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM employees WHERE email = %s AND deleted_at IS NULL",
        (data.email,),
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    emp_id = generate_id("emp-")
    now = datetime.now().isoformat()
    pw_hash = hash_password(data.password)
    # Default first_name to email prefix
    first_name = data.email.split("@")[0]

    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, password_hash, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (emp_id, first_name, "", data.email, pw_hash, now, now),
    )
    db.commit()

    token = create_session(db, emp_id)
    resp = JSONResponse(content={
        "id": emp_id,
        "first_name": first_name,
        "last_name": "",
        "email": data.email,
        "avatar_url": None,
    })
    resp.set_cookie(
        SESSION_COOKIE, token,
        httponly=True, samesite="lax", max_age=30 * 24 * 3600, path="/",
    )
    return resp


@router.post("/login")
def login(data: AuthRequest, db=Depends(get_db)):
    row = db.execute(
        "SELECT id, first_name, last_name, email, avatar_url, password_hash "
        "FROM employees WHERE email = %s AND deleted_at IS NULL",
        (data.email,),
    ).fetchone()
    if not row or not row["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(data.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_session(db, row["id"])
    resp = JSONResponse(content={
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
        "avatar_url": row["avatar_url"],
    })
    resp.set_cookie(
        SESSION_COOKIE, token,
        httponly=True, samesite="lax", max_age=30 * 24 * 3600, path="/",
    )
    return resp


@router.post("/logout")
def logout(
    employee: dict = Depends(require_auth),
    db=Depends(get_db),
):
    # Delete all sessions for this employee
    db.execute("DELETE FROM sessions WHERE employee_id = %s", (employee["id"],))
    db.commit()
    resp = JSONResponse(content={"success": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@router.get("/me")
def me(employee: dict = Depends(require_auth)):
    return employee


@router.post("/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    employee: dict = Depends(require_auth),
    db=Depends(get_db),
):
    avatars_dir = os.path.join(settings.upload_dir, "avatars")
    os.makedirs(avatars_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "avatar.png")[1] or ".png"
    filename = f"{employee['id']}{ext}"
    filepath = os.path.join(avatars_dir, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    avatar_url = f"/uploads/avatars/{filename}"
    now = datetime.now().isoformat()
    db.execute(
        "UPDATE employees SET avatar_url = %s, updated_at = %s WHERE id = %s",
        (avatar_url, now, employee["id"]),
    )
    db.commit()

    return {"avatar_url": avatar_url}


class ResetRequest(BaseModel):
    employee_id: str


class ResetPassword(BaseModel):
    token: str
    password: str


@router.post("/reset-request")
def request_reset(
    data: ResetRequest,
    employee: dict = Depends(require_auth),
    db=Depends(get_db),
):
    """Admin generates a password reset link for an employee."""
    target = db.execute(
        "SELECT id, email, first_name, last_name FROM employees WHERE id = %s AND deleted_at IS NULL",
        (data.employee_id,),
    ).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="Employee not found")

    token = create_reset_token(db, data.employee_id)
    reset_url = f"/ops/reset-password.html?token={token}"

    return {
        "reset_url": reset_url,
        "employee": {
            "id": target["id"],
            "email": target["email"],
            "name": f"{target['first_name']} {target['last_name']}".strip(),
        },
        "expires_in": "1 hour",
    }


@router.post("/reset-password")
def reset_password(data: ResetPassword, db=Depends(get_db)):
    """Consume a reset token and set a new password."""
    employee_id = consume_reset_token(db, data.token)
    if not employee_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    pw_hash = hash_password(data.password)
    now = datetime.now().isoformat()
    db.execute(
        "UPDATE employees SET password_hash = %s, updated_at = %s WHERE id = %s",
        (pw_hash, now, employee_id),
    )
    # Invalidate all existing sessions so they must log in with new password
    db.execute("DELETE FROM sessions WHERE employee_id = %s", (employee_id,))
    db.commit()

    return {"success": True}
