# Backups (3-2-1 Strategy)

> 3 copies, 2 media types, 1 offsite. No single point of failure.

## How It Works

- **3am daily:** `scripts/backup.sh` runs on the droplet via cron — dumps the database (`pg_dump`, gzipped) and archives `uploads/` to `/var/www/conductor/backups/`
- **4am daily:** `dodge-wsl` pulls backups via rsync over Tailscale to `/mnt/d/Dropbox/TIE/Backups/conductor/` (Dropbox syncs to cloud automatically)
- **Weekly:** DigitalOcean takes full droplet snapshots (enabled in DO console, $1/mo)

## Backup Locations (4 Copies)

| Copy | Location | Type | Retention |
|------|----------|------|-----------|
| 1 | Droplet `/var/www/conductor/backups/` | pg_dump + uploads tar | 7 daily |
| 2 | DO weekly snapshots | Full droplet image | 4 weekly (DO managed) |
| 3 | `dodge-wsl` → Dropbox | rsync pull over Tailscale | 7 daily (matches server) |
| 4 | Dropbox cloud | Auto-sync from copy 3 | Dropbox versioning |

## Backup Files

- `conductor_YYYY-MM-DD.sql.gz` — PostgreSQL dump
- `uploads_YYYY-MM-DD.tar.gz` — Uploads directory archive

## Cron Jobs

- **Droplet:** `0 3 * * * /var/www/conductor/scripts/backup.sh >> /var/log/conductor-backup.log 2>&1`
- **dodge-wsl** (tim's crontab): `0 4 * * * rsync -avz root@100.105.238.37:/var/www/conductor/backups/ /mnt/d/Dropbox/TIE/Backups/conductor/ >> /tmp/conductor-backup-sync.log 2>&1`

## Restore Procedures

### Restore database from backup

```bash
# On the droplet (or any machine with psql access):
gunzip -c conductor_YYYY-MM-DD.sql.gz | psql -U conductor conductor

# To restore to a test database first:
gunzip -c conductor_YYYY-MM-DD.sql.gz | psql -U conductor conductor_test
```

### Restore uploads from backup

```bash
tar xzf uploads_YYYY-MM-DD.tar.gz -C /var/www/conductor/
```

### Full server rebuild (worst case)

1. Create new droplet (or restore from DO snapshot)
2. Install PostgreSQL, Python 3.12, Caddy, Tailscale
3. Clone repo: `git clone https://github.com/timgrote/podium.git /var/www/conductor`
4. Run `scripts/deploy.sh` to set up venv, deps, and frontend build
5. Configure systemd service (`conductor-api.service`) with `CONDUCTOR_DATABASE_URL`
6. Restore database: `gunzip -c conductor_YYYY-MM-DD.sql.gz | psql -U conductor conductor`
7. Restore uploads: `tar xzf uploads_YYYY-MM-DD.tar.gz -C /var/www/conductor/`
8. Re-run backup setup (see below)
9. Verify: `curl http://localhost:3000/api/company`

## Re-deploying the Backup System

### On a new server

```bash
# 1. Create backups directory
mkdir -p /var/www/conductor/backups

# 2. Make backup script executable (already in repo)
chmod +x /var/www/conductor/scripts/backup.sh

# 3. Add cron job
(crontab -l 2>/dev/null; echo "0 3 * * * /var/www/conductor/scripts/backup.sh >> /var/log/conductor-backup.log 2>&1") | crontab -

# 4. Test it
bash /var/www/conductor/scripts/backup.sh

# 5. Verify
ls -lh /var/www/conductor/backups/
```

### On dodge-wsl (or any local machine)

```bash
# 1. Ensure SSH key is on the droplet
ssh-copy-id root@100.105.238.37

# 2. Create local directory
mkdir -p /mnt/d/Dropbox/TIE/Backups/conductor

# 3. Test rsync
rsync -avz root@100.105.238.37:/var/www/conductor/backups/ /mnt/d/Dropbox/TIE/Backups/conductor/

# 4. Add cron (daily at 4am, after 3am server backup)
(crontab -l 2>/dev/null; echo "0 4 * * * rsync -avz root@100.105.238.37:/var/www/conductor/backups/ /mnt/d/Dropbox/TIE/Backups/conductor/ >> /tmp/conductor-backup-sync.log 2>&1") | crontab -
```

## Optional: DO Spaces

If you want a cloud copy independent of Dropbox, create a DO Spaces bucket (`conductor-backups`), install `s3cmd` on the droplet, and configure it. The backup script already handles Spaces upload and retention (7 daily, 4 weekly, 3 monthly) — it activates automatically when `s3cmd` is configured.
