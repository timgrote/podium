from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db
from ..models.client import ClientCreate, ClientNoteCreate, ClientNoteResponse, ClientResponse, ClientUpdate
from ..utils import generate_id

router = APIRouter()


@router.get("", response_model=list[ClientResponse])
def list_clients(
    q: str | None = Query(None, description="Search by name, email, or company"),
    db=Depends(get_db),
):
    if q:
        like = f"%{q}%"
        rows = db.execute(
            "SELECT * FROM clients WHERE deleted_at IS NULL "
            "AND (name ILIKE %s OR email ILIKE %s OR company ILIKE %s) ORDER BY name",
            (like, like, like),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM clients WHERE deleted_at IS NULL ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


_NOTE_SELECT = (
    "SELECT n.id, n.client_id, n.author_id, n.content, n.created_at, "
    "e.first_name || ' ' || e.last_name AS author_name, "
    "e.avatar_url AS author_avatar_url "
    "FROM client_notes n "
    "LEFT JOIN employees e ON n.author_id = e.id "
)


@router.get("/notes/{note_id}", response_model=ClientNoteResponse)
def get_client_note(note_id: str, db=Depends(get_db)):
    row = db.execute(_NOTE_SELECT + "WHERE n.id = %s", (note_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(row)


@router.delete("/notes/{note_id}")
def delete_client_note(note_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM client_notes WHERE id = %s", (note_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    db.execute("DELETE FROM client_notes WHERE id = %s", (note_id,))
    db.commit()
    return {"success": True}


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM clients WHERE id = %s AND deleted_at IS NULL", (client_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return dict(row)


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(data: ClientCreate, db=Depends(get_db)):
    client_id = generate_id("c-")
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO clients (id, name, accounting_email, company, phone, address, notes, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (client_id, data.name, data.email, data.company, data.phone, data.address, data.notes, now, now),
    )
    db.commit()
    return {
        "id": client_id, "name": data.name, "accounting_email": data.email, "company": data.company,
        "phone": data.phone, "address": data.address, "notes": data.notes,
        "created_at": now, "updated_at": now,
    }


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(client_id: str, data: ClientUpdate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM clients WHERE id = %s AND deleted_at IS NULL", (client_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return dict(existing)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [client_id]
    db.execute(f"UPDATE clients SET {set_clause} WHERE id = %s", values)
    db.commit()

    row = db.execute("SELECT * FROM clients WHERE id = %s", (client_id,)).fetchone()
    return dict(row)


@router.delete("/{client_id}")
def delete_client(client_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM clients WHERE id = %s AND deleted_at IS NULL", (client_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    now = datetime.now().isoformat()
    db.execute("UPDATE clients SET deleted_at = %s WHERE id = %s", (now, client_id))
    db.commit()
    return {"success": True}


# --- Client Notes ---


@router.get("/{client_id}/notes", response_model=list[ClientNoteResponse])
def list_client_notes(client_id: str, db=Depends(get_db)):
    rows = db.execute(
        _NOTE_SELECT + "WHERE n.client_id = %s ORDER BY n.created_at DESC",
        (client_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/{client_id}/notes", response_model=ClientNoteResponse, status_code=201)
def add_client_note(client_id: str, data: ClientNoteCreate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM clients WHERE id = %s AND deleted_at IS NULL", (client_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    note_id = generate_id("cnote-")
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO client_notes (id, client_id, author_id, content, created_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (note_id, client_id, data.author_id, data.content, now),
    )
    db.commit()

    row = db.execute(_NOTE_SELECT + "WHERE n.id = %s", (note_id,)).fetchone()
    return dict(row)
