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

# Contract (optional)
contract:
  signed_date: date     # When contract was signed
  document_url: string  # Link to signed contract document

# Billable Tasks (line items)
tasks:
  - name: string        # Task description (e.g., "Preliminary Design")
    amount: number      # Dollar amount for this task
    invoiced_percent: number  # 0-100, percentage invoiced
    paid_percent: number      # 0-100, percentage paid

# Invoices (array of invoice records)
invoices:
  - invoice_number: string    # Project-based numbering (e.g., "JBHL21-1")
    created_at: date          # When invoice was created
    amount: number            # Total invoice amount
    status: enum              # draft | sent | paid
    sheet_url: string         # Google Sheets URL
    pdf_url: string           # PDF export URL (after sending)
    send_to: array[string]    # Email addresses
    sent_at: date             # When invoice was sent
    paid_at: date             # When payment received
    tasks_invoiced:           # Tasks included in this invoice
      - name: string
        amount: number
        percent: number       # Percentage of task invoiced (0-100)

# Legacy Financial (for backwards compatibility)
amount: number          # Single contract amount (deprecated, use tasks)

# Computed (display only, calculated from tasks)
# total_amount: sum of task amounts
# total_invoiced: sum of (task.amount * task.invoiced_percent / 100)
# total_paid: sum of (task.amount * task.paid_percent / 100)

# Timeline
created_at: date        # Project creation
updated_at: date        # Last modification
due_date: date          # Target completion
completion_date: date   # Actual completion

# Notes (Markdown)
notes: markdown         # Free-form project notes, stored as markdown

# Todoist Integration
todoist_project_id: string  # Linked Todoist project
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
  "job_id": "JBHL21",
  "project_name": "Heron Lakes 21",
  "client_name": "Jim Birdsall",
  "client_email": "jim@example.com",
  "status": "contract",
  "tasks": [
    { "name": "Preliminary Design", "amount": 2000, "invoiced_percent": 100, "paid_percent": 100 },
    { "name": "Construction Documents", "amount": 2200, "invoiced_percent": 50, "paid_percent": 0 },
    { "name": "Changes", "amount": 400, "invoiced_percent": 0, "paid_percent": 0 }
  ],
  "contract": {
    "signed_date": "2026-01-05"
  },
  "invoices": [
    {
      "invoice_number": "JBHL21-1",
      "created_at": "2026-01-10",
      "amount": 2000,
      "status": "sent",
      "sheet_url": "https://docs.google.com/spreadsheets/d/abc123",
      "pdf_url": "https://drive.google.com/file/d/xyz789",
      "send_to": ["jim@example.com", "accounting@example.com"],
      "sent_at": "2026-01-10",
      "tasks_invoiced": [
        { "name": "Preliminary Design", "amount": 2000, "percent": 100 }
      ]
    }
  ],
  "created_at": "2026-01-03",
  "updated_at": "2026-01-09",
  "notes": "## Design Notes\n- Golf course irrigation\n- 21 holes\n\n## Client Communication\n- 2026-01-03: Initial meeting"
}
```

**Computed values for this project:**
- Total: $4,600 (sum of task amounts)
- Invoiced: $3,100 (2000×100% + 2200×50% + 400×0%)
- Paid: $2,000 (2000×100% + 2200×0% + 400×0%)

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
