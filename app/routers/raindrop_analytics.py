import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from ..config import settings
from ..services.keygen_client import count_active_licenses, fetch_trial_licenses
from ..services.loki_analytics import aggregate_dashboard, aggregate_errors, aggregate_events, query_loki_range

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


@router.get("/analytics")
def get_analytics(days: int = Query(default=14, ge=1, le=90)):
    start, end, start_str, end_str = _date_range(days)
    logql = '{app="raindrop"} |= "Drawing Closed"'
    entries = query_loki_range(logql, start, end)
    return aggregate_dashboard(entries, start_str, end_str)


@router.get("/exceptions")
def get_exceptions(days: int = Query(default=14, ge=1, le=90)):
    """Code exceptions (level=error) — stack traces, unhandled errors."""
    start, end, _, _ = _date_range(days)
    logql = '{app="raindrop"} | json | level="error"'
    entries = query_loki_range(logql, start, end, limit=200)
    exceptions = aggregate_errors(entries, include_stack=True)
    return {"exceptions": exceptions, "count": len(exceptions)}


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
def get_trials():
    """Active Raindrop trials + trials expired in the last 30 days (from KeyGen)."""
    if not settings.keygen_api_token:
        return {
            "active": [], "expired_recent": [],
            "active_count": 0, "expired_recent_count": 0,
            "licensed_active_count": 0, "available": False,
        }

    licenses = fetch_trial_licenses()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    active, expired = [], []

    for lic in licenses:
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

    licensed_active_count = count_active_licenses(settings.keygen_yearly_policy_id)

    return {
        "active": active, "expired_recent": expired,
        "active_count": len(active), "expired_recent_count": len(expired),
        "licensed_active_count": licensed_active_count, "available": True,
    }


@router.get("/leaderboard")
def get_leaderboard():
    """User leaderboard for the current calendar month (independent of the day selector)."""
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59)
    logql = '{app="raindrop"} |= "Drawing Closed"'
    entries = query_loki_range(logql, start, end)
    dashboard = aggregate_dashboard(entries, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    return {"user_stats": dashboard["user_stats"], "period": dashboard["period"]}
