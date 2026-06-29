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
