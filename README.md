# Podium

Multi-tenant SaaS platform for service businesses. Start with irrigation design, expand to any project-based business.

## Architecture

```
/podium
├── app/                    # FastAPI backend
│   ├── main.py             # App entry point, mounts routers + static files
│   ├── config.py           # Settings (db path, Google API keys, etc.)
│   ├── database.py         # SQLite connection helper
│   └── routers/            # API route modules
│       ├── clients.py
│       ├── company.py
│       ├── contracts.py
│       ├── flows.py
│       ├── invoices.py
│       ├── projects.py
│       └── proposals.py
├── db/
│   ├── schema.sql          # Full database schema
│   ├── init_db.py          # Initialize/seed local database
│   └── podium.db           # SQLite database (created by init_db.py)
├── ops/                    # Project management dashboard (HTML/JS)
│   ├── dashboard.html
│   ├── project.html
│   ├── clients.html
│   └── settings.html
├── flows/                  # Client-facing pages (HTML/JS)
│   ├── proposal.html
│   ├── contract.html
│   ├── invoice.html
│   └── payment.html
└── index.html              # Landing page
```

## Quick Start

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize the database
cd db && python3 init_db.py && cd ..

# 4. Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Open in browser
http://localhost:8000/ops/dashboard.html
```

## Backend

- **FastAPI** serves both the API and static files
- **SQLite** database at `db/podium.db` (configurable via `PODIUM_DB_PATH` env var)
- All frontend pages call `/api/...` endpoints — no external dependencies required

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/api/clients` | Client CRUD |
| `/api/company` | Company settings (GET / PUT) |
| `/api/projects` | Project CRUD + detail views |
| `/api/contracts` | Contract management + tasks |
| `/api/proposals` | Proposal CRUD |
| `/api/invoices` | Invoice management |
| `/api/flows` | Public flow data for client-facing pages |

## Configuration

Settings are loaded from environment variables with the `PODIUM_` prefix:

| Variable | Default | Purpose |
|----------|---------|---------|
| `PODIUM_DB_PATH` | `db/podium.db` | Path to SQLite database |
| `PODIUM_HOST` | `0.0.0.0` | Server bind address |
| `PODIUM_PORT` | `8000` | Server port |
| `PODIUM_GOOGLE_SERVICE_ACCOUNT_JSON` | | Base64-encoded Google credentials |
| `PODIUM_GOOGLE_SERVICE_ACCOUNT_PATH` | | Path to Google credentials JSON file |
| `PODIUM_INVOICE_TEMPLATE_ID` | *(set)* | Google Sheets template for invoices |
| `PODIUM_INVOICE_DRIVE_FOLDER_ID` | | Google Drive folder for generated invoices |

## Database

Key tables (see `db/schema.sql` for full schema):
- `clients` - Companies/people we bill
- `contacts` - Individual people (PMs, engineers)
- `projects` - Jobs with status workflow
- `contracts` - Signed agreements
- `contract_tasks` - Tasks/phases on contracts with billing tracking
- `invoices` - Both task-based and list-based invoices
- `invoice_line_items` - Line items on invoices
- `proposals`, `proposal_tasks`
- `company_settings` - Company name, logo, colors, etc.

Status workflow: `proposal → contract → invoiced → paid → complete`

## Deployment

Auto-deploys on push to `master` via GitHub Actions.

```bash
# Manual deploy
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com \
  "cd /opt/n8n-docker-caddy/podium && git pull"
```
