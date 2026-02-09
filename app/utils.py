import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a short unique ID, matching db/init_db.py pattern."""
    short_id = uuid.uuid4().hex[:8]
    return f"{prefix}{short_id}" if prefix else short_id
