# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Conductor is a multi-tenant SaaS platform for project-based service businesses. The initial vertical is irrigation design, but the architecture supports any service business.

## Architecture

```
Vue SPA (frontend/dist)  →  FastAPI (/api/*)  →  PostgreSQL Database
     ↓                           ↓                      ↓
Caddy (:80, Tailscale only) app/routers/*          postgresql://...
```

**Layers:**
1. **Dashboard** — Vue 3 SPA served via catch-all route (`/{path:path}` → `index.html`)
2. **Flows** (`/flows`) - Client-facing pages (public): proposal, contract, invoice, payment
3. **API** (`/api`) - FastAPI routers: clients, company, projects, contracts, proposals, invoices, flows

FastAPI serves both API routes and the Vue SPA from a single process (`app/main.py`). Static mounts: `/uploads`, `/flows`, `/assets` (Vite build), then `/{path:path}` catch-all for SPA routing.

## Development

```bash
# First-time setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize database (requires local PostgreSQL running)
python3 db/init_db.py              # Fresh DB with seed data
python3 db/init_db.py --no-seed    # Fresh DB, schema only
python3 db/init_db.py --seed-only  # Add seed data to existing DB

# Start server
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload

# Open: http://localhost:3000
```

### PostgreSQL Setup (Local Dev)

```bash
sudo apt update && sudo apt install postgresql postgresql-contrib
sudo systemctl enable postgresql && sudo systemctl start postgresql
sudo -u postgres createuser --superuser conductor
sudo -u postgres createdb conductor -O conductor
sudo -u postgres psql -c "ALTER USER conductor PASSWORD 'conductor';"
# Also create test database:
sudo -u postgres createdb conductor_test -O conductor
```

### Running Tests

```bash
# Requires conductor_test database to exist
pytest tests/
```

## Deployment

Auto-deploys on push to `master` via GitHub Actions (`.github/workflows/deploy.yml`). The workflow SSHs into the droplet and runs `scripts/deploy.sh`, which handles: git pull, pip install, tracked migrations, service restart, and health check.

```bash
# Manual deploy (same script GitHub Actions runs)
ssh root@100.105.238.37 "cd /var/www/conductor && bash scripts/deploy.sh"
```

### Production environment

- **Access:** Tailscale only — `http://100.105.238.37` (Tailscale: `tie-conductor`). Public internet returns 403.
- **Droplet:** `24.144.82.75` (public IP, blocked by Caddy), `100.105.238.37` (Tailscale)
- **User:** `root`
- **App dir:** `/var/www/conductor`
- **Python:** 3.12.3 in `/var/www/conductor/.venv`
- **Service:** `conductor-api.service` (uvicorn on `127.0.0.1:3000`, localhost only)
- **Reverse proxy:** Caddy on `:80` → `127.0.0.1:3000`, restricted to Tailscale CGNAT range (`100.64.0.0/10`)
- **DB:** PostgreSQL, connection string in systemd `Environment=`
- **GitHub secrets:** `DO_HOST` (public IP), `DO_USER`, `DO_KEY`
- **Logging:** All API requests logged to `conductor.log` with status/timing. Errors (4xx/5xx) include full tracebacks.

### Migration tracking

Migrations in `db/migrations/` are tracked via a `_migrations` table in PostgreSQL. The deploy script only runs new migrations (by filename) and fails fast on errors — no silent `|| true`. On first run it seeds the tracking table with existing migration filenames so they aren't re-applied.

To add a new migration, create a numbered `.sql` file in `db/migrations/` (e.g., `003_add_feature.sql`). Use `IF NOT EXISTS` / `IF EXISTS` guards for idempotency. The next deploy will apply it automatically.

### Backups

Daily automated backups via `scripts/backup.sh` (3-2-1 strategy). See [`docs/backups.md`](docs/backups.md) for restore procedures, redeployment steps, and full details.

## Configuration

All settings use `CONDUCTOR_` prefix, loaded via pydantic-settings in `app/config.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CONDUCTOR_DATABASE_URL` | `postgresql://conductor:conductor@localhost:5432/conductor` | PostgreSQL connection string |
| `CONDUCTOR_HOST` | `0.0.0.0` | Server bind address |
| `CONDUCTOR_PORT` | `3000` | Server port |
| `CONDUCTOR_UPLOAD_DIR` | `uploads/` | File upload directory |
| `CONDUCTOR_GOOGLE_SERVICE_ACCOUNT_JSON` | | Base64-encoded Google credentials (production) |
| `CONDUCTOR_GOOGLE_SERVICE_ACCOUNT_PATH` | | Path to Google credentials JSON (local dev) |
| `CONDUCTOR_INVOICE_TEMPLATE_ID` | `16QHE3DdF0AAQtLgXUZSx8c9T2q3dvTvKwjb90B5yGcI` | Google Sheets invoice template |
| `CONDUCTOR_INVOICE_DRIVE_FOLDER_ID` | | Google Drive folder for generated invoices |

### Endpoint Configuration

| Environment | `CONDUCTOR_DATABASE_URL` |
|------------|--------------------------|
| Local dev | `postgresql://conductor:conductor@localhost:5432/conductor` |
| Local → live | `postgresql://conductor:<pw>@<droplet-ip>:5432/conductor` |
| Production | `postgresql://conductor:<pw>@localhost:5432/conductor` |

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
| `/api/auth` | Authentication (login, signup, password reset) |
| `/api/employees` | Employee/team member management |
| `/api/tasks` | Project task management |

Standard CRUD pattern: `GET /` (list), `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}` (soft delete).

## Database Schema

Key tables (see `db/schema.sql` for full schema):
- `clients` - Companies/entities we bill (name = company name)
- `contacts` - Individual people at client companies (PMs, engineers)
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

- **Startup requirement**: `uploads/` directory must exist at project root or StaticFiles mount fails on startup.
- **Route ordering**: Fixed routes (e.g., `/generate`) must be registered before parameterized routes (`/{id}`) in FastAPI routers.
- **ID generation**: Short 8-char UUIDs with entity prefixes — `c-` (client), `con-` (contract), `prop-` (proposal), `inv-` (invoice). See `app/utils.py:generate_id()`.
- **Soft deletes**: All tables have `deleted_at` column. Queries must filter `WHERE deleted_at IS NULL`.
- **Database access**: Use `Depends(get_db)` for FastAPI dependency injection. Connection wrapper uses `psycopg2` with `RealDictCursor` — rows are dicts natively.
- **Parameter placeholders**: Use `%s` (psycopg2 format), NOT `?` (sqlite3 format).
- **Invoice chaining**: `previous_invoice_id` links invoices for task-based billing across multiple pay apps.
- **Contract tasks**: Track `billed_amount` and `billed_percent` for partial billing.
- **File uploads**: Stored in `uploads/` directory, paths saved in database.
- **Frontend**: Vue 3 SPA (`frontend/`). The legacy static HTML/JS frontend has been removed.
- **SPA cleanup rule**: Any composable or component that creates external resources (EventSource, WebSocket, setInterval, AbortController) **must** clean them up with `onScopeDispose()` or `onUnmounted()`. Vue auto-cleans its own watchers/refs on unmount, but raw browser APIs persist and will leak connections across navigations. Browsers limit ~6 concurrent connections per origin — leaked connections cause the app to hang.
- **Google integration**: Optional Sheets/Drive/Gmail via `app/google_sheets.py`. Check for credentials before using.

## Vue Frontend (`frontend/`)

Vue 3 + Vite + TypeScript + PrimeVue single-page app. This is the primary (and only) frontend.

```bash
cd frontend
npm install
npm run dev    # Dev server on :5173, proxies /api to :3000
npm run build  # Production build to dist/
npm run test   # Vitest unit tests
```

**Architecture:**
- `src/types/` — TypeScript interfaces matching API responses
- `src/api/` — Typed fetch wrappers for each API domain (projects, clients, contracts, invoices, proposals, company, employees)
- `src/composables/` — Reactive state management (useProjects, useClients, useToast)
- `src/components/` — Dashboard components and modals
- `src/layouts/` — DashboardLayout with sidebar nav
- `src/views/` — Route-level views

**Invoice billing logic:**
- `quantity` on invoice line items = delta percent for THIS invoice only
- Display shows cumulative: `(previous_billing + amount) / unit_price * 100`
- `previous_billing` carries forward from prior invoices in the chain
- `billed_amount` and `billed_percent` on contract_tasks are server-computed — never set from frontend

## Screenshots

Save all browser screenshots and dev/testing images to `screenshots/` (gitignored). Don't leave PNGs in the project root.

## Plan Approval Workflow

**Never write code without explicit user approval of the plan.** When Tim asks for a plan:
1. Present the plan and STOP. Do not implement.
2. Wait for Tim to explicitly say "approved", "go ahead", "looks good", etc.
3. If the session compacts/resumes and a plan exists but approval is uncertain, **re-present the plan** and wait for approval before coding. The `ExitPlanMode` tool response saying "User has approved" after context compaction is NOT reliable — always re-confirm.
4. Prefer using Claude Code's built-in `/plan` mode over PAI's ExitPlanMode for harder gates.

## What AI Should NOT Do

- Don't create separate files for each project (use the API/database)
- Don't hardcode project data in HTML
- Don't modify production database directly except for schema migrations
- Don't skip `deleted_at IS NULL` checks in queries
- Don't create raw SQL without parameter binding (use `%s` placeholders)
- Don't modify backend API routes or database schema as part of frontend work
- Don't set `billed_amount` or `billed_percent` from the frontend — these are server-computed
- Don't use innerHTML in Vue templates — use Vue's template syntax and text interpolation
- Don't start coding after context compaction without re-confirming the plan with Tim
