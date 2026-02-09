"""
Shared test fixtures for Podium.

conftest.py is a special pytest file — fixtures defined here are automatically
available to every test file in this directory without importing them.

The key fixture is `client`, which gives each test:
  1. A fresh in-memory SQLite database with the full schema
  2. A FastAPI TestClient wired to that database
  3. Automatic cleanup after the test finishes

This means tests never touch your real podium.db.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db


# Path to the SQL schema file
SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


def _create_test_db() -> sqlite3.Connection:
    """Create a fresh in-memory database with the full Podium schema."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


@pytest.fixture()
def client():
    """
    Provide a TestClient with a fresh test database.

    How this works:
    - We create a new in-memory SQLite DB for each test
    - We override FastAPI's `get_db` dependency so all endpoints use our test DB
    - After the test, we undo the override and close the DB

    This is called "dependency injection" — FastAPI lets you swap out
    real dependencies (like the database) with test versions.
    """
    db = _create_test_db()

    def _override_get_db():
        try:
            yield db
        except Exception:
            db.rollback()
            raise

    # Tell FastAPI: "when any endpoint asks for get_db, give it our test DB"
    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as tc:
        yield tc

    # Cleanup: remove the override so it doesn't leak into other tests
    app.dependency_overrides.clear()
    db.close()


@pytest.fixture()
def db(client):
    """
    Direct access to the test database connection.

    Some tests need to insert seed data before calling an endpoint.
    This fixture gives you the same DB the endpoints are using.
    """
    # Get the DB from the override we set up in `client`
    gen = app.dependency_overrides[get_db]()
    conn = next(gen)
    return conn
