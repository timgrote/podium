#!/usr/bin/env bash
# Start the self-contained local Conductor test server at http://127.0.0.1:3100.
set -euo pipefail
# Hermes may export a PYTHONPATH for its own venv. Do not let it leak into the app venv.
unset PYTHONHOME PYTHONPATH

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export CONDUCTOR_DATABASE_URL="${CONDUCTOR_DATABASE_URL:-postgresql://conductor:conductor@127.0.0.1:5432/conductor_dev}"
PORT="${CONDUCTOR_PORT:-3100}"

if [[ -x ".venv/Scripts/python.exe" ]]; then
  PYTHON=".venv/Scripts/python.exe"
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
else
  uv venv --python python .venv
  PYTHON=".venv/Scripts/python.exe"
  [[ -x "$PYTHON" ]] || PYTHON=".venv/bin/python"
fi

uv pip install --python "$PYTHON" -r requirements.txt

PG_ISREADY="$(command -v pg_isready || true)"
PSQL="$(command -v psql || true)"
if [[ -z "$PG_ISREADY" && -x "/c/Program Files/PostgreSQL/17/bin/pg_isready.exe" ]]; then
  PG_ISREADY="/c/Program Files/PostgreSQL/17/bin/pg_isready.exe"
fi
if [[ -z "$PSQL" && -x "/c/Program Files/PostgreSQL/17/bin/psql.exe" ]]; then
  PSQL="/c/Program Files/PostgreSQL/17/bin/psql.exe"
fi
if [[ -z "$PG_ISREADY" ]] || ! "$PG_ISREADY" -h 127.0.0.1 -p 5432 -q; then
  echo "PostgreSQL is not accepting local connections on 127.0.0.1:5432." >&2
  echo "Install/start PostgreSQL, then create the conductor and conductor_dev databases." >&2
  echo "See docs/local-test-server.md." >&2
  exit 1
fi

if "$PYTHON" - <<'PY'
import os
import sys
import psycopg2

url = os.environ["CONDUCTOR_DATABASE_URL"]
try:
    with psycopg2.connect(url) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.clients')")
        initialized = cur.fetchone()[0] is not None
except Exception as exc:
    print(f"Cannot connect to local development database: {exc}", file=sys.stderr)
    sys.exit(1)
if not initialized:
    print("Local development database is empty; initializing schema and seed data.")
    sys.exit(2)
PY
then
  :
else
  status=$?
  if [[ "$status" == "2" ]]; then
    SNAPSHOT="$ROOT/db/local-test-server.sql"
    if [[ -f "$SNAPSHOT" ]]; then
      if [[ -z "$PSQL" ]]; then
        echo "psql is required to restore $SNAPSHOT." >&2
        exit 1
      fi
      echo "Restoring local development snapshot: $SNAPSHOT"
      "$PSQL" -X -v ON_ERROR_STOP=1 "$CONDUCTOR_DATABASE_URL" -f "$SNAPSHOT"
    else
      "$PYTHON" db/init_db.py --no-seed
    fi
  else
    exit "$status"
  fi
fi

mkdir -p uploads
npm --prefix frontend ci
npm --prefix frontend run build

printf '\nConductor local test server: http://127.0.0.1:%s\n\n' "$PORT"
exec "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --reload
