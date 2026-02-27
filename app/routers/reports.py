from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from ..database import get_db

router = APIRouter()


@router.get("/weekly-activity")
def get_weekly_activity(
    weeks_ago: int = Query(0, ge=0, le=52),
    db=Depends(get_db),
):
    """Return structured weekly activity data for team review.

    weeks_ago=0 means current week (Mon-Sun).
    weeks_ago=1 means last week, etc.
    """
    # Calculate week boundaries (Monday to Sunday)
    today = datetime.now().date()
    days_since_monday = today.weekday()  # 0=Mon, 6=Sun
    this_monday = today - timedelta(days=days_since_monday)
    week_start = this_monday - timedelta(weeks=weeks_ago)
    week_end = week_start + timedelta(days=7)

    start_str = week_start.isoformat()
    end_str = week_end.isoformat()

    # --- Activity log entries for this week ---
    activity_rows = db.execute(
        "SELECT a.*, "
        "COALESCE(e.first_name || ' ' || e.last_name, 'System') AS actor_name, "
        "p.name AS project_name "
        "FROM activity_log a "
        "LEFT JOIN employees e ON a.actor_id = e.id "
        "LEFT JOIN projects p ON a.project_id = p.id "
        "WHERE a.created_at >= %s AND a.created_at < %s "
        "ORDER BY a.created_at DESC",
        (start_str, end_str),
    ).fetchall()
    activity = [dict(r) for r in activity_rows]

    # --- Group activity by employee ---
    by_employee = {}
    for row in activity:
        name = row["actor_name"]
        if name not in by_employee:
            by_employee[name] = []
        by_employee[name].append({
            "action": row["action"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "project_name": row["project_name"],
            "metadata": row["metadata"],
            "created_at": row["created_at"],
        })

    # --- Active projects ---
    active_rows = db.execute(
        "SELECT p.id, p.name, p.status, p.job_code, p.project_number, "
        "c.name AS client_name, c.company AS client_company "
        "FROM projects p "
        "LEFT JOIN clients c ON p.client_id = c.id "
        "WHERE p.deleted_at IS NULL AND p.status NOT IN ('complete', 'paid') "
        "ORDER BY p.created_at DESC"
    ).fetchall()
    active_projects = [dict(r) for r in active_rows]

    # --- Summary stats from activity log ---
    stats_row = db.execute(
        "SELECT "
        "COUNT(*) FILTER (WHERE entity_type = 'proposal' AND action = 'created') AS proposals_created, "
        "COUNT(*) FILTER (WHERE entity_type = 'proposal' AND action = 'sent') AS proposals_sent, "
        "COUNT(*) FILTER (WHERE entity_type = 'invoice' AND action = 'created') AS invoices_created, "
        "COUNT(*) FILTER (WHERE entity_type = 'invoice' AND action = 'sent') AS invoices_sent, "
        "COUNT(*) FILTER (WHERE entity_type = 'invoice' AND action = 'paid') AS invoices_paid, "
        "COUNT(*) FILTER (WHERE entity_type = 'project_task' AND action = 'completed') AS tasks_completed, "
        "COUNT(*) FILTER (WHERE entity_type = 'project_task' AND action = 'created') AS tasks_created, "
        "COUNT(*) FILTER (WHERE entity_type IN ('project_note', 'task_note') AND action = 'created') AS notes_written, "
        "COUNT(*) FILTER (WHERE entity_type = 'project' AND action = 'created') AS projects_created, "
        "COUNT(*) FILTER (WHERE entity_type = 'contract' AND action = 'created') AS contracts_created "
        "FROM activity_log "
        "WHERE created_at >= %s AND created_at < %s",
        (start_str, end_str),
    ).fetchone()
    summary = dict(stats_row) if stats_row else {}

    return {
        "week_start": start_str,
        "week_end": end_str,
        "weeks_ago": weeks_ago,
        "summary": summary,
        "active_projects": active_projects,
        "activity_by_employee": by_employee,
        "recent_activity": activity,
    }
