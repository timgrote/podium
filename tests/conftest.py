"""
Shared test fixtures for Conductor.

conftest.py is a special pytest file — fixtures defined here are automatically
available to every test file in this directory without importing them.

The key fixture is `client`, which gives each test:
  1. A fresh PostgreSQL test database with the full schema
  2. A FastAPI TestClient wired to that database
  3. Automatic cleanup after the test finishes

This means tests never touch your real conductor database.
"""

import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, PgConnection

# db/ is not a package; make the shared schema builder importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "db"))
from schema_loader import apply_schema  # noqa: E402

# Test database URL — uses a separate database to avoid clobbering dev data
TEST_DATABASE_URL = os.environ.get(
    "CONDUCTOR_TEST_DATABASE_URL",
    "postgresql://conductor:conductor@localhost:5432/conductor_test",
)


def _create_test_db() -> PgConnection:
    """Create a fresh test database connection with the full Conductor schema."""
    conn = psycopg2.connect(TEST_DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    apply_schema(conn)  # drops existing objects, builds from baseline + active migrations
    return PgConnection(conn)


@pytest.fixture()
def client():
    """
    Provide a TestClient with a fresh test database.

    How this works:
    - We create a new PostgreSQL test DB for each test (schema re-applied)
    - We override FastAPI's `get_db` dependency so all endpoints use our test DB
    - After the test, we undo the override and close the DB
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
