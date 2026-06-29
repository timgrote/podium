import app.routers.raindrop_analytics as ra


def test_exceptions_unique_count(client, monkeypatch):
    # Three exception occurrences, two share a message -> count 3, unique_count 2.
    entries = [
        ("1700000000000000000", {"_Message": "Boom", "level": "error", "MachineName": "M", "DrawingName": "d"}),
        ("1700000000000000001", {"_Message": "Boom", "level": "error"}),
        ("1700000000000000002", {"_Message": "Other", "level": "error"}),
    ]
    monkeypatch.setattr(ra, "query_loki_range", lambda *a, **k: entries)
    body = client.get("/api/raindrop/exceptions").json()
    assert body["count"] == 3
    assert body["unique_count"] == 2


def test_exceptions_unique_count_prev(client, monkeypatch):
    cur = [
        ("1700000000000000000", {"_Message": "A", "level": "error"}),
        ("1700000000000000001", {"_Message": "A", "level": "error"}),
        ("1700000000000000002", {"_Message": "B", "level": "error"}),
    ]
    prev = [("1700000000000000000", {"_Message": "A", "level": "error"})]
    calls = []

    def fake_query(logql, start, end, limit=200):
        calls.append(1)
        return cur if len(calls) == 1 else prev      # current window first, then previous

    monkeypatch.setattr(ra, "query_loki_range", fake_query)
    body = client.get("/api/raindrop/exceptions?days=14").json()
    assert body["unique_count"] == 2                  # A, B
    assert body["unique_count_prev"] == 1             # A
