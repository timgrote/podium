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


def _login(client, db):
    """Helper: create employee, login, return session cookie + employee id."""
    from app.auth import hash_password
    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, password_hash, is_active) "
        "VALUES (%s, %s, %s, %s, %s, TRUE)",
        ("emp-crud", "CRUD", "User", "crud@example.com", hash_password("password123")),
    )
    db.commit()
    resp = client.post("/api/auth/login", json={"email": "crud@example.com", "password": "password123"})
    assert resp.status_code == 200
    return resp.cookies, "emp-crud"


def test_create_api_key(client, db):
    """POST /api/auth/api-keys creates a key and returns the raw key once."""
    cookies, emp_id = _login(client, db)
    resp = client.post(
        "/api/auth/api-keys",
        json={"name": "My Gmail Key"},
        cookies=cookies,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Gmail Key"
    assert "raw_key" in data
    assert data["raw_key"].startswith("pod_")
    assert "id" in data


def test_list_api_keys(client, db):
    """GET /api/auth/api-keys lists keys without exposing raw keys."""
    cookies, emp_id = _login(client, db)
    client.post("/api/auth/api-keys", json={"name": "Key 1"}, cookies=cookies)
    client.post("/api/auth/api-keys", json={"name": "Key 2"}, cookies=cookies)

    resp = client.get("/api/auth/api-keys", cookies=cookies)
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) == 2
    for k in keys:
        assert "raw_key" not in k
        assert "key_hash" not in k


def test_delete_api_key(client, db):
    """DELETE /api/auth/api-keys/{id} soft-deletes the key."""
    cookies, emp_id = _login(client, db)
    create_resp = client.post("/api/auth/api-keys", json={"name": "To Delete"}, cookies=cookies)
    key_id = create_resp.json()["id"]

    resp = client.delete(f"/api/auth/api-keys/{key_id}", cookies=cookies)
    assert resp.status_code == 200

    list_resp = client.get("/api/auth/api-keys", cookies=cookies)
    assert all(k["id"] != key_id for k in list_resp.json())


def test_cannot_delete_other_users_key(client, db):
    """Users can only delete their own API keys."""
    cookies, emp_id = _login(client, db)
    create_resp = client.post("/api/auth/api-keys", json={"name": "My Key"}, cookies=cookies)
    key_id = create_resp.json()["id"]

    from app.auth import hash_password
    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, password_hash, is_active) "
        "VALUES (%s, %s, %s, %s, %s, TRUE)",
        ("emp-other", "Other", "User", "other@example.com", hash_password("password123")),
    )
    db.commit()
    resp2 = client.post("/api/auth/login", json={"email": "other@example.com", "password": "password123"})
    cookies2 = resp2.cookies

    resp = client.delete(f"/api/auth/api-keys/{key_id}", cookies=cookies2)
    assert resp.status_code == 404


def test_create_task_with_api_key(client, db):
    """API key should authenticate task creation endpoint."""
    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, password_hash, is_active) "
        "VALUES (%s, %s, %s, %s, %s, TRUE)",
        ("emp-task1", "Task", "User", "taskuser@example.com", "fakehash"),
    )
    db.execute(
        "INSERT INTO projects (id, name, job_code, status, project_number) "
        "VALUES (%s, %s, %s, %s, %s)",
        ("proj-test1", "Test Project", "TEST", "active", "26-999"),
    )
    raw_key = "task-creation-key"
    db.execute(
        "INSERT INTO api_keys (id, employee_id, key_hash, name) "
        "VALUES (%s, %s, %s, %s)",
        ("ak-task1", "emp-task1", _hash_key(raw_key), "Task Key"),
    )
    db.commit()

    resp = client.post(
        "/api/projects/proj-test1/tasks",
        json={"title": "Task from API key", "status": "todo"},
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Task from API key"


def test_create_task_without_auth_rejected(client, db):
    """Task creation without any auth should return 401."""
    db.execute(
        "INSERT INTO projects (id, name, job_code, status, project_number) "
        "VALUES (%s, %s, %s, %s, %s)",
        ("proj-test2", "Test Project 2", "TST2", "active", "26-998"),
    )
    db.commit()

    resp = client.post(
        "/api/projects/proj-test2/tasks",
        json={"title": "Should fail", "status": "todo"},
    )
    assert resp.status_code == 401
