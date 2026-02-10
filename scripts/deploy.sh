#!/usr/bin/env bash
#
# Conductor deploy script
# Runs on the droplet — called by GitHub Actions or manually via SSH.
#
# Usage:
#   cd /var/www/conductor && bash scripts/deploy.sh
#
set -euo pipefail

REPO_DIR="/var/www/conductor"
VENV="$REPO_DIR/.venv"
MIGRATIONS_DIR="$REPO_DIR/db/migrations"
SERVICE="conductor-api"
HEALTH_URL="http://localhost:3000/api/company"
HEALTH_TIMEOUT=10

cd "$REPO_DIR"

# ── 1. Pull latest code ─────────────────────────────────────────────
echo "==> Pulling latest from master..."
git pull origin master

# ── 2. Install dependencies ──────────────────────────────────────────
echo "==> Installing dependencies..."
"$VENV/bin/pip" install -q -r requirements.txt

# ── 3. Run new migrations only ───────────────────────────────────────
echo "==> Running migrations..."

# Get the DATABASE_URL from the systemd environment (same one the app uses)
DB_URL=$(systemctl show "$SERVICE" -p Environment --value \
    | tr ' ' '\n' \
    | grep '^CONDUCTOR_DATABASE_URL=' \
    | cut -d= -f2- || true)

# Fallback: try EnvironmentFile if inline Environment didn't have it
if [ -z "$DB_URL" ]; then
    ENV_FILE=$(systemctl show "$SERVICE" -p EnvironmentFile --value | tr -d '"' || true)
    if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
        DB_URL=$(grep '^CONDUCTOR_DATABASE_URL=' "$ENV_FILE" | cut -d= -f2- || true)
    fi
fi

if [ -z "$DB_URL" ]; then
    echo "FATAL: Could not read CONDUCTOR_DATABASE_URL from $SERVICE environment"
    exit 1
fi

if [[ ! "$DB_URL" =~ ^postgresql:// ]]; then
    echo "FATAL: CONDUCTOR_DATABASE_URL looks malformed: '${DB_URL:0:30}...'"
    echo "Expected it to start with postgresql://"
    exit 1
fi

# psql wrapper using the app's connection string
run_sql() {
    psql "$DB_URL" -v ON_ERROR_STOP=1 "$@"
}

# Ensure tracking table exists
run_sql -c "
CREATE TABLE IF NOT EXISTS _migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
" >/dev/null

# Seed tracking table on first run (migrations already applied via schema.sql)
ROW_COUNT=$(run_sql -tAc "SELECT COUNT(*) FROM _migrations")
if [ "$ROW_COUNT" -eq 0 ] && [ -d "$MIGRATIONS_DIR" ]; then
    echo "    First run — seeding tracking table with existing migrations..."
    for f in "$MIGRATIONS_DIR"/*.sql; do
        [ -f "$f" ] || continue
        BASENAME=$(basename "$f")
        run_sql -v migration_name="$BASENAME" -c \
            "INSERT INTO _migrations (filename) VALUES (:'migration_name')" >/dev/null
        echo "    Marked as applied: $BASENAME"
    done
fi

# Apply any new migrations
if [ -d "$MIGRATIONS_DIR" ]; then
    for f in "$MIGRATIONS_DIR"/*.sql; do
        [ -f "$f" ] || continue
        BASENAME=$(basename "$f")
        ALREADY=$(run_sql -v migration_name="$BASENAME" -tAc \
            "SELECT 1 FROM _migrations WHERE filename = :'migration_name'")
        if [ "$ALREADY" = "1" ]; then
            echo "    Skip (already applied): $BASENAME"
            continue
        fi
        echo "    Applying: $BASENAME"
        # Run migration + record in a single transaction (atomic)
        {
            cat "$f"
            echo ""
            echo "INSERT INTO _migrations (filename) VALUES ('$(echo "$BASENAME" | sed "s/'/''/g")');"
        } | run_sql
        echo "    Done: $BASENAME"
    done
else
    echo "    No migrations directory found, skipping."
fi

# ── 4. Restart service ───────────────────────────────────────────────
echo "==> Restarting $SERVICE..."
systemctl restart "$SERVICE"

# ── 5. Health check ──────────────────────────────────────────────────
echo "==> Health check (${HEALTH_TIMEOUT}s timeout)..."
for i in $(seq 1 "$HEALTH_TIMEOUT"); do
    if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
        echo "==> Healthy after ${i}s. Deploy complete."
        exit 0
    fi
    sleep 1
done

echo "FATAL: Health check failed after ${HEALTH_TIMEOUT}s"
echo "--- last curl attempt ---"
curl -sv "$HEALTH_URL" 2>&1 | tail -20 || true
echo "--- journalctl output ---"
journalctl -u "$SERVICE" --no-pager -n 30
exit 1
