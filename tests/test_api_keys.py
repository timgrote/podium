import hashlib


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def test_api_key_auth_returns_employee(client, db):
    """Bearer token in Authorization header should authenticate like a session."""
    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, password_hash, is_active) "
        "VALUES (%s, %s, %s, %s, %s, TRUE)",
        ("emp-test1", "Test", "User", "test@example.com", "fakehash"),
    )
    raw_key = "test-api-key-123"
    db.execute(
        "INSERT INTO api_keys (id, employee_id, key_hash, name) "
        "VALUES (%s, %s, %s, %s)",
        ("ak-001", "emp-test1", _hash_key(raw_key), "Test Key"),
    )
    db.commit()

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "emp-test1"
    assert data["email"] == "test@example.com"


def test_api_key_auth_rejects_invalid_key(client):
    """Invalid API key should return 401."""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer bad-key"})
    assert resp.status_code == 401


def test_api_key_auth_rejects_expired_key(client, db):
    """Expired API key should return 401."""
    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, password_hash, is_active) "
        "VALUES (%s, %s, %s, %s, %s, TRUE)",
        ("emp-test2", "Test", "Two", "test2@example.com", "fakehash"),
    )
    raw_key = "expired-key-456"
    db.execute(
        "INSERT INTO api_keys (id, employee_id, key_hash, name, expires_at) "
        "VALUES (%s, %s, %s, %s, NOW() - INTERVAL '1 day')",
        ("ak-002", "emp-test2", _hash_key(raw_key), "Expired Key"),
    )
    db.commit()

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp.status_code == 401


def test_api_key_auth_rejects_deleted_key(client, db):
    """Soft-deleted API key should return 401."""
    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, password_hash, is_active) "
        "VALUES (%s, %s, %s, %s, %s, TRUE)",
        ("emp-test3", "Test", "Three", "test3@example.com", "fakehash"),
    )
    raw_key = "deleted-key-789"
    db.execute(
        "INSERT INTO api_keys (id, employee_id, key_hash, name, deleted_at) "
        "VALUES (%s, %s, %s, %s, NOW())",
        ("ak-003", "emp-test3", _hash_key(raw_key), "Deleted Key"),
    )
    db.commit()

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp.status_code == 401
