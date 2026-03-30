import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db
from ..models.wiki_note import WikiNoteCreate, WikiNoteResponse, WikiNoteUpdate
from ..utils import generate_id

_root = Path(__file__).resolve().parent.parent.parent
_IMAGE_RE = re.compile(r'!\[.*?\]\((/uploads/images/[^)]+)\)')

router = APIRouter()

_SELECT = (
    "SELECT w.id, w.title, w.content, w.category, "
    "w.created_by, w.updated_by, w.created_at, w.updated_at, "
    "e1.first_name || ' ' || e1.last_name AS created_by_name, "
    "e2.first_name || ' ' || e2.last_name AS updated_by_name "
    "FROM wiki_notes w "
    "LEFT JOIN employees e1 ON w.created_by = e1.id "
    "LEFT JOIN employees e2 ON w.updated_by = e2.id "
    "WHERE w.deleted_at IS NULL "
)


@router.get("/categories")
def list_categories(db=Depends(get_db)):
    rows = db.execute(
        "SELECT DISTINCT category FROM wiki_notes "
        "WHERE deleted_at IS NULL ORDER BY category"
    ).fetchall()
    return [r["category"] for r in rows]


@router.get("", response_model=list[WikiNoteResponse])
def list_notes(
    q: str | None = Query(None, description="Search title and content"),
    category: str | None = Query(None, description="Filter by category"),
    db=Depends(get_db),
):
    sql = _SELECT
    params: list = []

    if q:
        like = f"%{q}%"
        sql += "AND (w.title ILIKE %s OR w.content ILIKE %s) "
        params.extend([like, like])

    if category:
        sql += "AND w.category = %s "
        params.append(category)

    sql += "ORDER BY w.updated_at DESC"
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@router.get("/{note_id}", response_model=WikiNoteResponse)
def get_note(note_id: str, db=Depends(get_db)):
    row = db.execute(_SELECT + "AND w.id = %s", (note_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(row)


@router.post("", response_model=WikiNoteResponse, status_code=201)
def create_note(data: WikiNoteCreate, db=Depends(get_db)):
    note_id = generate_id("wiki-")
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO wiki_notes (id, title, content, category, created_by, updated_by, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (note_id, data.title, data.content, data.category, data.created_by, data.created_by, now, now),
    )
    db.commit()

    row = db.execute(_SELECT + "AND w.id = %s", (note_id,)).fetchone()
    return dict(row)


@router.patch("/{note_id}", response_model=WikiNoteResponse)
def update_note(note_id: str, data: WikiNoteUpdate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM wiki_notes WHERE id = %s AND deleted_at IS NULL", (note_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        row = db.execute(_SELECT + "AND w.id = %s", (note_id,)).fetchone()
        return dict(row)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [note_id]
    db.execute(f"UPDATE wiki_notes SET {set_clause} WHERE id = %s", values)
    db.commit()

    row = db.execute(_SELECT + "AND w.id = %s", (note_id,)).fetchone()
    return dict(row)


@router.delete("/{note_id}")
def delete_note(note_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id, content FROM wiki_notes WHERE id = %s AND deleted_at IS NULL", (note_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    # Delete attached images from disk
    for match in _IMAGE_RE.finditer(existing["content"] or ""):
        img_path = _root / match.group(1).lstrip("/")
        img_path.unlink(missing_ok=True)

    now = datetime.now().isoformat()
    db.execute("UPDATE wiki_notes SET deleted_at = %s WHERE id = %s", (now, note_id))
    db.commit()
    return {"success": True}
