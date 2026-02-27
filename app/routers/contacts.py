from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db
from ..models.contact import ContactCreate, ContactNoteCreate, ContactNoteResponse, ContactResponse, ContactUpdate
from ..utils import generate_id

router = APIRouter()


@router.get("", response_model=list[ContactResponse])
def list_contacts(
    client_id: str | None = Query(None, description="Filter by client"),
    db=Depends(get_db),
):
    if client_id:
        rows = db.execute(
            "SELECT * FROM contacts WHERE client_id = %s AND deleted_at IS NULL ORDER BY name",
            (client_id,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM contacts WHERE deleted_at IS NULL ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


_NOTE_SELECT = (
    "SELECT n.id, n.contact_id, n.author_id, n.content, n.created_at, "
    "e.first_name || ' ' || e.last_name AS author_name, "
    "e.avatar_url AS author_avatar_url "
    "FROM contact_notes n "
    "LEFT JOIN employees e ON n.author_id = e.id "
)


@router.get("/notes/{note_id}", response_model=ContactNoteResponse)
def get_contact_note(note_id: str, db=Depends(get_db)):
    row = db.execute(_NOTE_SELECT + "WHERE n.id = %s", (note_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(row)


@router.delete("/notes/{note_id}")
def delete_contact_note(note_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM contact_notes WHERE id = %s", (note_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    db.execute("DELETE FROM contact_notes WHERE id = %s", (note_id,))
    db.commit()
    return {"success": True}


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM contacts WHERE id = %s AND deleted_at IS NULL", (contact_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")
    return dict(row)


@router.post("", response_model=ContactResponse, status_code=201)
def create_contact(data: ContactCreate, db=Depends(get_db)):
    contact_id = generate_id("ct-")
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO contacts (id, name, email, phone, role, notes, client_id, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (contact_id, data.name, data.email, data.phone, data.role, data.notes, data.client_id, now, now),
    )
    db.commit()
    return {
        "id": contact_id, "name": data.name, "email": data.email,
        "phone": data.phone, "role": data.role, "notes": data.notes, "client_id": data.client_id,
        "created_at": now, "updated_at": now,
    }


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: str, data: ContactUpdate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM contacts WHERE id = %s AND deleted_at IS NULL", (contact_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")

    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    if not updates:
        return dict(existing)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [contact_id]
    db.execute(f"UPDATE contacts SET {set_clause} WHERE id = %s", values)
    db.commit()

    row = db.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,)).fetchone()
    return dict(row)


@router.delete("/{contact_id}")
def delete_contact(contact_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM contacts WHERE id = %s AND deleted_at IS NULL", (contact_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")

    now = datetime.now().isoformat()
    db.execute("UPDATE contacts SET deleted_at = %s WHERE id = %s", (now, contact_id))
    db.commit()
    return {"success": True}


# --- Contact Notes ---


@router.get("/{contact_id}/notes", response_model=list[ContactNoteResponse])
def list_contact_notes(contact_id: str, db=Depends(get_db)):
    rows = db.execute(
        _NOTE_SELECT + "WHERE n.contact_id = %s ORDER BY n.created_at DESC",
        (contact_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/{contact_id}/notes", response_model=ContactNoteResponse, status_code=201)
def add_contact_note(contact_id: str, data: ContactNoteCreate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM contacts WHERE id = %s AND deleted_at IS NULL", (contact_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")

    note_id = generate_id("ctnote-")
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO contact_notes (id, contact_id, author_id, content, created_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (note_id, contact_id, data.author_id, data.content, now),
    )
    db.commit()

    row = db.execute(_NOTE_SELECT + "WHERE n.id = %s", (note_id,)).fetchone()
    return dict(row)
