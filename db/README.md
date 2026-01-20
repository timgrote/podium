# Database

SQLite database for Podium.

## Files

- `schema.sql` - Database schema (tables, indexes, views)
- `init_db.py` - Initialize database with schema and optional seed data
- `podium.db` - The actual database file (gitignored)

## Local Development

```bash
# Create fresh database with test data
python3 init_db.py

# Create fresh database without seed data
python3 init_db.py --no-seed

# Add seed data to existing database
python3 init_db.py --seed-only
```

## Deployment

The database file lives on the server at:
```
/opt/n8n-docker-caddy/data/podium.db
```

### First-time setup on server

```bash
ssh root@n8n.irrigationengineers.com

# Create data directory if needed
mkdir -p /opt/n8n-docker-caddy/data

# Copy init script and schema
cd /opt/n8n-docker-caddy/podium/db
python3 init_db.py --no-seed

# Move to data directory
mv podium.db /opt/n8n-docker-caddy/data/
```

### n8n SQLite Node Setup

1. Install the community SQLite node in n8n:
   - Go to Settings → Community Nodes
   - Install: `n8n-nodes-sqlite3`

2. Configure the node with path:
   ```
   /data/podium.db
   ```
   (The n8n container mounts `/opt/n8n-docker-caddy/data` as `/data`)

## Backup

### Manual backup
```bash
cp /opt/n8n-docker-caddy/data/podium.db /backups/podium-$(date +%Y%m%d-%H%M).db
```

### Automated backup (cron)
```bash
# Add to crontab: backup every hour
0 * * * * cp /opt/n8n-docker-caddy/data/podium.db /opt/n8n-docker-caddy/backups/podium-$(date +\%Y\%m\%d-\%H\%M).db
```

### Export to Google Sheets
Use the `podium-db-export` n8n workflow to dump tables to Google Sheets for manual editing.

## Schema Changes

When adding columns or tables:

1. Update `schema.sql` with the change
2. Run migration on server:
   ```bash
   sqlite3 /opt/n8n-docker-caddy/data/podium.db "ALTER TABLE projects ADD COLUMN new_field TEXT;"
   ```
3. Update n8n workflows if needed

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
