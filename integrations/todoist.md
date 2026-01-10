# Todoist Integration

## Overview

Sync project tasks between Podium and Todoist for task management.

## Integration Pattern

```
Podium Project ←→ Todoist Project
     └── tasks[] ←→ Todoist Tasks
```

## n8n Workflow Design

### Create Project → Create Todoist Project
When a new project is added to Podium:
1. Create Todoist project with same name
2. Store `todoist_project_id` in project record
3. Add default tasks based on project type

### Sync Tasks
Bidirectional sync via n8n scheduled workflow:
- Todoist → Podium: New tasks, completions, updates
- Podium → Podium: Display task list in project view

## Todoist API

```
Base: https://api.todoist.com/rest/v2
Auth: Bearer token

POST /projects - Create project
GET /tasks?project_id={id} - Get project tasks
POST /tasks - Create task
POST /tasks/{id}/close - Complete task
```

## Default Task Templates

### Proposal Status
- [ ] Send proposal to client
- [ ] Follow up if no response (3 days)

### Contract Status
- [ ] Send contract for signature
- [ ] Receive signed contract
- [ ] Schedule kickoff

### Invoiced Status
- [ ] Send invoice
- [ ] Follow up on payment (net 30)

## n8n Nodes Required

1. **Todoist node** (built-in) - API operations
2. **Webhook** - Receive Todoist webhooks (optional)
3. **Schedule** - Periodic sync

## Implementation Steps

1. Create Todoist API credential in n8n
2. Build "Create Todoist Project" workflow
3. Build "Sync Tasks" scheduled workflow
4. Update dashboard to display tasks
5. Add task completion UI
