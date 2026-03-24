# Podium Gmail Add-on

Create Podium tasks directly from your Gmail inbox.

## Architecture

```
Gmail Add-on → n8n webhook (public) → Podium API (internal/Tailscale)
```

The add-on doesn't hit Podium directly (it's Tailscale-only). Instead, it calls
n8n webhooks which relay requests to the Podium API internally.

## Setup

### 1. Create an API key in Podium

Go to Podium settings and create a new API key. Copy the `pod_...` key — you'll
only see it once.

### 2. Set up n8n webhooks

Create two n8n workflows:

**Workflow 1: Create Task**
- Trigger: Webhook (POST `/webhook/podium/create-task`)
- Step 1: Extract `api_key`, `project_id`, `title`, `description`, `due_date` from body
- Step 2: HTTP Request to `http://100.105.238.37/api/projects/{{project_id}}/tasks`
  - Method: POST
  - Headers: `Authorization: Bearer {{api_key}}`
  - Body: `{ title, description, due_date, status: "todo" }`
- Step 3: Respond to Webhook with result

**Workflow 2: List Projects**
- Trigger: Webhook (POST `/webhook/podium/list-projects`)
- Step 1: Extract `api_key` from body
- Step 2: HTTP Request to `http://100.105.238.37/api/projects`
  - Method: GET
  - Headers: `Authorization: Bearer {{api_key}}`
- Step 3: Respond to Webhook with project list

### 3. Deploy the Gmail Add-on

1. Go to [script.google.com](https://script.google.com) and create a new project
2. Replace `Code.gs` contents with the code from this directory
3. Enable the manifest: View > Show manifest file, replace with `appsscript.json`
4. Set Script Properties (Project Settings > Script Properties):
   - `N8N_WEBHOOK_URL`: `https://n8n.irrigationengineers.com/webhook/podium/create-task`
   - `N8N_PROJECTS_WEBHOOK_URL`: `https://n8n.irrigationengineers.com/webhook/podium/list-projects`
   - `PODIUM_API_KEY`: your `pod_...` key from step 1
5. Deploy > Test deployments > Install (for your account only)

### 4. Test

Open any email in Gmail. The Podium sidebar should appear on the right.
Select a project, edit the title/description, and click "Create Task".
