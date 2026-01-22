# CLAUDE.md - Podium

## Project Overview

Podium is a multi-tenant SaaS platform for project-based service businesses. The initial vertical is irrigation design (connecting to Raindrop), but the architecture supports any service business.

## Architecture Layers

1. **Ops** (`/ops`) - The project management dashboard. This is the business engine.
2. **Flows** (`/flows`) - Client-facing automated workflows (proposal, contract, invoice, payment)
3. **Integrations** (`/integrations`) - External services (Todoist, Gmail)

## Tech Stack

- **Frontend**: Static HTML/CSS/JS served by Caddy
- **Backend**: n8n workflows at `n8n.irrigationengineers.com`
- **Storage**: SQLite at `/opt/n8n-docker-caddy/local_files/podium.db` (mounted as `/files/podium.db` in n8n)
- **Hosting**: DigitalOcean droplet at `pm.irrigationengineers.com`
- **Auth**: Google OAuth via OAuth2 Proxy (@irrigationengineers.com only)

## Key Files

- `/ops/dashboard.html` - Main project dashboard
- `/ops/schema/project.schema.md` - Project data model
- `/integrations/todoist.md` - Task integration plan
- `/integrations/gmail.md` - Email integration plan

## API Endpoints

All APIs are n8n webhooks:

```
GET  /webhook/podium-api?action=list    # List projects
POST /webhook/podium-api                 # CRUD operations
POST /webhook/podium-intake              # New project submission
```

## Development

```bash
python -m http.server 3000
# Open: http://localhost:3000/ops/dashboard.html
```

## Patterns from TIE

This project borrows patterns from the TIE Obsidian vault:
- Frontmatter-style properties for projects (see schema)
- Markdown notes field for project documentation
- Status workflow: proposal → contract → invoiced → paid → complete
- Task integration (Todoist instead of Obsidian tasks)

## Infrastructure Access

```bash
# SSH to droplet
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com

# Query database directly
ssh -i ~/.ssh/digitalocean_n8n root@n8n.irrigationengineers.com \
  "sqlite3 /opt/n8n-docker-caddy/local_files/podium.db 'SELECT * FROM projects'"

# n8n API helper (list workflows, etc.)
~/.claude/skills/N8n/Tools/n8n-api.sh list
```

## What AI Should Know

- n8n is the orchestration layer - it abstracts storage backends
- Data is stored in SQLite, accessed via n8n's `n8n-nodes-sqlite3` community node
- Projects have a `notes` field that stores markdown content
- Status changes trigger workflow automations
- The dashboard reads from and writes to the CRUD API

## What AI Should NOT Do

- Don't create separate files for each project (use the API/database)
- Don't hardcode project data in HTML
- Don't bypass n8n for data operations
