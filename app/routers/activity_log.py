from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import settings
from ..database import get_db
from ..models.activity_log import PathMappingCreate, OverrideCreate
from ..services.loki_client import query_loki
from ..services.activity_mapper import resolve_projects
from ..utils import generate_id

router = APIRouter()


@router.get("")
def get_activity_log(
    employee_id: str = Query(...),
    date_from: str = Query(...),
    date_to: str = Query(...),
    db=Depends(get_db),
):
    """Get unified activity feed for an employee over a date range."""
    # Look up Loki alias from user_settings
    row = db.execute(
        "SELECT value FROM user_settings WHERE employee_id = %s AND key = 'loki_alias'",
        (employee_id,),
    ).fetchone()
    loki_alias = row["value"] if row else None

    items = []

    # Query Loki if alias is configured
    if loki_alias and settings.loki_url:
        loki_items = query_loki(settings.loki_url, loki_alias, date_from, date_to)
        for item in loki_items:
            item["employee_id"] = employee_id
        items.extend(loki_items)

    # Resolve project assignments
    items = resolve_projects(items, employee_id, db)

    # Sort by timestamp descending
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return items


@router.get("/mappings")
def list_mappings(db=Depends(get_db)):
    """List all active path-to-project mappings."""
    rows = db.execute(
        """SELECT m.*, p.name AS project_name
           FROM activity_path_mappings m
           JOIN projects p ON p.id = m.project_id
           WHERE m.deleted_at IS NULL
           ORDER BY m.created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/mappings")
def create_mapping(data: PathMappingCreate, db=Depends(get_db)):
    """Create a path-to-project mapping."""
    mapping_id = generate_id("apm-")
    db.execute(
        """INSERT INTO activity_path_mappings (id, pattern, source, project_id, created_at)
           VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
           ON CONFLICT (pattern, source) WHERE deleted_at IS NULL DO UPDATE
           SET project_id = EXCLUDED.project_id""",
        (mapping_id, data.pattern, data.source, data.project_id),
    )
    db.commit()
    return {"id": mapping_id, "pattern": data.pattern, "source": data.source, "project_id": data.project_id}


@router.delete("/mappings/{mapping_id}")
def delete_mapping(mapping_id: str, db=Depends(get_db)):
    """Soft-delete a path mapping."""
    db.execute(
        "UPDATE activity_path_mappings SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s",
        (mapping_id,),
    )
    db.commit()
    return {"ok": True}


@router.post("/overrides")
def create_override(data: OverrideCreate, db=Depends(get_db)):
    """Override the project assignment for a specific activity item."""
    override_id = generate_id("ao-")
    db.execute(
        """INSERT INTO activity_overrides (id, source, source_key, employee_id, project_id, created_at)
           VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
           ON CONFLICT (source, source_key, employee_id) DO UPDATE
           SET project_id = EXCLUDED.project_id""",
        (override_id, data.source, data.source_key, data.employee_id, data.project_id),
    )

    # If "remember" is set, also create a path mapping
    if data.remember and data.pattern and data.project_id:
        mapping_id = generate_id("apm-")
        db.execute(
            """INSERT INTO activity_path_mappings (id, pattern, source, project_id, created_at)
               VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
               ON CONFLICT (pattern, source) WHERE deleted_at IS NULL DO UPDATE
               SET project_id = EXCLUDED.project_id""",
            (mapping_id, data.pattern, data.source, data.project_id),
        )

    db.commit()
    return {"ok": True}
