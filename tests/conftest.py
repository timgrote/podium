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
from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, PgConnection


# Path to the SQL schema file
SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"

# Test database URL — uses a separate database to avoid clobbering dev data
TEST_DATABASE_URL = os.environ.get(
    "CONDUCTOR_TEST_DATABASE_URL",
    "postgresql://conductor:conductor@localhost:5432/conductor_test",
)


def _create_test_db() -> PgConnection:
    """Create a fresh test database connection with the full Conductor schema."""
    conn = psycopg2.connect(TEST_DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = True
    cur = conn.cursor()

    # Drop all existing tables/views for a clean slate
    cur.execute("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
            FOR r IN (SELECT viewname FROM pg_views WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.viewname) || ' CASCADE';
            END LOOP;
        END $$;
    """)

    conn.autocommit = False
    cur.execute(SCHEMA_PATH.read_text())
    conn.commit()

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
