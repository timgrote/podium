from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from ..database import get_db
from ..models.contact import ContactCreate, ContactNoteCreate, ContactNoteResponse, ContactResponse, ContactUpdate
from ..utils import generate_id
from ..vcf_parser import parse_vcards

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


@router.post("/import")
async def import_vcf(
    file: UploadFile = File(...),
    commit: bool = Query(False, description="If true, write changes; otherwise preview only"),
    db=Depends(get_db),
):
    """Import contacts from an uploaded .vcf file.

    Matches on email (case-insensitive): unmatched cards are created, matched
    cards update the existing contact with any non-empty fields from the card.
    Company (ORG) is matched to an existing client by name, or created (with the
    card's address) when there's no match. With commit=false, returns the
    resolved plan without writing.
    """
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", "replace")

    cards = parse_vcards(text)
    if not cards:
        raise HTTPException(status_code=400, detail="No contacts found in file")

    # Existing contacts indexed by lowercased email for matching.
    existing_rows = db.execute(
        "SELECT id, name, email, phone, role, notes, client_id FROM contacts WHERE deleted_at IS NULL"
    ).fetchall()
    by_email = {r["email"].lower(): dict(r) for r in existing_rows if r["email"]}

    # Companies indexed by lowercased name for ORG matching.
    client_rows = db.execute(
        "SELECT id, name FROM clients WHERE deleted_at IS NULL"
    ).fetchall()
    clients_by_name = {r["name"].lower(): r["id"] for r in client_rows}
    created_company_names: set[str] = set()
    now = datetime.now().isoformat()

    def resolve_company(org: str | None, address: str | None) -> tuple[str | None, bool]:
        """Return (client_id, is_new) for an ORG name, creating the company if needed."""
        if not org:
            return None, False
        key = org.lower()
        if key in clients_by_name:
            return clients_by_name[key], False
        if not commit:
            return None, True  # would be created
        new_id = generate_id("c-")
        db.execute(
            "INSERT INTO clients (id, name, address, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (new_id, org, address, now, now),
        )
        clients_by_name[key] = new_id
        created_company_names.add(key)
        return new_id, True

    plan: list[dict] = []
    fields = ("email", "phone", "role", "notes")
    for card in cards:
        org = card.get("org")
        client_id, company_new = resolve_company(org, card.get("address"))
        match = by_email.get(card["email"].lower()) if card.get("email") else None
        if not commit and company_new and org:
            created_company_names.add(org.lower())

        plan.append({
            "name": card["name"],
            "email": card.get("email"),
            "phone": card.get("phone"),
            "role": card.get("role"),
            "notes": card.get("notes"),
            "company_name": org,
            "company_new": company_new,
            "client_id": client_id,
            "action": "update" if match else "create",
            "existing_id": match["id"] if match else None,
        })

        if not commit:
            continue

        if match:
            updates = {f: card.get(f) for f in fields if card.get(f)}
            # Only set company if the contact doesn't already have one.
            if client_id and not match["client_id"]:
                updates["client_id"] = client_id
            if updates:
                updates["updated_at"] = now
                set_clause = ", ".join(f"{k} = %s" for k in updates)
                db.execute(
                    f"UPDATE contacts SET {set_clause} WHERE id = %s",
                    list(updates.values()) + [match["id"]],
                )
        else:
            db.execute(
                "INSERT INTO contacts (id, name, email, phone, role, notes, client_id, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (generate_id("ct-"), card["name"], card.get("email"), card.get("phone"),
                 card.get("role"), card.get("notes"), client_id, now, now),
            )

    if commit:
        db.commit()

    created = sum(1 for e in plan if e["action"] == "create")
    updated = sum(1 for e in plan if e["action"] == "update")
    return {
        "contacts": plan,
        "summary": {
            "create": created,
            "update": updated,
            "total": len(plan),
            "new_companies": len(created_company_names),
        },
        "committed": commit,
    }


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


# --- Contact Projects ---


@router.get("/{contact_id}/projects")
def list_contact_projects(contact_id: str, db=Depends(get_db)):
    """Get projects where this contact is listed in project_contacts or as client_pm."""
    rows = db.execute(
        "SELECT DISTINCT p.id, p.name AS project_name, p.job_code, p.status "
        "FROM projects p "
        "LEFT JOIN project_contacts pc ON pc.project_id = p.id AND pc.contact_id = %s "
        "WHERE (pc.contact_id = %s OR p.client_pm_id = %s) "
        "AND p.deleted_at IS NULL "
        "ORDER BY p.name",
        (contact_id, contact_id, contact_id),
    ).fetchall()
    return [dict(r) for r in rows]


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
