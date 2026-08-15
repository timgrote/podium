#!/usr/bin/env bash
# Start the local Podium/Conductor test server at http://127.0.0.1:3001.
# Port 3001 is the canonical test-server port: master's frontend shows the
# amber "TEST SERVER" banner automatically on this port, and production (port 80)
# never does.
set -euo pipefail
unset PYTHONHOME PYTHONPATH

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export CONDUCTOR_DATABASE_URL="${CONDUCTOR_DATABASE_URL:-postgresql://conductor:conductor@127.0.0.1:5432/conductor_dev}"
PORT="${CONDUCTOR_PORT:-3001}"

# --- Python venv + deps ---
if [[ -x ".venv/Scripts/python.exe" ]]; then
  PYTHON=".venv/Scripts/python.exe"
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
else
  uv venv --python python .venv
  PYTHON=".venv/Scripts/python.exe"; [[ -x "$PYTHON" ]] || PYTHON=".venv/bin/python"
fi
uv pip install --python "$PYTHON" -r requirements.txt

# --- PostgreSQL must be listening ---
PG_ISREADY="$(command -v pg_isready || true)"
if [[ -z "$PG_ISREADY" && -x "/c/Program Files/PostgreSQL/17/bin/pg_isready.exe" ]]; then
  PG_ISREADY="/c/Program Files/PostgreSQL/17/bin/pg_isready.exe"
fi
if [[ -z "$PG_ISREADY" ]] || ! "$PG_ISREADY" -h 127.0.0.1 -p 5432 -q; then
  echo "PostgreSQL is not accepting local connections on 127.0.0.1:5432." >&2
  echo "Install/start PostgreSQL and create the conductor/conductor_dev databases." >&2
  echo "See docs/local-test-server.md." >&2
  exit 1
fi

# --- Initialize an empty local DB if needed ---
if "$PYTHON" - <<'PY'
import os, sys, psycopg2
url = os.environ["CONDUCTOR_DATABASE_URL"]
try:
    with psycopg2.connect(url) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.clients')")
        ok = cur.fetchone()[0] is not None
except Exception as e:
    print(f"Cannot connect to local dev DB: {e}", file=sys.stderr); sys.exit(1)
sys.exit(0 if ok else 2)
PY
then
  :
else
  status=$?
  if [[ "$status" == "2" ]]; then
    if [[ -f "$ROOT/db/local-test-server.sql" ]]; then
      PSQL="$(command -v psql || true)"
      [[ -z "$PSQL" && -x "/c/Program Files/PostgreSQL/17/bin/psql.exe" ]] && PSQL="/c/Program Files/PostgreSQL/17/bin/psql.exe"
      echo "Restoring local test snapshot db/local-test-server.sql"
      "$PSQL" -X -v ON_ERROR_STOP=1 "$CONDUCTOR_DATABASE_URL" -f "$ROOT/db/local-test-server.sql"
    else
      "$PYTHON" db/init_db.py --no-seed
    fi
  else
    exit "$status"
  fi
fi

# --- Frontend (built SPA served by FastAPI) ---
mkdir -p uploads
npm --prefix frontend ci
npm --prefix frontend run build

printf '\nPodium test server: http://127.0.0.1:%s  (orange TEST SERVER banner shows)\n\n' "$PORT"
exec "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --reload
