"""Activity logging for weekly reviews and audit trails.

Usage from any router:
    from ..activity_log import log_activity
    log_activity(db, actor_id="emp-abc", action="created", entity_type="invoice",
                 entity_id="inv-123", project_id="JBHL21")
"""

import json
import logging

from .utils import generate_id

logger = logging.getLogger(__name__)


def log_activity(
    db,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    project_id: str | None = None,
    actor_id: str | None = None,
    metadata: dict | None = None,
):
    """Insert an activity log entry. Best-effort — never raises."""
    try:
        db.execute(
            "INSERT INTO activity_log (id, actor_id, action, entity_type, entity_id, project_id, metadata) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                generate_id("act-"),
                actor_id,
                action,
                entity_type,
                entity_id,
                project_id,
                json.dumps(metadata) if metadata else None,
            ),
        )
    except Exception:
        logger.warning("Failed to log activity: %s %s %s", action, entity_type, entity_id, exc_info=True)
