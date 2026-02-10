import json
import os

import psycopg2
import psycopg2.extras
from collections.abc import Generator

from .config import settings

# File-based override for the database URL (set via settings UI)
_CONNECTION_FILE = os.path.join(os.path.dirname(__file__), "..", "db", "connection.json")


def get_database_url() -> str:
    """Resolve the active database URL. Priority: connection.json > env var > default."""
    try:
        with open(_CONNECTION_FILE) as f:
            data = json.load(f)
            if data.get("database_url"):
                return data["database_url"]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return settings.database_url


def set_database_url(url: str):
    """Persist a database URL override to connection.json."""
    os.makedirs(os.path.dirname(_CONNECTION_FILE), exist_ok=True)
    with open(_CONNECTION_FILE, "w") as f:
        json.dump({"database_url": url}, f)


def clear_database_url():
    """Remove the override, falling back to env var / default."""
    try:
        os.remove(_CONNECTION_FILE)
    except FileNotFoundError:
        pass


class PgConnection:
    """Thin wrapper around psycopg2 connection that mimics sqlite3's
    conn.execute(...).fetchone() chaining pattern used throughout the app."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self._conn = conn

    def execute(self, sql: str, params=None) -> "PgCursor":
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def cursor(self):
        return self._conn.cursor()


def get_db() -> Generator[PgConnection, None, None]:
    conn = psycopg2.connect(
        get_database_url(),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    db = PgConnection(conn)
    try:
        yield db
    finally:
        db.close()
