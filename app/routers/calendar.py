import logging

from datetime import date

from fastapi import APIRouter, Depends, Query

from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


def _assignees_for_tasks(db, task_ids: list[str]) -> dict[str, list[dict]]:
    """Return {task_id: [employee...]} for all given task ids in one query."""
    if not task_ids:
        return {}
    rows = db.execute(
        "SELECT a.task_id, e.id, e.first_name, e.last_name "
        "FROM project_task_assignees a "
        "JOIN employees e ON e.id = a.employee_id "
        "WHERE a.task_id = ANY(%s) AND e.deleted_at IS NULL",
        (task_ids,),
    ).fetchall()
    result: dict[str, list[dict]] = {tid: [] for tid in task_ids}
    for r in rows:
        emp = {"id": r["id"], "first_name": r["first_name"], "last_name": r["last_name"]}
        if emp["id"] not in (e["id"] for e in result[r["task_id"]]):
            result[r["task_id"]].append(emp)
    return result


def _date_range_clause(col: str, from_date, to_date) -> tuple[str, list]:
    """Build 'AND <col> >= %s [AND <col> <= %s]' plus params for a date filter."""
    clause = ""
    params: list = []
    if from_date is not None:
        clause += f" AND {col} >= %s"
        params.append(str(from_date))
    if to_date is not None:
        clause += f" AND {col} <= %s"
        params.append(str(to_date))
    return clause, params


@router.get("/calendar")
def get_calendar(
    from_date: date | None = Query(None, description="Inclusive lower bound (YYYY-MM-DD)"),
    to_date: date | None = Query(None, description="Inclusive upper bound (YYYY-MM-DD)"),
    db=Depends(get_db),
):
    """Return unified calendar items: task due dates + deliverable deadlines.

    Every item carries the metadata needed to filter client-side by priority,
    company (client) and assignee: kind, date, priority, project, client,
    status and assignees.
    """
    task_range, task_params = _date_range_clause("t.due_date", from_date, to_date)

    # --- Tasks with a due date ---
    task_sql = (
        "SELECT t.id, t.title, t.due_date AS date, t.priority, t.status, "
        "       p.id AS project_id, p.name AS project_name, p.client_id, "
        "       c.name AS client_name "
        "FROM project_tasks t "
        "JOIN projects p ON p.id = t.project_id AND p.deleted_at IS NULL "
        "LEFT JOIN clients c ON c.id = p.client_id AND c.deleted_at IS NULL "
        "WHERE t.deleted_at IS NULL AND t.parent_id IS NULL AND t.due_date IS NOT NULL"
        + task_range
        + " ORDER BY t.due_date ASC"
    )
    task_rows = db.execute(task_sql, tuple(task_params)).fetchall()

    assignees_by_task = _assignees_for_tasks(db, [r["id"] for r in task_rows])

    items = []
    for r in task_rows:
        items.append({
            "id": r["id"],
            "kind": "task",
            "title": r["title"],
            "date": str(r["date"]),
            "priority": r["priority"],
            "status": r["status"],
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "client_id": r["client_id"],
            "client_name": r["client_name"],
            "assignees": assignees_by_task.get(r["id"], []),
        })

    # --- Deliverables with a deadline ---
    del_range, del_params = _date_range_clause("d.deadline", from_date, to_date)
    del_sql = (
        "SELECT d.id, d.name AS title, d.deadline AS date, d.status, "
        "       d.progress_percent, d.updated_by, "
        "       p.id AS project_id, p.name AS project_name, p.client_id, "
        "       c.name AS client_name "
        "FROM project_deliverables d "
        "JOIN projects p ON p.id = d.project_id AND p.deleted_at IS NULL "
        "LEFT JOIN clients c ON c.id = p.client_id AND c.deleted_at IS NULL "
        "WHERE d.deleted_at IS NULL AND d.deadline IS NOT NULL"
        + del_range
        + " ORDER BY d.deadline ASC"
    )
    del_rows = db.execute(del_sql, tuple(del_params)).fetchall()

    for r in del_rows:
        assignees = []
        if r["updated_by"]:
            emp = db.execute(
                "SELECT id, first_name, last_name FROM employees WHERE id = %s AND deleted_at IS NULL",
                (r["updated_by"],),
            ).fetchone()
            if emp:
                assignees.append({"id": emp["id"], "first_name": emp["first_name"], "last_name": emp["last_name"]})
        items.append({
            "id": r["id"],
            "kind": "deliverable",
            "title": r["title"],
            "date": str(r["date"]),
            "priority": None,
            "status": r["status"],
            "progress_percent": r["progress_percent"],
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "client_id": r["client_id"],
            "client_name": r["client_name"],
            "assignees": assignees,
        })

    # Single merged, date-sorted list.
    items.sort(key=lambda i: i["date"])
    return items
