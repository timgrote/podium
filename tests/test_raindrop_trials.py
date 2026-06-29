from datetime import datetime, timedelta, timezone

import app.routers.raindrop_analytics as ra
from app.config import settings


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def test_trials_unavailable_when_token_unset(client, monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "")
    monkeypatch.setattr(ra, "fetch_trial_licenses", lambda: [])
    r = client.get("/api/raindrop/trials")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert body["active"] == [] and body["expired_recent"] == []


def test_trials_split_active_and_recent_expired(client, monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")
    now = datetime.now(timezone.utc)
    licenses = [
        {"name": "Active User", "email": "a@x.com", "created": _iso(now - timedelta(days=5)),
         "expiry": _iso(now + timedelta(days=20)), "status": "ACTIVE"},
        {"name": "Just Expired", "email": "b@x.com", "created": _iso(now - timedelta(days=40)),
         "expiry": _iso(now - timedelta(days=10)), "status": "EXPIRED"},
        {"name": "Long Expired", "email": "c@x.com", "created": _iso(now - timedelta(days=70)),
         "expiry": _iso(now - timedelta(days=40)), "status": "EXPIRED"},
    ]
    monkeypatch.setattr(ra, "fetch_trial_licenses", lambda: licenses)
    body = client.get("/api/raindrop/trials").json()

    assert body["available"] is True
    assert body["active_count"] == 1
    assert body["active"][0]["name"] == "Active User"
    assert body["active"][0]["days_remaining"] in (19, 20)

    assert body["expired_recent_count"] == 1          # 40-days-ago one is excluded
    assert body["expired_recent"][0]["name"] == "Just Expired"
    assert body["expired_recent"][0]["days_since_expiry"] in (9, 10)


def test_trials_includes_licensed_active_count(client, monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")
    monkeypatch.setattr(ra, "fetch_trial_licenses", lambda: [])
    monkeypatch.setattr(ra, "count_active_licenses", lambda policy_id: 7)
    body = client.get("/api/raindrop/trials").json()
    assert body["licensed_active_count"] == 7


def test_leaderboard_uses_current_month(client, monkeypatch):
    captured = {}

    def fake_query(logql, start, end, limit=5000):
        captured["start"] = start
        captured["end"] = end
        return []

    monkeypatch.setattr(ra, "query_loki_range", fake_query)
    r = client.get("/api/raindrop/leaderboard")
    assert r.status_code == 200
    body = r.json()
    assert "user_stats" in body and "period" in body
    assert captured["start"].day == 1            # first of the current month
    assert captured["start"].hour == 0
