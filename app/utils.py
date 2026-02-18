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
    """Generate the next invoice number for a project using project_number (e.g., 26-001-1)."""
    # Look up the project_number for this project
    proj = db.execute(
        "SELECT project_number FROM projects WHERE id = %s", (project_id,)
    ).fetchone()
    prefix = proj["project_number"] if proj and proj["project_number"] else project_id

    last = db.execute(
        "SELECT invoice_number FROM invoices WHERE project_id = %s ORDER BY created_at DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    if last and last["invoice_number"]:
        parts = last["invoice_number"].rsplit("-", 1)
        next_num = int(parts[-1]) + 1 if len(parts) > 1 and parts[-1].isdigit() else 1
    else:
        next_num = 1
    return f"{prefix}-{next_num}"
