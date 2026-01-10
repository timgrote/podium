# Project Schema

Based on TIE project management patterns. Properties drive dashboard views and workflow automation.

## Core Properties

```yaml
# Identity
job_id: string          # Unique identifier (e.g., "2026-001", "JBHL21")
project_name: string    # Project title
client_name: string     # Client/company name
client_email: string    # Primary contact email

# Status Workflow
status: enum            # proposal | contract | invoiced | paid | complete
phase: enum             # Optional: prelim | design | production | delivered

# Financial
amount: number          # Contract amount
invoiced_amount: number # Amount invoiced to date
paid_amount: number     # Amount received

# Timeline
created_at: date        # Project creation
updated_at: date        # Last modification
due_date: date          # Target completion
completion_date: date   # Actual completion

# Notes (Markdown)
notes: markdown         # Free-form project notes, stored as markdown

# Tasks (Todoist Integration)
todoist_project_id: string  # Linked Todoist project
tasks: array            # Synced from Todoist
```

## Status Workflow

```
proposal → contract → invoiced → paid → complete
    ↓         ↓          ↓        ↓
  Draft    Signed    Sent bill  Got $   Done
```

## Example Project Object

```json
{
  "job_id": "2026-001",
  "project_name": "Gateway Residence",
  "client_name": "John Smith",
  "client_email": "john@smithlandscape.com",
  "status": "proposal",
  "amount": 2500,
  "invoiced_amount": 0,
  "paid_amount": 0,
  "created_at": "2026-01-09",
  "updated_at": "2026-01-09",
  "notes": "## Design Notes\n- 3 zones front yard\n- Drip for planters\n\n## Client Communication\n- 2026-01-09: Initial call, discussed scope",
  "todoist_project_id": null,
  "tasks": []
}
```

## Notes Field Structure

The `notes` field contains markdown with suggested sections:

```markdown
## Design Notes
Technical details, specifications, decisions

## Client Communication
Chronological log of interactions

## Updates
Project status changes, milestones

## Hours
Time tracking (if needed)
```

## Dashboard Computed Fields

These are calculated from raw data for display:

- `outstanding`: amount - paid_amount
- `unbilled`: amount - invoiced_amount
- `status_badge`: Color-coded status indicator
- `days_since_update`: Today - updated_at
