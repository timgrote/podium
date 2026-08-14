"""Overview endpoint: unfinished tasks + deliverables for a set of projects."""
from fastapi import APIRouter, Depends, Query

from ..database import get_db

router = APIRouter()


@router.get("/overview/items")
def get_overview_items(
    project_ids: str = Query(..., description="Comma-separated project IDs"),
    db=Depends(get_db),
):
    """Return unfinished tasks and deliverables for the given projects.

    Tasks: status NOT IN ('done', 'canceled', 'archived')
    Deliverables: status != 'accepted'
    """
    ids = [p.strip() for p in project_ids.split(",") if p.strip()]
    if not ids:
        return {"tasks": [], "deliverables": []}

    # --- Unfinished tasks ---
    task_rows = db.execute(
        "SELECT t.id, t.title, t.status, t.priority, t.due_date, "
        "       t.project_id, p.name AS project_name, "
        "       c.id AS client_id, c.name AS client_name "
        "FROM project_tasks t "
        "JOIN projects p ON p.id = t.project_id AND p.deleted_at IS NULL "
        "LEFT JOIN clients c ON c.id = p.client_id AND c.deleted_at IS NULL "
        "WHERE t.deleted_at IS NULL "
        "  AND t.parent_id IS NULL "
        "  AND t.status NOT IN ('done', 'canceled', 'archived') "
        "  AND t.project_id = ANY(%s) "
        "ORDER BY t.due_date NULLS LAST, t.priority DESC NULLS LAST",
        (ids,),
    ).fetchall()

    # Batch assignee lookup
    task_ids = [r["id"] for r in task_rows]
    assignees_map: dict[str, list[dict]] = {tid: [] for tid in task_ids}
    if task_ids:
        assignee_rows = db.execute(
            "SELECT a.task_id, e.id, e.first_name, e.last_name "
            "FROM project_task_assignees a "
            "JOIN employees e ON e.id = a.employee_id AND e.deleted_at IS NULL "
            "WHERE a.task_id = ANY(%s)",
            (task_ids,),
        ).fetchall()
        for ar in assignee_rows:
            assignees_map.setdefault(ar["task_id"], []).append(
                {"id": ar["id"], "first_name": ar["first_name"], "last_name": ar["last_name"]}
            )

    tasks = []
    for r in task_rows:
        tasks.append({
            "id": r["id"],
            "kind": "task",
            "title": r["title"],
            "status": r["status"],
            "priority": r["priority"],
            "due_date": str(r["due_date"]) if r["due_date"] else None,
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "client_id": r["client_id"],
            "client_name": r["client_name"],
            "assignees": assignees_map.get(r["id"], []),
        })

    # --- Unfinished deliverables ---
    del_rows = db.execute(
        "SELECT d.id, d.name AS title, d.status, d.progress_percent, d.deadline, "
        "       d.project_id, p.name AS project_name, "
        "       c.id AS client_id, c.name AS client_name "
        "FROM project_deliverables d "
        "JOIN projects p ON p.id = d.project_id AND p.deleted_at IS NULL "
        "LEFT JOIN clients c ON c.id = p.client_id AND c.deleted_at IS NULL "
        "WHERE d.deleted_at IS NULL "
        "  AND d.status != 'accepted' "
        "  AND d.project_id = ANY(%s) "
        "ORDER BY d.deadline NULLS LAST",
        (ids,),
    ).fetchall()

    deliverables = []
    for r in del_rows:
        deliverables.append({
            "id": r["id"],
            "kind": "deliverable",
            "title": r["title"],
            "status": r["status"],
            "progress_percent": float(r["progress_percent"]) if r["progress_percent"] is not None else 0,
            "deadline": str(r["deadline"]) if r["deadline"] else None,
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "client_id": r["client_id"],
            "client_name": r["client_name"],
        })

    return {"tasks": tasks, "deliverables": deliverables}
