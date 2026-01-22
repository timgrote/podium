# Database

SQLite database for Podium, running on the n8n DigitalOcean droplet.

## Production Database

| Component | Path |
|-----------|------|
| **Host** | `n8n.irrigationengineers.com` (DigitalOcean droplet) |
| **Database file (host)** | `/opt/n8n-docker-caddy/local_files/podium.db` |
| **Database file (n8n container)** | `/files/podium.db` |
| **SSH key** | `~/.ssh/digitalocean_n8n` |

### Quick Access

```bash
# SSH to droplet and query database
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com \
  "sqlite3 /opt/n8n-docker-caddy/local_files/podium.db 'SELECT id, name, status FROM projects'"

# Interactive SQLite shell
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com \
  "sqlite3 /opt/n8n-docker-caddy/local_files/podium.db"

# Via n8n API (no SSH needed)
curl 'https://n8n.irrigationengineers.com/webhook/podium-api?action=list'
```

## Files

- `schema.sql` - Database schema (tables, indexes, views)
- `migrations/` - SQL migration scripts
- `init_db.py` - Initialize database with schema and optional seed data
- `podium.db` - Local database file (gitignored)

## Local Development

```bash
# Create fresh database with test data
python3 init_db.py

# Create fresh database without seed data
python3 init_db.py --no-seed

# Add seed data to existing database
python3 init_db.py --seed-only
```

## Production Deployment

The database file lives on the server at:
```
/opt/n8n-docker-caddy/local_files/podium.db
```

This is mounted into the n8n Docker container as `/files/podium.db`.

### First-time setup on server

```bash
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com

# Create local_files directory if needed
mkdir -p /opt/n8n-docker-caddy/local_files

# Copy init script and schema
cd /opt/n8n-docker-caddy/podium/db
python3 init_db.py --no-seed

# Move to local_files directory
mv podium.db /opt/n8n-docker-caddy/local_files/
```

### n8n SQLite Node Setup

1. Install the community SQLite node in n8n:
   - Go to Settings → Community Nodes
   - Install: `n8n-nodes-sqlite3`

2. Configure the node with path:
   ```
   /files/podium.db
   ```
   (The n8n container mounts `/opt/n8n-docker-caddy/local_files` as `/files`)

## Backup

### Manual backup
```bash
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com \
  "cp /opt/n8n-docker-caddy/local_files/podium.db /opt/n8n-docker-caddy/backups/podium-\$(date +%Y%m%d-%H%M).db"
```

### Automated backup (cron)
```bash
# Add to crontab on droplet: backup every hour
0 * * * * cp /opt/n8n-docker-caddy/local_files/podium.db /opt/n8n-docker-caddy/backups/podium-$(date +\%Y\%m\%d-\%H\%M).db
```

### Export to Google Sheets
Use the `podium-db-export` n8n workflow to dump tables to Google Sheets for manual editing.

## Schema Changes

When adding columns or tables:

1. Update `schema.sql` with the change
2. Create a migration script in `migrations/` (e.g., `002_add_my_column.sql`)
3. Run migration on server:
   ```bash
   ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com \
     "sqlite3 /opt/n8n-docker-caddy/local_files/podium.db 'ALTER TABLE projects ADD COLUMN new_field TEXT;'"
   ```
4. Update n8n workflows if needed

## Tables

| Table | Purpose |
|-------|---------|
| `clients` | Companies/people we bill |
| `contacts` | Individual people (PMs, etc.) |
| `projects` | Jobs we're working on |
| `project_contacts` | Junction: who's on which project |
| `contracts` | Signed agreements |
| `proposals` | Unsigned quotes |
| `proposal_tasks` | Line items on proposals |
| `invoices` | Both task & list types |
| `invoice_line_items` | Line items on invoices |

## Views

| View | Purpose |
|------|---------|
| `v_project_summary` | Projects with computed totals |
| `v_invoices` | Invoices with project/client info |
