"""Build a fresh Conductor database from the single schema source of truth.

The schema is defined in exactly ONE place:
- db/baseline.sql — the complete current schema (all tables/views/indexes).
- db/migrations/*.sql — incremental FUTURE changes applied on top of the baseline.

A fresh database is built by applying the baseline, then every active migration
in filename order. Historical migrations (001-033) live in db/migrations/archive/
and are already baked into the baseline — they are NOT replayed for fresh
databases (they reference intermediate schema states and would fail).

To change the schema: edit the baseline OR add a new numbered migration in
db/migrations/ (never both, never edit an archived migration). After any schema
change, run `pytest tests/ -q` to confirm fresh databases match.
"""

from pathlib import Path

_DB_DIR = Path(__file__).resolve().parent
BASELINE_PATH = _DB_DIR / "baseline.sql"
MIGRATIONS_DIR = _DB_DIR / "migrations"

_DROP_ALL_SQL = """
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
"""


def drop_all(conn):
    """Drop all tables and views in the public schema for a fresh start."""
    cur = conn.cursor()
    cur.execute(_DROP_ALL_SQL)
    conn.commit()


def schema_files():
    """The ordered list of SQL files defining a fresh database."""
    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [BASELINE_PATH] + migrations


def apply_schema(conn):
    """Drop existing objects and build the schema from baseline + active migrations."""
    drop_all(conn)
    files = schema_files()
    cur = conn.cursor()
    for path in files:
        cur.execute(path.read_text(encoding="utf-8"))
    conn.commit()
    print(f"Schema built from {len(files)} file(s) "
          f"(baseline + {len(files) - 1} active migration(s))")
