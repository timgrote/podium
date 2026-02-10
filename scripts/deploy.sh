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
    | cut -d= -f2-)

if [ -z "$DB_URL" ]; then
    echo "FATAL: Could not read CONDUCTOR_DATABASE_URL from $SERVICE environment"
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
    EXISTING=$(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null)
    if [ -n "$EXISTING" ]; then
        echo "    First run — seeding tracking table with existing migrations..."
        for f in $EXISTING; do
            BASENAME=$(basename "$f")
            run_sql -c "INSERT INTO _migrations (filename) VALUES ('$BASENAME')" >/dev/null
            echo "    Marked as applied: $BASENAME"
        done
    fi
fi

# Apply any new migrations
if [ -d "$MIGRATIONS_DIR" ]; then
    for f in "$MIGRATIONS_DIR"/*.sql; do
        [ -f "$f" ] || continue
        BASENAME=$(basename "$f")
        ALREADY=$(run_sql -tAc "SELECT 1 FROM _migrations WHERE filename = '$BASENAME'")
        if [ "$ALREADY" = "1" ]; then
            echo "    Skip (already applied): $BASENAME"
            continue
        fi
        echo "    Applying: $BASENAME"
        run_sql -f "$f"
        run_sql -c "INSERT INTO _migrations (filename) VALUES ('$BASENAME')" >/dev/null
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
echo "--- journalctl output ---"
journalctl -u "$SERVICE" --no-pager -n 30
exit 1
