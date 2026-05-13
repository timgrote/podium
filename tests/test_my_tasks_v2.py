"""
Tests for My Tasks v2: filter params, bulk PATCH, done-today, is_stale.
"""

from datetime import date, datetime, timedelta


def _seed(db, *, employee_id="emp-1", project_id="TEST01", client_id="c-test1"):
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO clients (id, name, accounting_email, created_at, updated_at) "
        "VALUES (%s, 'Test Client', 't@x.com', %s, %s)",
        (client_id, now, now),
    )
    db.execute(
        "INSERT INTO projects (id, name, client_id, status, created_at, updated_at) "
        "VALUES (%s, 'Test Project', %s, 'contract', %s, %s)",
        (project_id, client_id, now, now),
    )
    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, created_at, updated_at) "
        "VALUES (%s, 'Tim', 'Grote', 'tim@x.com', %s, %s)",
        (employee_id, now, now),
    )
    db.commit()


def _make_task(db, *, task_id, project_id="TEST01", title="t",
               status="todo", due_date=None, updated_at=None,
               completed_at=None, assignee_id=None):
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO project_tasks "
        "(id, project_id, title, status, start_date, due_date, "
        "completed_at, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (task_id, project_id, title, status,
         now[:10], str(due_date) if due_date else None,
         completed_at, now, updated_at or now),
    )
    if assignee_id:
        db.execute(
            "INSERT INTO project_task_assignees (task_id, employee_id) VALUES (%s, %s)",
            (task_id, assignee_id),
        )
    db.commit()


# ---------------------------------------------------------------------------
# Filter params on /tasks/my
# ---------------------------------------------------------------------------

def test_my_tasks_due_before_filter(client, db):
    _seed(db)
    today = date.today()
    _make_task(db, task_id="t-1", due_date=today, assignee_id="emp-1")
    _make_task(db, task_id="t-2", due_date=today + timedelta(days=10), assignee_id="emp-1")
    resp = client.get(f"/api/tasks/my?employee_id=emp-1&due_before={today + timedelta(days=3)}")
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert "t-1" in ids and "t-2" not in ids


def test_my_tasks_no_due_date_filter(client, db):
    _seed(db)
    _make_task(db, task_id="t-due", due_date=date.today(), assignee_id="emp-1")
    _make_task(db, task_id="t-orphan", assignee_id="emp-1")
    resp = client.get("/api/tasks/my?employee_id=emp-1&no_due_date=true")
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert ids == ["t-orphan"]


def test_my_tasks_status_csv_filter(client, db):
    _seed(db)
    _make_task(db, task_id="t-todo", status="todo", assignee_id="emp-1")
    _make_task(db, task_id="t-prog", status="in_progress", assignee_id="emp-1")
    _make_task(db, task_id="t-done", status="done", assignee_id="emp-1")
    resp = client.get("/api/tasks/my?employee_id=emp-1&status=todo,in_progress")
    ids = sorted(t["id"] for t in resp.json())
    assert ids == ["t-prog", "t-todo"]


def test_my_tasks_stale_filter_and_flag(client, db):
    _seed(db)
    old = (datetime.now() - timedelta(days=60)).isoformat()
    _make_task(db, task_id="t-fresh", assignee_id="emp-1")
    _make_task(db, task_id="t-stale", updated_at=old, assignee_id="emp-1")
    _make_task(db, task_id="t-old-done", status="done", updated_at=old, assignee_id="emp-1")

    all_resp = client.get("/api/tasks/my?employee_id=emp-1").json()
    flags = {t["id"]: t["is_stale"] for t in all_resp}
    assert flags["t-stale"] is True
    assert flags["t-fresh"] is False
    assert flags["t-old-done"] is False  # done tasks are never stale

    stale_only = client.get("/api/tasks/my?employee_id=emp-1&stale=true").json()
    assert [t["id"] for t in stale_only] == ["t-stale"]


# ---------------------------------------------------------------------------
# /tasks/done-today
# ---------------------------------------------------------------------------

def test_done_today_returns_only_today(client, db):
    _seed(db)
    today = date.today()
    yesterday = today - timedelta(days=1)
    _make_task(db, task_id="t-today", status="done",
               completed_at=datetime.combine(today, datetime.min.time()).isoformat(),
               assignee_id="emp-1")
    _make_task(db, task_id="t-yest", status="done",
               completed_at=datetime.combine(yesterday, datetime.min.time()).isoformat(),
               assignee_id="emp-1")
    _make_task(db, task_id="t-open", assignee_id="emp-1")

    resp = client.get(f"/api/tasks/done-today?employee_id=emp-1&today={today}")
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert ids == ["t-today"]


# ---------------------------------------------------------------------------
# Bulk PATCH
# ---------------------------------------------------------------------------

def test_bulk_due_date_updates_all(client, db):
    _seed(db)
    today = date.today()
    _make_task(db, task_id="t-a", due_date=today, assignee_id="emp-1")
    _make_task(db, task_id="t-b", due_date=today, assignee_id="emp-1")
    new_due = today + timedelta(days=7)
    resp = client.patch(
        "/api/tasks/bulk",
        json={"task_ids": ["t-a", "t-b"], "patch": {"due_date": str(new_due)}},
    )
    assert resp.status_code == 200
    for t in resp.json():
        assert t["due_date"] == str(new_due)


def test_bulk_404_when_any_missing_and_no_partial_update(client, db):
    _seed(db)
    today = date.today()
    _make_task(db, task_id="t-a", due_date=today, assignee_id="emp-1")
    resp = client.patch(
        "/api/tasks/bulk",
        json={"task_ids": ["t-a", "t-nope"], "patch": {"due_date": str(today + timedelta(days=7))}},
    )
    assert resp.status_code == 404
    row = db.execute("SELECT due_date FROM project_tasks WHERE id = 't-a'").fetchone()
    assert str(row["due_date"]) == str(today)


def test_bulk_rejects_disallowed_fields(client, db):
    _seed(db)
    _make_task(db, task_id="t-a", assignee_id="emp-1")
    resp = client.patch(
        "/api/tasks/bulk",
        json={"task_ids": ["t-a"], "patch": {"title": "hax"}},
    )
    assert resp.status_code == 422 or resp.status_code == 400


def test_bulk_status_done_sets_completed_at(client, db):
    _seed(db)
    _make_task(db, task_id="t-a", assignee_id="emp-1")
    resp = client.patch(
        "/api/tasks/bulk",
        json={"task_ids": ["t-a"], "patch": {"status": "done"}},
    )
    assert resp.status_code == 200
    assert resp.json()[0]["completed_at"] is not None


def test_bulk_empty_task_ids_rejected(client, db):
    _seed(db)
    resp = client.patch("/api/tasks/bulk", json={"task_ids": [], "patch": {"status": "done"}})
    assert resp.status_code == 400


def test_bulk_empty_patch_rejected(client, db):
    _seed(db)
    _make_task(db, task_id="t-a", assignee_id="emp-1")
    resp = client.patch("/api/tasks/bulk", json={"task_ids": ["t-a"], "patch": {}})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Project tasks filter params
# ---------------------------------------------------------------------------

def test_project_tasks_due_after_filter(client, db):
    _seed(db)
    today = date.today()
    _make_task(db, task_id="t-old", due_date=today - timedelta(days=5))
    _make_task(db, task_id="t-soon", due_date=today + timedelta(days=2))
    resp = client.get(f"/api/projects/TEST01/tasks?due_after={today}")
    ids = sorted(t["id"] for t in resp.json())
    assert ids == ["t-soon"]
