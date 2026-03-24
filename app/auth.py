import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Cookie, Depends, Header, HTTPException

from .database import PgConnection, get_db

logger = logging.getLogger(__name__)

SESSION_COOKIE = "session_token"
SESSION_DAYS = 30
RESET_TOKEN_HOURS = 1


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_session(db: PgConnection, employee_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    db.execute(
        "INSERT INTO sessions (token, employee_id, expires_at) VALUES (%s, %s, %s)",
        (token, employee_id, expires.isoformat()),
    )
    db.commit()
    return token


def get_current_employee(
    session_token: str | None = Cookie(None, alias=SESSION_COOKIE),
    authorization: str | None = Header(None),
    db: PgConnection = Depends(get_db),
) -> dict | None:
    if not session_token:
        pass
    else:
        row = db.execute(
            "SELECT e.id, e.first_name, e.last_name, e.email, e.avatar_url, e.is_active "
            "FROM sessions s JOIN employees e ON s.employee_id = e.id "
            "WHERE s.token = %s AND s.expires_at > NOW() AND e.deleted_at IS NULL "
            "AND e.is_active = TRUE",
            (session_token,),
        ).fetchone()
        if row:
            # Sliding expiry: best-effort, don't fail the request if this fails
            try:
                new_expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
                db.execute(
                    "UPDATE sessions SET expires_at = %s WHERE token = %s",
                    (new_expires.isoformat(), session_token),
                )
                db.commit()
            except Exception:
                logger.warning("Failed to extend session expiry", exc_info=True)
            return dict(row)

    # Fall back to API key from Authorization: Bearer <key>
    if authorization and authorization.startswith("Bearer "):
        raw_key = authorization[7:]
        key_hash = hash_api_key(raw_key)
        row = db.execute(
            "SELECT e.id, e.first_name, e.last_name, e.email, e.avatar_url, e.is_active, ak.id AS api_key_id "
            "FROM api_keys ak JOIN employees e ON ak.employee_id = e.id "
            "WHERE ak.key_hash = %s AND ak.deleted_at IS NULL "
            "AND (ak.expires_at IS NULL OR ak.expires_at > NOW()) "
            "AND e.deleted_at IS NULL AND e.is_active = TRUE",
            (key_hash,),
        ).fetchone()
        if row:
            api_key_id = row["api_key_id"]
            # Update last_used_at (best-effort)
            try:
                db.execute(
                    "UPDATE api_keys SET last_used_at = NOW() WHERE id = %s",
                    (api_key_id,),
                )
                db.commit()
            except Exception:
                logger.warning("Failed to update api_key last_used_at", exc_info=True)
            result = dict(row)
            del result["api_key_id"]  # Don't leak internal field
            return result

    return None


def require_auth(
    employee: dict | None = Depends(get_current_employee),
) -> dict:
    if employee is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return employee


def create_reset_token(db: PgConnection, employee_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_HOURS)
    db.execute(
        "INSERT INTO password_resets (token, employee_id, expires_at) VALUES (%s, %s, %s)",
        (token, employee_id, expires.isoformat()),
    )
    db.commit()
    return token


def consume_reset_token(db: PgConnection, token: str) -> str | None:
    """Atomically validate and consume a reset token. Returns employee_id or None.

    Does NOT commit — caller must commit so the token consumption and
    password update happen in the same transaction.
    """
    row = db.execute(
        "UPDATE password_resets SET used_at = NOW() "
        "WHERE token = %s AND expires_at > NOW() AND used_at IS NULL "
        "RETURNING employee_id",
        (token,),
    ).fetchone()
    if not row:
        return None
    return row["employee_id"]
