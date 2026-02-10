import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a short unique ID, matching db/init_db.py pattern."""
    short_id = uuid.uuid4().hex[:8]
    return f"{prefix}{short_id}" if prefix else short_id


def next_invoice_number(db, project_id: str) -> str:
    """Generate the next invoice number for a project (e.g., JBHL21-4)."""
    last = db.execute(
        "SELECT invoice_number FROM invoices WHERE project_id = %s ORDER BY created_at DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    if last and last["invoice_number"]:
        parts = last["invoice_number"].rsplit("-", 1)
        next_num = int(parts[-1]) + 1 if len(parts) > 1 and parts[-1].isdigit() else 1
    else:
        next_num = 1
    return f"{project_id}-{next_num}"
