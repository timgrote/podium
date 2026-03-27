import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from ..services.loki_analytics import aggregate_dashboard, aggregate_errors, aggregate_events, query_loki_range

logger = logging.getLogger("conductor")
router = APIRouter()


def _date_range(days: int) -> tuple[datetime, datetime, str, str]:
    end = datetime.now().replace(hour=23, minute=59, second=59)
    start = (end - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0)
    return start, end, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


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
