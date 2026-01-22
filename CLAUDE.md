# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Podium is a multi-tenant SaaS platform for project-based service businesses. The initial vertical is irrigation design, but the architecture supports any service business.

## Architecture

```
Frontend (Static HTML/JS)  →  n8n Webhooks  →  SQLite Database
     ↓                           ↓                   ↓
Caddy (TLS/Auth)           Workflow Logic      /files/podium.db
```

**Three layers:**
1. **Ops** (`/ops`) - Project management dashboard (protected by OAuth)
   - `dashboard.html` - Main project list with expandable details
   - `project.html` - Individual project view
   - `clients.html` - Client management
   - `settings.html` - Company settings
2. **Flows** (`/flows`) - Client-facing pages (public): proposal, contract, invoice, payment
3. **Integrations** (`/integrations`) - External services (Todoist, Gmail)

## Development

```bash
# Local server
python -m http.server 3000
# Open: http://localhost:3000/ops/dashboard.html

# Initialize local dev database with seed data
cd db && python3 init_db.py

# Init without seed data
cd db && python3 init_db.py --no-seed
```

## Deployment

Auto-deploys on push to `master` or `main` via GitHub Actions. Static files only, no build step.

```bash
# Manual deploy
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com \
  "cd /opt/n8n-docker-caddy/podium && git pull"
```

## Database Access

```bash
# Query database directly
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com \
  "sqlite3 /opt/n8n-docker-caddy/local_files/podium.db 'SELECT id, name, status FROM projects'"
```

The database file is at `/opt/n8n-docker-caddy/local_files/podium.db` on the host, mounted as `/files/podium.db` in the n8n container.

## API Endpoints

All APIs are n8n webhooks at `https://n8n.irrigationengineers.com`:

| Endpoint | Purpose |
|----------|---------|
| `/webhook/podium-api` | Project CRUD (action: list, get, create, update, add_invoice, update_invoice) |
| `/webhook/podium-clients` | Client CRUD (action: list, search, get, create, update, delete) |
| `/webhook/podium-company` | Company settings |
| `/webhook/podium-invoice-create` | Create invoice from Google Sheets template |
| `/webhook/podium-invoice-send` | Export PDF and email invoice |
| `/webhook/podium-sheet-delete` | Delete a Google Sheet by URL |

## Database Schema

Key tables (see `db/schema.sql` for full schema):
- `clients` - Companies/people we bill
- `contacts` - Individual people (PMs, engineers)
- `projects` - Jobs with status workflow
- `invoices` - Both task-based and list-based invoices (type: 'task' or 'list')
- `invoice_line_items` - Line items on invoices
- `contracts`, `proposals`, `proposal_tasks`

Views: `v_project_summary`, `v_invoices`

Status workflow: `proposal → contract → invoiced → paid → complete`

## Key Patterns

- **n8n orchestration** - All data operations go through webhooks. See `ops/workflows/n8n-code-snippets/` for reusable SQL query builders.
- **Invoice chaining** - Task-based invoices link via `previous_invoice_id`. Line items track `previous_billing` for cumulative totals.
- **Invoice storage** - `data_path` stores Google Sheet URLs, `pdf_path` stores generated PDF paths.
- **Soft deletes** - All tables use `deleted_at` for soft deletion.
- **Invoice template** - Google Sheet ID `16QHE3DdF0AAQtLgXUZSx8c9T2q3dvTvKwjb90B5yGcI`

## Frontend Data Flow

The dashboard fetches project lists with nested contracts/invoices via JSON aggregation in SQLite:
```
API call → n8n webhook → Code node (parse-and-build-query.js) → SQLite → format-response.js → JSON
```

## What AI Should NOT Do

- Don't create separate files for each project (use the API/database)
- Don't hardcode project data in HTML
- Don't bypass n8n for data operations
- Don't modify production database directly except for schema migrations
