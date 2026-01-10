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

// Update status
fetch(API_BASE, {
  method: 'POST',
  body: JSON.stringify({ action: 'update', job_id: '...', status: '...' })
})
```

## Future

- Individual project view with notes editor
- Todoist task panel
- Gmail communication log
- Time tracking
