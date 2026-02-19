import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a short unique ID, matching db/init_db.py pattern."""
    short_id = uuid.uuid4().hex[:8]
    return f"{prefix}{short_id}" if prefix else short_id


def next_project_number(db) -> str:
    """Generate the next project number in YY-NNN format (e.g., 26-001)."""
    from datetime import datetime
    yr = datetime.now().strftime("%y")
    prefix = f"{yr}-"
    last = db.execute(
        "SELECT project_number FROM projects WHERE project_number LIKE %s ORDER BY project_number DESC LIMIT 1",
        (prefix + "%",),
    ).fetchone()
    if last and last["project_number"]:
        seq = int(last["project_number"].split("-", 1)[1]) + 1
    else:
        seq = 1
    return f"{yr}-{seq:03d}"


def next_invoice_number(db, project_id: str) -> str:
    """Generate the next invoice number for a project using job_code (e.g., DRH-SilverPeaks-1)."""
    proj = db.execute(
        "SELECT job_code, project_number FROM projects WHERE id = %s", (project_id,)
    ).fetchone()
    prefix = (proj["job_code"] or proj["project_number"]) if proj else project_id

    # Check ALL invoices (including deleted) to avoid unique constraint collisions
    rows = db.execute(
        "SELECT invoice_number FROM invoices WHERE project_id = %s",
        (project_id,),
    ).fetchall()
    max_num = 0
    for row in rows:
        inv_num = row["invoice_number"] or ""
        parts = inv_num.rsplit("-", 1)
        if len(parts) > 1 and parts[-1].isdigit():
            max_num = max(max_num, int(parts[-1]))
    return f"{prefix}-{max_num + 1}"
