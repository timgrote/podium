# Local Test Server

The canonical local Conductor/Podium server is:

> **http://127.0.0.1:3100/**

It runs the production-style FastAPI app and serves the built Vue SPA from the same process. It is intentionally bound to loopback only, so it is not exposed on the LAN. The local database is `conductor_dev`; it is separate from the automated-test database (`conductor_test`) and from production.

## One-time workstation setup (Windows)

### Prerequisites

Install these once on the machine before running the launcher. Only PostgreSQL is
required for the app itself; `uv` and `Node.js` are required by
`scripts/start-local.sh` (it uses `uv` to build the Python venv and `npm` to
install/build the frontend).

- **Node.js (includes `npm`)** — version 18+ recommended:
  ```bash
  winget install --id OpenJS.NodeJS.LTS --exact --silent --accept-package-agreements --accept-source-agreements
  ```
- **`uv` (Python package/venv manager)** — install with the Windows installer:
  ```bash
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  (Alternatively install via `pip install uv`, or use the `uv` binary from
  https://github.com/astral-sh/uv/releases.)
- **PostgreSQL 17** — the database server, installed and run as a Windows service (see step 1 below).

1. Install PostgreSQL 17, accepting its default local port (`5432`). The local development-only PostgreSQL password used below is `conductor`.

   ```bash
   winget install --id PostgreSQL.PostgreSQL.17 --exact --silent --accept-package-agreements --accept-source-agreements --override '--mode unattended --unattendedmodeui none --superpassword conductor'
   ```

2. In Git Bash, create the non-production role and databases. This is idempotent: existing objects are left alone.

   ```bash
   PG_BIN='/c/Program Files/PostgreSQL/17/bin'
   export PGPASSWORD=conductor
   PSQL=("$PG_BIN/psql.exe" -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d postgres)
   "${PSQL[@]}" -tAc "SELECT 'CREATE ROLE conductor LOGIN PASSWORD ''conductor''' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'conductor')" | "${PSQL[@]}"
   for db in conductor_dev conductor_test; do
     if [ "$("${PSQL[@]}" -tAc "SELECT 1 FROM pg_database WHERE datname = '$db'")" != "1" ]; then
       "${PSQL[@]}" -c "CREATE DATABASE $db OWNER conductor"
     fi
   done
   ```

The installer creates and starts the local PostgreSQL service. If it is stopped later, start **postgresql-x64-17** from Windows Services before launching the app.

## Start the server

From the repository root:

```bash
bash scripts/start-local.sh
```

The launcher will:

- create `.venv` and install Python dependencies through `uv` if needed;
- verify PostgreSQL is listening locally;
- on an empty `conductor_dev`, restore `db/local-test-server.sql` when present; otherwise initialize the repository schema without seed data;
- install frontend dependencies and build the Vue SPA;
- run Uvicorn with reload at `http://127.0.0.1:3100/`.

Stop it with `Ctrl+C`. A later start does not reseed or wipe `conductor_dev`.

## Test-server indicator (orange border)

Once you are logged in, a test server is always visually marked so it cannot be
mistaken for production:

- an **orange banner** across the top reading **"⚠️ TEST SERVER — not production"**, and
- an **orange frame** around the edges of the page.

This is driven by `frontend/src/composables/useEnvironment.ts`: the indicator
shows whenever the app is served on a non-standard port. Production runs through
Caddy on port 80 (so `window.location.port` is empty) and never shows it. The
local test server on port 3100 (and staging on 3001) shows it automatically —
no extra configuration is needed when you run `scripts/start-local.sh`.

If you start the backend manually on another non-80 port, the border still
appears, which is the desired safety behavior.

## Local snapshot data

A plain PostgreSQL dump at `db/local-test-server.sql` is the local test-data contract. It is deliberately gitignored because it may contain business data. On a new clone, copy the approved dump to that exact path **before** the first start; the launcher restores it only when `conductor_dev` has no schema.

The current workstation snapshot is a PostgreSQL 15 plain dump and restores successfully into local PostgreSQL 17. It currently contains 24 clients, 88 projects, and 4 employees.

> **Password gotcha:** the dump carries over the **production bcrypt hashes** for
> Tim/Ally/Matara, so your real production password will not match them — they
> are stale. After restoring the snapshot, reset local passwords to known test
> values. The QA account `qa_test@conductor.test` / `testtest` always works. To
> reset an employee's local password:
>
> ```bash
> .venv/Scripts/python.exe -c "
> import psycopg2
> from app.auth import hash_password
> conn = psycopg2.connect('postgresql://conductor:conductor@127.0.0.1:5432/conductor_dev')
> cur = conn.cursor()
> cur.execute('UPDATE employees SET password_hash = %s WHERE email = %s',
>             (hash_password('testtest'), 'tim@irrigationengineers.com'))
> conn.commit()
> conn.close()
> "
> ```

## Safety and reset

- Never point `CONDUCTOR_DATABASE_URL` at production when running locally.
- `scripts/start-local.sh` defaults to `postgresql://conductor:conductor@127.0.0.1:5432/conductor_dev`.
- Tests use `CONDUCTOR_TEST_DATABASE_URL` and reset `conductor_test` per test; do not use `conductor_dev` for tests.
- To deliberately replace all local development data with the local snapshot, stop the server and run this command. It drops **only** the `conductor_dev` public schema, then restores the gitignored snapshot:

  ```bash
  PG_BIN='/c/Program Files/PostgreSQL/17/bin'
  export PGPASSWORD=conductor
  "$PG_BIN/psql.exe" -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U conductor -d conductor_dev -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
  "$PG_BIN/psql.exe" -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U conductor -d conductor_dev -f db/local-test-server.sql
  ```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `PostgreSQL is not accepting local connections` | Start the **postgresql-x64-17** Windows service, then retry. |
| `role "conductor" does not exist` or `database "conductor_dev" does not exist` | Run the one-time database-creation block above. |
| App starts but frontend is blank | Let the launcher finish `npm --prefix frontend run build`, then refresh the fixed URL. |
| Port 3100 is already in use | Stop the process using it. Do not change the canonical port; the stable browser link is part of the local workflow. |

## Agent workflow

An agent working from any fresh clone should read this file, run `bash scripts/start-local.sh` in a tracked background process, wait for the `Uvicorn running on http://127.0.0.1:3100` line, and verify both `/` and `/api/clients` before reporting the server ready.
