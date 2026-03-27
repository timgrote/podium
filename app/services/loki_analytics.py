import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import httpx

from ..config import settings

logger = logging.getLogger("conductor")


def query_loki_range(logql: str, start: datetime, end: datetime, limit: int = 5000) -> list[tuple[str, dict]]:
    """Query Loki and return (timestamp_ns, parsed_json) tuples."""
    url = f"{settings.loki_url}/loki/api/v1/query_range"
    params = {
        "query": logql,
        "start": str(int(start.timestamp() * 1e9)),
        "end": str(int(end.timestamp() * 1e9)),
        "limit": limit,
    }
    headers = {}
    if settings.loki_api_key:
        headers["X-API-Key"] = settings.loki_api_key

    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Loki analytics query failed: {e}")
        return []

    entries = []
    for stream in data.get("data", {}).get("result", []):
        for ts_ns, line in stream.get("values", []):
            try:
                entry = json.loads(line)
                entries.append((ts_ns, entry))
            except (json.JSONDecodeError, TypeError):
                continue
    return entries


def _extract_username(entry: dict) -> str:
    """Extract a clean username from EnvironmentUserName (e.g. 'FRAMEWORK-AI300\\tim' -> 'tim')."""
    env_user = entry.get("EnvironmentUserName", "")
    if "\\" in env_user:
        return env_user.split("\\")[-1].lower()
    return env_user.lower() or "unknown"


def _date_key(ts_ns: str) -> str:
    """Convert nanosecond timestamp to date string."""
    try:
        dt = datetime.fromtimestamp(int(ts_ns) / 1e9)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return "unknown"


def _hour_key(ts_ns: str) -> int:
    """Convert nanosecond timestamp to hour of day."""
    try:
        return datetime.fromtimestamp(int(ts_ns) / 1e9).hour
    except (ValueError, OSError):
        return 0


def aggregate_dashboard(entries: list[tuple[str, dict]], start_date: str, end_date: str) -> dict:
    """Aggregate Drawing Closed events into dashboard metrics."""
    # Per-day tracking
    daily_users: dict[str, set] = defaultdict(set)
    daily_sessions: Counter = Counter()
    daily_work_mins: dict[str, float] = defaultdict(float)

    # Per-user tracking
    user_sessions: Counter = Counter()
    user_work_mins: dict[str, float] = defaultdict(float)
    user_commands: dict[str, int] = defaultdict(int)
    user_raindrop_cmds: dict[str, int] = defaultdict(int)
    user_saves: dict[str, int] = defaultdict(int)
    user_drawings: dict[str, set] = defaultdict(set)

    # Global
    hourly: Counter = Counter()
    all_users: set = set()
    total_commands = 0
    total_raindrop = 0
    total_work_mins = 0.0
    total_open_mins = 0.0
    total_saves = 0
    all_drawings: set = set()

    for ts_ns, entry in entries:
        if entry.get("Action") != "Drawing Closed":
            continue

        user = _extract_username(entry)
        date = _date_key(ts_ns)
        hour = _hour_key(ts_ns)
        work = float(entry.get("TotalWorkMinutes", 0) or 0)
        open_mins = float(entry.get("TotalOpenMinutes", 0) or 0)
        cmds = int(entry.get("CommandCount", 0) or 0)
        rd_cmds = int(entry.get("RaindropCommands", 0) or 0)
        saves = int(entry.get("SaveCount", 0) or 0)
        drawing = entry.get("DrawingName", "")

        daily_users[date].add(user)
        daily_sessions[date] += 1
        daily_work_mins[date] += work

        user_sessions[user] += 1
        user_work_mins[user] += work
        user_commands[user] += cmds
        user_raindrop_cmds[user] += rd_cmds
        user_saves[user] += saves
        if drawing:
            user_drawings[user].add(drawing)

        hourly[hour] += 1
        all_users.add(user)
        total_commands += cmds
        total_raindrop += rd_cmds
        total_work_mins += work
        total_open_mins += open_mins
        total_saves += saves
        if drawing:
            all_drawings.add(drawing)

    total_sessions = sum(daily_sessions.values())

    # Build date range (fill in zero days)
    dates = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    while current <= end_dt:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    daily_active_users = [
        {"date": d, "count": len(daily_users.get(d, set())), "users": sorted(daily_users.get(d, set()))}
        for d in dates
    ]
    daily_sessions_list = [{"date": d, "count": daily_sessions.get(d, 0)} for d in dates]
    daily_work_hours_list = [{"date": d, "hours": round(daily_work_mins.get(d, 0) / 60, 1)} for d in dates]

    hourly_distribution = [{"hour": h, "count": hourly.get(h, 0)} for h in range(24)]

    user_stats = sorted(
        [
            {
                "user": u,
                "sessions": user_sessions[u],
                "work_hours": round(user_work_mins[u] / 60, 1),
                "commands": user_commands[u],
                "raindrop_commands": user_raindrop_cmds[u],
                "saves": user_saves[u],
                "unique_drawings": len(user_drawings[u]),
            }
            for u in all_users
        ],
        key=lambda x: x["work_hours"],
        reverse=True,
    )

    # Compute insights
    insights = []
    if user_stats:
        top = user_stats[0]
        insights.append(f"{top['user'].title()} is the most active user with {top['work_hours']}h")
    if any(h["count"] > 0 for h in hourly_distribution):
        peak = max(hourly_distribution, key=lambda x: x["count"])
        insights.append(f"Peak usage hour: {peak['hour']}:00")
    if total_sessions > 0:
        avg_session = round(total_work_mins / total_sessions, 1)
        insights.append(f"Average session: {avg_session} min active work")
    if total_open_mins > 0:
        productivity = round(total_work_mins / total_open_mins * 100, 1)
        insights.append(f"Productivity ratio: {productivity}% active time")
    if total_commands > 0:
        adoption = round(total_raindrop / total_commands * 100, 1)
        insights.append(f"Raindrop command adoption: {adoption}%")

    return {
        "period": {"start": start_date, "end": end_date},
        "summary": {
            "total_sessions": total_sessions,
            "unique_users": len(all_users),
            "total_work_hours": round(total_work_mins / 60, 1),
            "total_commands": total_commands,
            "raindrop_adoption_pct": round(total_raindrop / total_commands * 100, 1) if total_commands else 0,
            "avg_session_minutes": round(total_work_mins / total_sessions, 1) if total_sessions else 0,
            "productivity_pct": round(total_work_mins / total_open_mins * 100, 1) if total_open_mins else 0,
            "total_saves": total_saves,
            "unique_drawings": len(all_drawings),
        },
        "daily_active_users": daily_active_users,
        "daily_sessions": daily_sessions_list,
        "daily_work_hours": daily_work_hours_list,
        "hourly_distribution": hourly_distribution,
        "user_stats": user_stats,
        "insights": insights,
    }


def aggregate_errors(entries: list[tuple[str, dict]], include_stack: bool = False) -> list[dict]:
    """Parse raw Loki entries into error/warning records."""
    errors = []
    for ts_ns, entry in entries:
        try:
            ts = datetime.fromtimestamp(int(ts_ns) / 1e9).isoformat()
        except (ValueError, OSError):
            ts = "unknown"

        record = {
            "timestamp": ts,
            "user": _extract_username(entry),
            "machine": entry.get("MachineName", ""),
            "message": entry.get("_Message", "") or entry.get("Message", str(entry)),
            "drawing": entry.get("DrawingName", ""),
            "app_version": entry.get("AppVersion", ""),
            "level": entry.get("level", ""),
        }
        if include_stack:
            record["exception"] = entry.get("Exception", "")
            record["stack_trace"] = entry.get("StackTrace", "")

        errors.append(record)

    errors.sort(key=lambda x: x["timestamp"], reverse=True)
    return errors


def aggregate_events(entries: list[tuple[str, dict]]) -> dict:
    """Summarize distinct event/action types."""
    actions: Counter = Counter()
    for _, entry in entries:
        action = entry.get("Action", entry.get("CommandName", "unknown"))
        actions[action] += 1

    return {
        "event_types": [{"action": a, "count": c} for a, c in actions.most_common(50)],
        "total_events": len(entries),
    }
