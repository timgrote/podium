# Podium

Multi-tenant SaaS platform for service businesses. Start with irrigation design, expand to any project-based business.

## Architecture

```
/podium
├── index.html              # Landing page / marketing
├── /ops                    # Project management dashboard
│   ├── dashboard.html      # Main dashboard view
│   └── /schema             # Data models
├── /flows                  # Automated workflow pages
│   ├── proposal.html       # Client views proposal
│   ├── contract.html       # Client signs contract
│   ├── invoice.html        # Client views invoice
│   └── payment.html        # Payment confirmation
└── /integrations           # External service integrations
    ├── todoist.md          # Task management
    └── gmail.md            # Email integration
```

## Layers

| Layer | Purpose |
|-------|---------|
| **Podium** | Platform infrastructure, multi-tenancy |
| **Ops** | Project management dashboard (the business engine) |
| **Flows** | Automated client-facing workflows |
| **Integrations** | Todoist, Gmail, future services |

## Backend

- **n8n** at `n8n.irrigationengineers.com` handles all API operations
- **SQLite** database at `/files/podium.db` (on droplet: `/opt/n8n-docker-caddy/local_files/podium.db`)
- See `db/README.md` for database access and schema

## API Endpoints

```
# CRUD API
GET  /webhook/podium-api?action=list     # List all projects
POST /webhook/podium-api                  # Add/update projects
     body: { action: "add", ...project }
     body: { action: "update", job_id: "...", status: "..." }

# Intake
POST /webhook/podium-intake              # New project submission
```

## Development

```bash
# Local server
python -m http.server 3000

# Then open
http://localhost:3000/ops/dashboard.html
```

## Project Schema

See `/ops/schema/project.schema.md` for the full data model.

Key fields:
- `job_id`, `project_name`, `client_name`, `client_email`
- `status`: proposal → contract → invoiced → paid → complete
- `amount`, `invoiced_amount`, `paid_amount`
- `notes`: Markdown field for project documentation
- `tasks`: Synced with Todoist

## Roadmap

1. **Now**: Dashboard with status tracking
2. **Next**: Todoist integration for task management
3. **Later**: Gmail integration for client communication
4. **Future**: Multi-tenant accounts, Raindrop integration
