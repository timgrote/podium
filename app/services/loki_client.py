import hashlib
import json
import logging
from datetime import datetime

import httpx

logger = logging.getLogger("conductor")


def query_loki(loki_url: str, user_alias: str, date_from: str, date_to: str, api_key: str = "") -> list[dict]:
    """Query Loki for Raindrop drawing close events for a given user and date range."""
    # Filter for Drawing Closed events containing this user's alias
    logql = '{app="raindrop"} |= "Drawing Closed" |= "' + user_alias + '"'

    start_dt = datetime.fromisoformat(f"{date_from}T00:00:00")
    end_dt = datetime.fromisoformat(f"{date_to}T23:59:59")
    start_ns = str(int(start_dt.timestamp() * 1e9))
    end_ns = str(int(end_dt.timestamp() * 1e9))

    url = f"{loki_url}/loki/api/v1/query_range"
    params = {
        "query": logql,
        "start": start_ns,
        "end": end_ns,
        "limit": 5000,
    }

    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Loki query failed: {e}")
        return []

    return _parse_loki_response(data, user_alias)


def _parse_loki_response(data: dict, user_alias: str) -> list[dict]:
    """Parse Loki query_range response into normalized activity items."""
    items = []
    results = data.get("data", {}).get("result", [])

    for stream in results:
        for ts_ns, line in stream.get("values", []):
            try:
                entry = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue

            # Only Drawing Closed events
            action = entry.get("Action", "")
            if action != "Drawing Closed":
                continue

            drawing_name = entry.get("DrawingName", "Unknown")
            drawing_path = entry.get("DrawingPath", "")
            work_minutes = entry.get("TotalWorkMinutes", 0) or 0
            open_minutes = entry.get("TotalOpenMinutes", 0) or 0
            command_count = entry.get("CommandCount", 0) or 0
            raindrop_commands = entry.get("RaindropCommands", 0) or 0
            save_count = entry.get("SaveCount", 0) or 0

            # Parse timestamp from nanoseconds
            try:
                timestamp = datetime.fromtimestamp(int(ts_ns) / 1e9).isoformat()
            except (ValueError, OSError):
                timestamp = datetime.now().isoformat()

            # Deterministic ID
            raw = f"{ts_ns}:{user_alias}:{drawing_path}"
            item_id = "loki-" + hashlib.sha256(raw.encode()).hexdigest()[:12]

            # Build detail string
            detail_parts = []
            if work_minutes:
                detail_parts.append(f"{work_minutes:.0f} min active" if work_minutes >= 1 else f"{work_minutes:.1f} min active")
            if command_count:
                detail_parts.append(f"{command_count} cmds")
            if raindrop_commands:
                detail_parts.append(f"{raindrop_commands} Raindrop")
            if save_count:
                detail_parts.append(f"{save_count} saves")

            items.append({
                "id": item_id,
                "source": "loki",
                "timestamp": timestamp,
                "description": drawing_name,
                "detail": ", ".join(detail_parts) if detail_parts else None,
                "duration_minutes": float(work_minutes) if work_minutes else None,
                "source_path": drawing_path,
            })

    return items
