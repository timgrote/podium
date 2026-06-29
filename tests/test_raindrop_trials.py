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


def test_licensed_counts_unique_non_expired_users(client, monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")
    monkeypatch.setattr(ra, "fetch_trial_licenses", lambda: [])
    future, past_exp = _iso(now + timedelta(days=200)), _iso(now - timedelta(days=1))
    created = _iso(now - timedelta(days=100))
    yearly = [
        # alice holds two non-expired licenses -> counts once
        {"name": "Alice", "email": "alice@x.com", "created": created, "expiry": future, "status": "ACTIVE"},
        {"name": "alice@x.com", "email": "", "created": created, "expiry": future, "status": "INACTIVE"},
        # bob, one non-expired
        {"name": "Bob", "email": "bob@x.com", "created": created, "expiry": future, "status": "ACTIVE"},
        # carol's license is expired -> excluded
        {"name": "Carol", "email": "carol@x.com", "created": created, "expiry": past_exp, "status": "EXPIRED"},
    ]
    monkeypatch.setattr(ra, "fetch_licenses", lambda policy_id: yearly)
    body = client.get("/api/raindrop/trials").json()
    assert body["licensed_active_count"] == 2          # alice (deduped) + bob; carol excluded


def test_trials_trend_counts(client, monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")
    # A trial created 5 days ago: active now, but did NOT exist 14 days ago.
    trials = [
        {"name": "T", "email": "t@x.com", "created": _iso(now - timedelta(days=5)),
         "expiry": _iso(now + timedelta(days=25)), "status": "ACTIVE"},
    ]
    # A yearly license created 100 days ago: active now AND 14 days ago.
    yearly = [
        {"name": "L", "email": "l@x.com", "created": _iso(now - timedelta(days=100)),
         "expiry": _iso(now + timedelta(days=200)), "status": "ACTIVE"},
    ]
    monkeypatch.setattr(ra, "fetch_trial_licenses", lambda: trials)
    monkeypatch.setattr(ra, "fetch_licenses", lambda policy_id: yearly)
    body = client.get("/api/raindrop/trials?days=14").json()
    assert body["active_count"] == 1
    assert body["active_trials_prev"] == 0          # didn't exist 14 days ago
    assert body["licensed_active_count"] == 1
    assert body["licensed_active_prev"] == 1        # already active 14 days ago


def test_analytics_includes_work_hours_prev(client, monkeypatch):
    calls = []

    def fake_query(logql, start, end, limit=5000):
        calls.append(1)
        mins = 120 if len(calls) == 1 else 60      # current window 2h, previous 1h
        return [("1700000000000000000", {"Action": "Drawing Closed", "TotalWorkMinutes": mins})]

    monkeypatch.setattr(ra, "query_loki_range", fake_query)
    body = client.get("/api/raindrop/analytics?days=14").json()
    assert body["summary"]["total_work_hours"] == 2.0
    assert body["summary"]["total_work_hours_prev"] == 1.0


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
