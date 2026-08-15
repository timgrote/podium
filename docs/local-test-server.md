# Local Test Server (for a Hermes agent)

Run the Podium/Conductor app locally, against an isolated database, at a fixed
URL that shows an amber **"TEST SERVER"** banner so it can never be confused with
production.

> **URL:** http://127.0.0.1:3001
>
> Port 3001 is deliberate: `frontend/src/composables/useEnvironment.ts` shows the
> amber test banner whenever the app is served on port 3001. Production (port 80)
> never shows it. Do not change the port.

## One command

From the repository root:

```bash
bash scripts/start-local.sh
```

This launcher does everything: creates the Python venv and installs deps (`uv`),
checks PostgreSQL, restores the local snapshot into `conductor_dev` on first run,
builds the Vue SPA, and runs Uvicorn (reload on) at `http://127.0.0.1:3001`.

Stop with `Ctrl+C`. Later starts do not wipe `conductor_dev`.

## Prerequisites (one-time, per machine)

- **Node.js + npm** (18+): `winget install --id OpenJS.NodeJS.LTS --exact --silent`
- **uv**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **PostgreSQL 17**: `winget install --id PostgreSQL.PostgreSQL.17 --exact --silent`
  (accepts port 5432). Then create the local role and databases once:

  ```bash
  PG_BIN='/c/Program Files/PostgreSQL/17/bin'
  export PGPASSWORD=conductor
  PSQL=("$PG_BIN/psql.exe" -X -h 127.0.0.1 -U postgres -d postgres)
  "${PSQL[@]}" -tAc "SELECT 'CREATE ROLE conductor LOGIN PASSWORD ''conductor''' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='conductor')" | "${PSQL[@]}"
  for db in conductor_dev conductor_test; do
    [ "$("${PSQL[@]}" -tAc "SELECT 1 FROM pg_database WHERE datname='$db'")" = "1" ] || "${PSQL[@]}" -c "CREATE DATABASE $db OWNER conductor"
  done
  ```

## Test data (optional but recommended)

To start with realistic data, put a plain PostgreSQL dump at **`db/local-test-server.sql`**
(do not commit it — it may contain business data; it is gitignored). The launcher
restores it into `conductor_dev` on first run. Without it, the schema is created
empty.

**Password gotcha:** dumps carry the production bcrypt hashes, which won't match
your real passwords. Use the QA account **`qa_test@conductor.test` / `testtest`**
(always works), or reset a local password:

```bash
.venv/Scripts/python.exe -c "
import psycopg2
from app.auth import hash_password
c=psycopg2.connect('postgresql://conductor:conductor@127.0.0.1:5432/conductor_dev');cur=c.cursor()
cur.execute('UPDATE employees SET password_hash=%s WHERE email=%s',(hash_password('testtest'),'tim@irrigationengineers.com'));c.commit();c.close()"
```

## Verify it's ready

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3001/          # 200
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3001/api/clients  # 200
```

Then open http://127.0.0.1:3001 — you should see the amber **"TEST SERVER — not
production"** banner. Log in with `qa_test@conductor.test` / `testtest`.

## Safety

- The launcher always points at local `conductor_dev` — never at production.
- Tests use `conductor_test` (`CONDUCTOR_TEST_DATABASE_URL`), separate from `conductor_dev`.
- The local server is bound to loopback only; it is not exposed on the network.
