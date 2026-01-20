# Podium n8n Workflows

Workflow definitions for Podium's n8n backend.

## Setup

### Prerequisites

1. n8n instance at `n8n.irrigationengineers.com`
2. Google OAuth2 credentials with Sheets and Drive scopes
3. Invoice template at: `16QHE3DdF0AAQtLgXUZSx8c9T2q3dvTvKwjb90B5yGcI`

### Import Workflow

1. Open n8n at `https://n8n.irrigationengineers.com`
2. Go to Workflows → Import from File
3. Select `podium-invoice-create.json`
4. Update credential IDs:
   - Replace `GOOGLE_DRIVE_CREDENTIAL_ID` with your Google Drive credential ID
   - Replace `GOOGLE_SHEETS_CREDENTIAL_ID` with your Google Sheets credential ID
5. Save and activate the workflow

### Update podium-api

See `podium-api-updates.md` for code to add to the existing podium-api workflow.

## Workflows

| Workflow | Webhook Path | Purpose |
|----------|--------------|---------|
| podium-invoice-create | `/webhook/podium-invoice-create` | Copy template, populate, return sheet URL |
| podium-invoice-send | `/webhook/podium-invoice-send` | Export PDF, email to client |

## Invoice Template

**Google Sheet ID:** `16QHE3DdF0AAQtLgXUZSx8c9T2q3dvTvKwjb90B5yGcI`

### Cell Mapping

| Cell | Field |
|------|-------|
| B7 | Project Name |
| B8 | Project ID (Job ID) |
| B9 | Invoice Date |
| B10 | Invoice Number |
| B11 | Project Manager Email |
| E7 | Client Contact |
| A14:E23 | Task line items |

### Task Row Columns (A14:E23)

| Column | Content |
|--------|---------|
| A | Task name |
| B | Fee (total task amount) |
| C | Percent Complete |
| D | Previous Fee Billing |
| E | Current Fee Billing |

## Testing

```bash
# Create invoice
curl -X POST https://n8n.irrigationengineers.com/webhook/podium-invoice-create \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "JBHL21",
    "tasks": [
      { "name": "Preliminary Design", "amount": 2000, "percent": 100 }
    ],
    "send_to": ["jim@birdsall.com"]
  }'

# Expected response:
# {
#   "invoice_number": "JBHL21-1",
#   "sheet_url": "https://docs.google.com/spreadsheets/d/...",
#   "amount": 2000
# }
```

## Files

- `podium-invoice-create.json` - Importable n8n workflow
- `podium-invoice-create.md` - Detailed workflow documentation
- `podium-invoice-send.md` - Send workflow documentation
- `podium-api-updates.md` - Code to add to podium-api
