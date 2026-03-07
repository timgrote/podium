#!/usr/bin/env bash
#
# Conductor backup script (3-2-1 strategy)
# Runs daily via cron on the production droplet.
#
# Backs up:
#   1. PostgreSQL database (pg_dump, gzipped)
#   2. uploads/ directory (tar.gz)
#
# Stores backups in:
#   - Local: /var/www/conductor/backups/
#   - DO Spaces: s3://conductor-backups/ (if s3cmd configured)
#
# Retention: 7 daily, 4 weekly (Sunday), 3 monthly (1st)
#
# Usage:
#   bash /var/www/conductor/scripts/backup.sh
#
# Cron (daily at 3am):
#   0 3 * * * /var/www/conductor/scripts/backup.sh >> /var/log/conductor-backup.log 2>&1
#
set -euo pipefail

REPO_DIR="/var/www/conductor"
BACKUP_DIR="$REPO_DIR/backups"
SERVICE="conductor-api"
DATE=$(date +%Y-%m-%d)
DAY_OF_WEEK=$(date +%u)  # 7 = Sunday
DAY_OF_MONTH=$(date +%d)
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

log() { echo "$LOG_PREFIX $*"; }

# ── Get database URL from systemd ─────────────────────────────────────
DB_URL=$(systemctl show "$SERVICE" -p Environment --value \
    | tr ' ' '\n' \
    | grep '^CONDUCTOR_DATABASE_URL=' \
    | cut -d= -f2- || true)

if [ -z "$DB_URL" ]; then
    ENV_FILE=$(systemctl show "$SERVICE" -p EnvironmentFile --value | tr -d '"' || true)
    if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
        DB_URL=$(grep '^CONDUCTOR_DATABASE_URL=' "$ENV_FILE" | cut -d= -f2- || true)
    fi
fi

if [ -z "$DB_URL" ]; then
    log "FATAL: Could not read CONDUCTOR_DATABASE_URL from $SERVICE environment"
    exit 1
fi

# ── Create backup directory ────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

# ── 1. Database dump ──────────────────────────────────────────────────
DB_FILE="$BACKUP_DIR/conductor_${DATE}.sql.gz"
log "Dumping database..."
pg_dump "$DB_URL" | gzip > "$DB_FILE"
DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
log "Database dump complete: $DB_FILE ($DB_SIZE)"

# ── 2. Uploads archive ────────────────────────────────────────────────
UPLOADS_FILE="$BACKUP_DIR/uploads_${DATE}.tar.gz"
if [ -d "$REPO_DIR/uploads" ]; then
    log "Archiving uploads..."
    tar czf "$UPLOADS_FILE" -C "$REPO_DIR" uploads/
    UPL_SIZE=$(du -h "$UPLOADS_FILE" | cut -f1)
    log "Uploads archive complete: $UPLOADS_FILE ($UPL_SIZE)"
else
    log "No uploads directory found, skipping."
fi

# ── 3. Push to DO Spaces (if s3cmd configured) ────────────────────────
if command -v s3cmd &>/dev/null && [ -f "$HOME/.s3cfg" ]; then
    log "Uploading to DO Spaces..."
    s3cmd put "$DB_FILE" s3://conductor-backups/daily/
    [ -f "$UPLOADS_FILE" ] && s3cmd put "$UPLOADS_FILE" s3://conductor-backups/daily/

    # Copy to weekly/monthly folders for retention
    if [ "$DAY_OF_WEEK" = "7" ]; then
        log "Sunday — copying to weekly/"
        s3cmd put "$DB_FILE" s3://conductor-backups/weekly/
        [ -f "$UPLOADS_FILE" ] && s3cmd put "$UPLOADS_FILE" s3://conductor-backups/weekly/
    fi
    if [ "$DAY_OF_MONTH" = "01" ]; then
        log "1st of month — copying to monthly/"
        s3cmd put "$DB_FILE" s3://conductor-backups/monthly/
        [ -f "$UPLOADS_FILE" ] && s3cmd put "$UPLOADS_FILE" s3://conductor-backups/monthly/
    fi
    log "Spaces upload complete."
else
    log "s3cmd not configured — skipping Spaces upload (local backup only)"
fi

# ── 4. Local retention pruning ─────────────────────────────────────────
log "Pruning old local backups..."

# Keep last 7 daily backups
ls -t "$BACKUP_DIR"/conductor_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -v
ls -t "$BACKUP_DIR"/uploads_*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm -v

log "Local pruning complete."

# ── 5. Spaces retention pruning (if configured) ───────────────────────
if command -v s3cmd &>/dev/null && [ -f "$HOME/.s3cfg" ]; then
    log "Pruning old Spaces backups..."

    # Daily: keep 7
    s3cmd ls s3://conductor-backups/daily/ 2>/dev/null \
        | awk '{print $NF}' \
        | grep 'conductor_' \
        | sort -r \
        | tail -n +8 \
        | xargs -r -I {} s3cmd del {}

    s3cmd ls s3://conductor-backups/daily/ 2>/dev/null \
        | awk '{print $NF}' \
        | grep 'uploads_' \
        | sort -r \
        | tail -n +8 \
        | xargs -r -I {} s3cmd del {}

    # Weekly: keep 4
    s3cmd ls s3://conductor-backups/weekly/ 2>/dev/null \
        | awk '{print $NF}' \
        | grep 'conductor_' \
        | sort -r \
        | tail -n +5 \
        | xargs -r -I {} s3cmd del {}

    s3cmd ls s3://conductor-backups/weekly/ 2>/dev/null \
        | awk '{print $NF}' \
        | grep 'uploads_' \
        | sort -r \
        | tail -n +5 \
        | xargs -r -I {} s3cmd del {}

    # Monthly: keep 3
    s3cmd ls s3://conductor-backups/monthly/ 2>/dev/null \
        | awk '{print $NF}' \
        | grep 'conductor_' \
        | sort -r \
        | tail -n +4 \
        | xargs -r -I {} s3cmd del {}

    s3cmd ls s3://conductor-backups/monthly/ 2>/dev/null \
        | awk '{print $NF}' \
        | grep 'uploads_' \
        | sort -r \
        | tail -n +4 \
        | xargs -r -I {} s3cmd del {}

    log "Spaces pruning complete."
fi

log "Backup complete."
