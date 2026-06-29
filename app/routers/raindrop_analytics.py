import calendar
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from ..config import settings
from ..services.keygen_client import fetch_licenses, fetch_trial_licenses
from ..services.loki_analytics import _extract_username, aggregate_dashboard, aggregate_errors, aggregate_events, query_loki_range

logger = logging.getLogger("conductor")
router = APIRouter()


def _date_range(days: int) -> tuple[datetime, datetime, str, str]:
    end = datetime.now().replace(hour=23, minute=59, second=59)
    start = (end - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0)
    return start, end, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _parse_keygen_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _count_active_at(licenses: list[dict], at: datetime) -> int:
    """Count licenses valid (created <= at < expiry) at a point in time."""
    return sum(
        1 for lic in licenses
        if (c := _parse_keygen_dt(lic.get("created"))) and (e := _parse_keygen_dt(lic.get("expiry")))
        and c <= at < e
    )


def _user_key(lic: dict, idx: int) -> str:
    """Best-effort unique-user key for a license: email, else name, else a row fallback."""
    return (lic.get("email") or "").strip().lower() or (lic.get("name") or "").strip().lower() or f"__row{idx}"


def _active_users_by_month(logql: str, start: datetime, end: datetime) -> dict[str, set]:
    """Distinct Drawing-Closed users keyed by 'YYYY-MM' over a range.

    Split into <=25-day chunks because Loki rejects ranges over its ~721h
    max_query_length (a 31-day month 400s). Loki serialises queries server-side,
    so this is inherently ~slow over a year — callers should cache it.
    """
    by_month: dict[str, set] = defaultdict(set)
    cs = start
    while cs < end:
        ce = min(cs + timedelta(days=25), end)
        for ts_ns, entry in query_loki_range(logql, cs, ce, limit=5000):
            if entry.get("Action") != "Drawing Closed":
                continue
            try:
                month = datetime.fromtimestamp(int(ts_ns) / 1e9, tz=timezone.utc).strftime("%Y-%m")
            except (ValueError, OSError):
                continue
            by_month[month].add(_extract_username(entry))
        cs = ce
    return by_month


def _unique_users_active_at(licenses: list[dict], at: datetime) -> int:
    """Count distinct users holding a non-expired (created <= at < expiry) license at a time."""
    users = set()
    for i, lic in enumerate(licenses):
        created = _parse_keygen_dt(lic.get("created"))
        expiry = _parse_keygen_dt(lic.get("expiry"))
        if created and expiry and created <= at < expiry:
            users.add(_user_key(lic, i))
    return len(users)


def _work_hours(entries: list[tuple[str, dict]]) -> float:
    """Sum TotalWorkMinutes across Drawing Closed events, in hours."""
    mins = sum(
        float(entry.get("TotalWorkMinutes", 0) or 0)
        for _, entry in entries
        if entry.get("Action") == "Drawing Closed"
    )
    return round(mins / 60, 1)


@router.get("/analytics")
def get_analytics(days: int = Query(default=14, ge=1, le=90)):
    start, end, start_str, end_str = _date_range(days)
    logql = '{app="raindrop"} |= "Drawing Closed"'
    entries = query_loki_range(logql, start, end)
    result = aggregate_dashboard(entries, start_str, end_str)

    # Previous equal-length window, for the Work Hours trend.
    prev_entries = query_loki_range(logql, start - timedelta(days=days), start - timedelta(seconds=1))
    result["summary"]["total_work_hours_prev"] = _work_hours(prev_entries)
    return result


@router.get("/exceptions")
def get_exceptions(days: int = Query(default=14, ge=1, le=90)):
    """Code exceptions (level=error) — stack traces, unhandled errors."""
    start, end, _, _ = _date_range(days)
    logql = '{app="raindrop"} | json | level="error"'
    entries = query_loki_range(logql, start, end, limit=200)
    exceptions = aggregate_errors(entries, include_stack=True)
    unique_count = len({e["message"] for e in exceptions})

    # Previous equal-length window, for the Unique Exceptions trend.
    prev_entries = query_loki_range(logql, start - timedelta(days=days), start - timedelta(seconds=1), limit=200)
    unique_count_prev = len({e["message"] for e in aggregate_errors(prev_entries)})

    return {
        "exceptions": exceptions, "count": len(exceptions),
        "unique_count": unique_count, "unique_count_prev": unique_count_prev,
    }


@router.get("/warnings")
def get_warnings(days: int = Query(default=14, ge=1, le=90)):
    """App-level warnings (level=warning) — sizing errors, non-critical issues."""
    start, end, _, _ = _date_range(days)
    logql = '{app="raindrop"} | json | level="warning"'
    entries = query_loki_range(logql, start, end, limit=200)
    warnings = aggregate_errors(entries)
    return {"warnings": warnings, "count": len(warnings)}


@router.get("/events")
def get_events(days: int = Query(default=1, ge=1, le=7), limit: int = Query(default=200, le=1000)):
    start, end, _, _ = _date_range(days)
    logql = '{app="raindrop"}'
    entries = query_loki_range(logql, start, end, limit=limit)
    return aggregate_events(entries)


@router.get("/trials")
def get_trials(days: int = Query(default=14, ge=1, le=90)):
    """Active Raindrop trials + trials expired in the last 30 days (from KeyGen).

    Includes prior-window counts (``days`` ago) for licensed/trial trend arrows,
    derived from each license's created/expiry dates.
    """
    if not settings.keygen_api_token:
        return {
            "active": [], "expired_recent": [],
            "active_count": 0, "expired_recent_count": 0, "active_trials_prev": 0,
            "licensed_active_count": 0, "licensed_active_prev": 0, "available": False,
        }

    trial_licenses = fetch_trial_licenses()
    yearly_licenses = fetch_licenses(settings.keygen_yearly_policy_id)
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=days)
    cutoff = now - timedelta(days=30)
    active, expired = [], []

    for lic in trial_licenses:
        expiry = _parse_keygen_dt(lic.get("expiry"))
        if expiry is None:
            continue
        base = {
            "name": lic["name"], "email": lic["email"],
            "created": lic.get("created"), "expiry": lic.get("expiry"),
        }
        if expiry > now:
            active.append({**base, "days_remaining": (expiry - now).days})
        elif expiry >= cutoff:
            expired.append({**base, "days_since_expiry": (now - expiry).days})

    active.sort(key=lambda x: x["days_remaining"])
    expired.sort(key=lambda x: x["days_since_expiry"])

    return {
        "active": active, "expired_recent": expired,
        "active_count": len(active), "expired_recent_count": len(expired),
        "active_trials_prev": _count_active_at(trial_licenses, past),
        "licensed_active_count": _unique_users_active_at(yearly_licenses, now),
        "licensed_active_prev": _unique_users_active_at(yearly_licenses, past),
        "available": True,
    }


_yearly_cache: dict = {"data": None, "ts": 0.0}
_YEARLY_TTL = 1800  # 30 min — this series moves slowly and is expensive to build.


@router.get("/yearly")
def get_yearly():
    """Rolling 12-month monthly series: active users (Loki) + licensed users and
    active trials (KeyGen, counted at each month-end). Cached (~30 min) because the
    Loki side needs ~13 sequential chunked queries (~14s cold)."""
    if _yearly_cache["data"] is not None and time.monotonic() - _yearly_cache["ts"] < _YEARLY_TTL:
        return _yearly_cache["data"]

    now = datetime.now(timezone.utc)

    # Build the last 12 (year, month) buckets, oldest first.
    seq = []
    y, m = now.year, now.month
    for _ in range(12):
        seq.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    seq.reverse()

    logql = '{app="raindrop"} |= "Drawing Closed"'
    window_start = datetime(seq[0][0], seq[0][1], 1, tzinfo=timezone.utc)
    users_by_month = _active_users_by_month(logql, window_start, now)
    trial_licenses = fetch_trial_licenses()
    yearly_licenses = fetch_licenses(settings.keygen_yearly_policy_id)

    labels, active_users, licensed_users, active_trials = [], [], [], []
    for yr, mo in seq:
        label = f"{yr}-{mo:02d}"
        if (yr, mo) == (now.year, now.month):
            at = now
        else:
            last_day = calendar.monthrange(yr, mo)[1]
            at = datetime(yr, mo, last_day, 23, 59, 59, tzinfo=timezone.utc)

        labels.append(label)
        active_users.append(len(users_by_month.get(label, set())))
        licensed_users.append(_unique_users_active_at(yearly_licenses, at))
        active_trials.append(_count_active_at(trial_licenses, at))

    result = {
        "labels": labels,
        "active_users": active_users,
        "licensed_users": licensed_users,
        "active_trials": active_trials,
    }
    _yearly_cache["data"] = result
    _yearly_cache["ts"] = time.monotonic()
    return result


@router.get("/leaderboard")
def get_leaderboard():
    """User leaderboard for the current calendar month (independent of the day selector)."""
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59)
    logql = '{app="raindrop"} |= "Drawing Closed"'
    entries = query_loki_range(logql, start, end)
    dashboard = aggregate_dashboard(entries, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    user_stats = [u for u in dashboard["user_stats"] if u.get("raindrop_commands", 0) > 0]
    return {"user_stats": user_stats, "period": dashboard["period"]}
