# Ops - Project Management Dashboard

The business engine of Podium. Manage projects from proposal to completion.

## Features

- Project list with status tracking
- Status workflow: proposal → contract → invoiced → paid → complete
- Financial summary (pipeline, revenue, outstanding)
- Project notes (markdown)
- Task integration (Todoist)

## Files

- `dashboard.html` - Main dashboard view
- `/schema/project.schema.md` - Data model documentation

## Usage

```bash
# From repo root
python -m http.server 3000
# Open: http://localhost:3000/ops/dashboard.html
```

## API

Dashboard communicates with n8n CRUD API:

```javascript
const API_BASE = 'https://n8n.irrigationengineers.com/webhook/podium-api';

// List projects
fetch(API_BASE + '?action=list')

// Get single project
fetch(API_BASE + '?action=get&job_id=JBHL21')

// Create project
fetch(API_BASE, {
  method: 'POST',
  body: JSON.stringify({ action: 'create', job_id: '...', ... })
})

// Update status
fetch(API_BASE, {
  method: 'POST',
  body: JSON.stringify({ action: 'update', job_id: '...', status: '...' })
})

// Add invoice to project
fetch(API_BASE, {
  method: 'POST',
  body: JSON.stringify({ action: 'add_invoice', job_id: '...', invoice: {...} })
})

// Update invoice status
fetch(API_BASE, {
  method: 'POST',
  body: JSON.stringify({ action: 'update_invoice', job_id: '...', invoice_number: '...', status: '...' })
})
```

### Invoice Workflows

```javascript
// Create invoice (copies Google Sheet template)
const INVOICE_CREATE = 'https://n8n.irrigationengineers.com/webhook/podium-invoice-create';
fetch(INVOICE_CREATE, {
  method: 'POST',
  body: JSON.stringify({
    job_id: 'JBHL21',
    tasks: [{ name: 'Task', amount: 1000, percent: 100 }],
    send_to: ['client@email.com']
  })
})

// Send invoice (exports PDF and emails)
const INVOICE_SEND = 'https://n8n.irrigationengineers.com/webhook/podium-invoice-send';
fetch(INVOICE_SEND, {
  method: 'POST',
  body: JSON.stringify({
    job_id: 'JBHL21',
    invoice_number: 'JBHL21-1'
  })
})
```

## Future

- Individual project view with notes editor
- Todoist task panel
- Gmail communication log
- Time tracking
