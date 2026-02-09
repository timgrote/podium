# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Conductor is a multi-tenant SaaS platform for project-based service businesses. The initial vertical is irrigation design, but the architecture supports any service business.

## Architecture

```
Frontend (Static HTML/JS)  →  FastAPI (/api/*)  →  SQLite Database
     ↓                           ↓                      ↓
Caddy (TLS/Auth)           app/routers/*          db/conductor.db
```

**Three layers:**
1. **Ops** (`/ops`) - Project management dashboard (protected by OAuth2 Proxy in production)
2. **Flows** (`/flows`) - Client-facing pages (public): proposal, contract, invoice, payment
3. **API** (`/api`) - FastAPI routers: clients, company, projects, contracts, proposals, invoices, flows

FastAPI serves both API routes and static files from a single process (`app/main.py`). Static mounts: `/ops`, `/flows`, `/uploads`, then `/` (root last to avoid shadowing).

## Development

```bash
# First-time setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd db && python3 init_db.py && cd ..

# Start server
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload

# Open: http://localhost:3000/ops/dashboard.html
```

### Database initialization options

```bash
python3 db/init_db.py              # Fresh DB with seed data (3 clients, 3 projects, invoices, etc.)
python3 db/init_db.py --no-seed    # Fresh DB, schema only
python3 db/init_db.py --seed-only  # Add seed data to existing DB
```

## Deployment

Auto-deploys on push to `master`, `main`, or `feature/db-schema` via GitHub Actions (`.github/workflows/deploy.yml`). No build step — just `git reset --hard` on the droplet.

```bash
# Manual deploy
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com \
  "cd /opt/n8n-docker-caddy/podium && git pull"
```

## Configuration

All settings use `CONDUCTOR_` prefix, loaded via pydantic-settings in `app/config.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CONDUCTOR_DB_PATH` | `db/conductor.db` | Path to SQLite database |
| `CONDUCTOR_HOST` | `0.0.0.0` | Server bind address |
| `CONDUCTOR_PORT` | `3000` | Server port |
| `CONDUCTOR_UPLOAD_DIR` | `uploads/` | File upload directory |
| `CONDUCTOR_GOOGLE_SERVICE_ACCOUNT_JSON` | | Base64-encoded Google credentials (production) |
| `CONDUCTOR_GOOGLE_SERVICE_ACCOUNT_PATH` | | Path to Google credentials JSON (local dev) |
| `CONDUCTOR_INVOICE_TEMPLATE_ID` | `16QHE3DdF0AAQtLgXUZSx8c9T2q3dvTvKwjb90B5yGcI` | Google Sheets invoice template |
| `CONDUCTOR_INVOICE_DRIVE_FOLDER_ID` | | Google Drive folder for generated invoices |

## API Endpoints

All APIs are local FastAPI routes at `/api/*`:

| Endpoint | Purpose |
|----------|---------|
| `/api/clients` | Client CRUD |
| `/api/company` | Company settings (GET / PUT), logo upload |
| `/api/projects` | Project CRUD + detail views with nested contracts/invoices/proposals |
| `/api/contracts` | Contract management + contract tasks |
| `/api/proposals` | Proposal CRUD |
| `/api/invoices` | Invoice management + Google Sheets export/PDF/email |
| `/api/flows` | Public flow data for client-facing pages |

Standard CRUD pattern: `GET /` (list), `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}` (soft delete).

## Database Schema

Key tables (see `db/schema.sql` for full schema):
- `clients` - Companies/people we bill
- `contacts` - Individual people (PMs, engineers)
- `projects` - Jobs with status workflow; IDs are human-readable job codes (e.g., `JBHL21`)
- `contracts` - Signed agreements
- `contract_tasks` - Tasks/phases on contracts with billing tracking
- `invoices` - Both task-based and list-based invoices
- `invoice_line_items` - Line items on invoices
- `proposals`, `proposal_tasks`
- `company_settings` - Key-value store for company name, logo, colors, etc.

Views: `v_project_summary` (projects with computed totals), `v_invoices` (invoices with project/client info).

Status workflow: `proposal → contract → invoiced → paid → complete`

## Key Patterns

- **ID generation**: Short 8-char UUIDs with entity prefixes — `c-` (client), `con-` (contract), `prop-` (proposal), `inv-` (invoice). See `app/utils.py:generate_id()`.
- **Soft deletes**: All tables have `deleted_at` column. Queries must filter `WHERE deleted_at IS NULL`.
- **Database access**: Use `Depends(get_db)` for FastAPI dependency injection. Connection uses `sqlite3.Row` factory and enables foreign keys.
- **Invoice chaining**: `previous_invoice_id` links invoices for task-based billing across multiple pay apps.
- **Contract tasks**: Track `billed_amount` and `billed_percent` for partial billing.
- **File uploads**: Stored in `uploads/` directory, paths saved in database.
- **Frontend**: Vanilla HTML/JS with fetch API calls to `/api/*` — no frameworks, no build step.
- **Google integration**: Optional Sheets/Drive/Gmail via `app/google_sheets.py`. Check for credentials before using.

## What AI Should NOT Do

- Don't create separate files for each project (use the API/database)
- Don't hardcode project data in HTML
- Don't modify production database directly except for schema migrations
- Don't skip `deleted_at IS NULL` checks in queries
- Don't create raw SQL without parameter binding (use `?` placeholders)
