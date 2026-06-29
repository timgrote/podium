import app.services.keygen_client as kc
from app.config import settings


def _page(licenses):
    return {"data": [
        {"id": lic["id"], "attributes": {
            "name": lic["name"],
            "metadata": {"email": lic["email"]},
            "created": lic["created"],
            "expiry": lic["expiry"],
            "status": lic["status"],
        }} for lic in licenses
    ]}


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self._payload


def test_returns_empty_when_token_unset(monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "")
    assert kc.fetch_trial_licenses() == []


def test_normalizes_and_paginates(monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")
    full = [{"id": str(i), "name": f"User {i}", "email": f"u{i}@x.com",
             "created": "2026-06-01T00:00:00.000Z", "expiry": "2026-07-01T00:00:00.000Z",
             "status": "ACTIVE"} for i in range(100)]
    tail = [{"id": "100", "name": "Last User", "email": "last@x.com",
             "created": "2026-06-02T00:00:00.000Z", "expiry": "2026-07-02T00:00:00.000Z",
             "status": "ACTIVE"}]
    pages = {1: _page(full), 2: _page(tail)}
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(params["page[number]"])
        return _FakeResp(pages[params["page[number]"]])

    monkeypatch.setattr(kc.httpx, "get", fake_get)
    result = kc.fetch_trial_licenses()
    assert len(result) == 101
    assert calls == [1, 2]            # paged until a short page
    assert result[0] == {"name": "User 0", "email": "u0@x.com",
                         "created": "2026-06-01T00:00:00.000Z",
                         "expiry": "2026-07-01T00:00:00.000Z", "status": "ACTIVE"}
    assert result[-1]["name"] == "Last User"


def test_returns_empty_on_http_error(monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(kc.httpx, "get", boom)
    assert kc.fetch_trial_licenses() == []
