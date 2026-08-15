"""Guard: the fresh-DB schema (baseline + active migrations) must be complete.

The schema has a single source of truth: db/baseline.sql (the complete schema)
plus db/migrations/*.sql (future changes). conftest builds every test database
from those, so a broken schema breaks the whole suite. This test makes that
contract explicit and guards specifically against the drift class that bit us
(a column added to one place but not the baseline).

If you change the schema, run `pytest tests/ -q` — it must stay green.
"""

EXPECTED_TABLES = [
    "clients",
    "contacts",
    "projects",
    "contracts",
    "contract_tasks",
    "proposals",
    "invoices",
    "invoice_line_items",
    "employees",
    "project_tasks",
    "sessions",
    "company_settings",
]

# Columns that have historically drifted between the schema and migrations.
EXPECTED_COLUMNS = {
    "clients": ["accounting_email"],
    "project_tasks": ["is_pinned", "tags"],
}


def test_fresh_schema_has_all_expected_tables(db):
    rows = db.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public'"
    ).fetchall()
    names = {r["tablename"] for r in rows}
    missing = [t for t in EXPECTED_TABLES if t not in names]
    assert not missing, f"Missing tables in fresh schema: {missing}"


def test_fresh_schema_has_expected_columns(db):
    for table, cols in EXPECTED_COLUMNS.items():
        rows = db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s",
            (table,),
        ).fetchall()
        present = {r["column_name"] for r in rows}
        missing = [c for c in cols if c not in present]
        assert not missing, f"Missing columns in {table}: {missing}"
