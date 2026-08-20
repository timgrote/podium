"""Tests for the project Kanban board endpoints."""

from app.utils import generate_id


def _make_project(db, name, status="lead", board_order=0):
    pid = generate_id("proj-")
    db.execute(
        "INSERT INTO projects (id, name, status, board_order, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (pid, name, status, board_order),
    )
    return pid


def test_get_board_groups_by_status(client, db):
    _make_project(db, "Alpha", status="lead")
    _make_project(db, "Bravo", status="active")
    _make_project(db, "Charlie", status="active")
    db.commit()

    res = client.get("/api/kanban")
    assert res.status_code == 200
    data = res.json()
    statuses = [c["status"] for c in data["columns"]]
    # Canonical order, known statuses first.
    assert statuses[:6] == ["lead", "proposal", "contract", "active", "complete", "archive"]

    by_status = {c["status"]: c["projects"] for c in data["columns"]}
    assert [p["project_name"] for p in by_status["lead"]] == ["Alpha"]
    assert {p["project_name"] for p in by_status["active"]} == {"Bravo", "Charlie"}
    # Unknown statuses are not dropped from the board.
    assert by_status["active"][0]["project_name"] in ("Bravo", "Charlie")


def test_get_board_card_shape(client, db):
    pid = _make_project(db, "Omega", status="lead")
    db.commit()
    res = client.get("/api/kanban")
    cards = [p for c in res.json()["columns"] for p in c["projects"]]
    card = next(c for c in cards if c["id"] == pid)
    for field in (
        "id", "project_name", "status", "board_order", "client_name",
        "pm_name", "next_task_deadline", "total_outstanding",
    ):
        assert field in card, f"missing {field}"


def test_move_card_changes_status(client, db):
    pid = _make_project(db, "MoveMe", status="lead", board_order=0)
    db.commit()

    res = client.post("/api/kanban/move", json={"project_id": pid, "status": "active", "board_order": 0})
    assert res.status_code == 200
    data = res.json()
    by_status = {c["status"]: c["projects"] for c in data["columns"]}
    moved = next(p for p in by_status["active"] if p["id"] == pid)
    assert moved["status"] == "active"
    assert by_status["lead"] == []


def test_move_card_reindexes_within_column(client, db):
    a = _make_project(db, "A", status="active", board_order=0)
    b = _make_project(db, "B", status="active", board_order=1)
    c = _make_project(db, "C", status="active", board_order=2)
    db.commit()

    # Move B to the top of the active column.
    res = client.post("/api/kanban/move", json={"project_id": b, "status": "active", "board_order": 0})
    assert res.status_code == 200
    active = [p for c in res.json()["columns"] if c["status"] == "active" for p in c["projects"]]
    assert [p["project_name"] for p in active] == ["B", "A", "C"]
    # board_order stays dense 0..n
    assert [p["board_order"] for p in active] == [0, 1, 2]


def test_move_card_unknown_status_400(client, db):
    pid = _make_project(db, "Bad", status="lead")
    db.commit()
    res = client.post("/api/kanban/move", json={"project_id": pid, "status": "not_a_status", "board_order": 0})
    assert res.status_code == 400


def test_move_card_missing_project_404(client):
    res = client.post(
        "/api/kanban/move",
        json={"project_id": "proj-doesnotexist", "status": "active", "board_order": 0},
    )
    assert res.status_code == 404


# --- Task board ---


def _make_task(db, title, project_id, status="todo", sort_order=0):
    tid = generate_id("task-")
    db.execute(
        "INSERT INTO project_tasks (id, project_id, title, status, sort_order, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (tid, project_id, title, status, sort_order),
    )
    return tid


def test_get_task_board_groups_by_status(client, db):
    pid = _make_project(db, "Proj", status="active")
    _make_task(db, "Draft plan", pid, status="todo")
    _make_task(db, "CDs", pid, status="todo")
    _make_task(db, "Redline", pid, status="in_progress")
    _make_task(db, "Signed off", pid, status="done")
    db.commit()

    res = client.get("/api/kanban/tasks")
    assert res.status_code == 200
    data = res.json()
    statuses = [c["status"] for c in data["columns"]]
    assert statuses == ["triage", "todo", "in_progress", "blocked", "done", "canceled"]

    by_status = {c["status"]: c["tasks"] for c in data["columns"]}
    assert {t["title"] for t in by_status["todo"]} == {"Draft plan", "CDs"}
    assert [t["title"] for t in by_status["in_progress"]] == ["Redline"]
    assert [t["title"] for t in by_status["done"]] == ["Signed off"]


def test_task_card_includes_project_context(client, db):
    pid = _make_project(db, "ProjX", status="active")
    tid = _make_task(db, "Preliminary Plan", pid, status="todo")
    db.commit()
    res = client.get("/api/kanban/tasks")
    tasks = [t for c in res.json()["columns"] for t in c["tasks"]]
    card = next(t for t in tasks if t["id"] == tid)
    assert card["project_name"] == "ProjX"
    assert card["project_id"] == pid
    for field in ("title", "status", "sort_order", "due_date", "assignee_name"):
        assert field in card, f"missing {field}"


def test_task_board_filters_to_selected_employees(client, db):
    pid = _make_project(db, "Assigned", status="active")
    allie_task = _make_task(db, "Allie's task", pid)
    tim_task = _make_task(db, "Tim's task", pid)
    db.execute(
        "INSERT INTO employees (id, first_name, last_name, email, created_at, updated_at) "
        "VALUES ('allie-1', 'Allie', 'Example', 'allie@example.test', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
        "('tim-1', 'Tim', 'Grote', 'tim@example.test', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )
    db.execute(
        "INSERT INTO project_task_assignees (task_id, employee_id) VALUES (%s, %s), (%s, %s)",
        (allie_task, "allie-1", tim_task, "tim-1"),
    )
    db.commit()

    res = client.get("/api/kanban/tasks?assignee=allie-1")
    assert res.status_code == 200
    assert {t["id"] for c in res.json()["columns"] for t in c["tasks"]} == {allie_task}

    res = client.get("/api/kanban/tasks?assignee=allie-1,tim-1")
    assert res.status_code == 200
    assert {t["id"] for c in res.json()["columns"] for t in c["tasks"]} == {allie_task, tim_task}


def test_move_task_card_changes_status(client, db):
    pid = _make_project(db, "ProjY", status="active")
    tid = _make_task(db, "Move me", pid, status="todo")
    db.commit()

    res = client.post("/api/kanban/tasks/move", json={"task_id": tid, "status": "in_progress", "sort_order": 0})
    assert res.status_code == 200
    data = res.json()
    by_status = {c["status"]: c["tasks"] for c in data["columns"]}
    moved = next(t for t in by_status["in_progress"] if t["id"] == tid)
    assert moved["status"] == "in_progress"
    assert by_status["todo"] == []

    # Move to done sets completed_at
    res2 = client.post("/api/kanban/tasks/move", json={"task_id": tid, "status": "done", "sort_order": 0})
    assert res2.status_code == 200
    row = db.execute("SELECT completed_at FROM project_tasks WHERE id = %s", (tid,)).fetchone()
    assert row["completed_at"] is not None


def test_move_task_card_reindexes_within_column(client, db):
    pid = _make_project(db, "ProjZ", status="active")
    a = _make_task(db, "A", pid, status="todo", sort_order=0)
    b = _make_task(db, "B", pid, status="todo", sort_order=1)
    c = _make_task(db, "C", pid, status="todo", sort_order=2)
    db.commit()

    res = client.post("/api/kanban/tasks/move", json={"task_id": b, "status": "todo", "sort_order": 0})
    assert res.status_code == 200
    todo = [t for c in res.json()["columns"] if c["status"] == "todo" for t in c["tasks"]]
    assert [t["title"] for t in todo] == ["B", "A", "C"]
    assert [t["sort_order"] for t in todo] == [0, 1, 2]


def test_move_task_unknown_status_400(client, db):
    pid = _make_project(db, "ProjQ", status="active")
    tid = _make_task(db, "Bad", pid, status="todo")
    db.commit()
    res = client.post("/api/kanban/tasks/move", json={"task_id": tid, "status": "nope", "sort_order": 0})
    assert res.status_code == 400


def test_move_task_missing_404(client):
    res = client.post(
        "/api/kanban/tasks/move",
        json={"task_id": "task-nope", "status": "todo", "sort_order": 0},
    )
    assert res.status_code == 404
