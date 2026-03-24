import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..auth import hash_api_key, require_auth
from ..database import get_db
from ..models.api_key import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse
from ..utils import generate_id

router = APIRouter()

API_KEY_PREFIX = "pod_"


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=201)
def create_api_key(
    data: ApiKeyCreate,
    employee: dict = Depends(require_auth),
    db=Depends(get_db),
):
    raw_key = API_KEY_PREFIX + secrets.token_urlsafe(32)
    key_hash = hash_api_key(raw_key)
    key_id = generate_id("ak-")
    now = datetime.now().isoformat()

    db.execute(
        "INSERT INTO api_keys (id, employee_id, key_hash, name, created_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (key_id, employee["id"], key_hash, data.name, now),
    )
    db.commit()

    return {
        "id": key_id,
        "name": data.name,
        "raw_key": raw_key,
        "created_at": now,
        "last_used_at": None,
        "expires_at": None,
    }


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    employee: dict = Depends(require_auth),
    db=Depends(get_db),
):
    rows = db.execute(
        "SELECT id, name, created_at, last_used_at, expires_at "
        "FROM api_keys "
        "WHERE employee_id = %s AND deleted_at IS NULL "
        "ORDER BY created_at DESC",
        (employee["id"],),
    ).fetchall()
    return [dict(r) for r in rows]


@router.delete("/api-keys/{key_id}")
def delete_api_key(
    key_id: str,
    employee: dict = Depends(require_auth),
    db=Depends(get_db),
):
    existing = db.execute(
        "SELECT id FROM api_keys "
        "WHERE id = %s AND employee_id = %s AND deleted_at IS NULL",
        (key_id, employee["id"]),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="API key not found")

    now = datetime.now().isoformat()
    db.execute(
        "UPDATE api_keys SET deleted_at = %s WHERE id = %s",
        (now, key_id),
    )
    db.commit()
    return {"success": True}
