#!/bin/bash
# Deploy Podium database to server
# Run this ON THE SERVER after SSHing in

set -e

echo "=== Podium Database Deployment ==="

# Paths
PODIUM_DIR="/opt/n8n-docker-caddy/podium"
DATA_DIR="/opt/n8n-docker-caddy/data"
DB_FILE="$DATA_DIR/podium.db"

# Check we're in the right place
if [ ! -d "$PODIUM_DIR" ]; then
    echo "ERROR: $PODIUM_DIR not found. Are you on the right server?"
    exit 1
fi

# Create data directory
mkdir -p "$DATA_DIR"
echo "Created $DATA_DIR"

# Pull latest code
cd "$PODIUM_DIR"
git fetch origin
git checkout feature/db-schema
git pull origin feature/db-schema
echo "Pulled latest from feature/db-schema"

# Initialize database
cd "$PODIUM_DIR/db"
if [ -f "$DB_FILE" ]; then
    echo "WARNING: Database already exists at $DB_FILE"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted"
        exit 1
    fi
    rm "$DB_FILE"
fi

python3 init_db.py --no-seed
mv podium.db "$DB_FILE"
echo "Database initialized at $DB_FILE"

# Set permissions (n8n needs read/write)
chmod 664 "$DB_FILE"
chown root:root "$DB_FILE"

# Verify
echo ""
echo "=== Verification ==="
python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
tables = [r[0] for r in cur.fetchall()]
print(f'Tables: {len(tables)}')
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'  {t}: {cur.fetchone()[0]} rows')
"

echo ""
echo "=== Done ==="
echo "Database ready at: $DB_FILE"
echo ""
echo "Next: Install n8n-nodes-sqlite3 in n8n UI"
echo "  Settings → Community Nodes → Install → n8n-nodes-sqlite3"
