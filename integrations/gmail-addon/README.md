# Podium Gmail Add-on

Create Podium tasks directly from your Gmail inbox. Open an email, pick a project, and create a task — the email subject and body are pre-filled.

## Architecture

```
Gmail Add-on (Google servers)
    ↓ HTTPS POST (JSON)
n8n webhook (n8n.irrigationengineers.com, public)
    ↓ HTTP (internal, Tailscale)
Podium API (100.105.238.37, Tailscale-only)
    ↓
PostgreSQL
```

The Gmail Add-on runs on Google's infrastructure, which can't reach Podium directly (Tailscale-only). n8n acts as a relay — it's both public-facing and on the Tailnet.

## Prerequisites

- Podium deployed and running (API at `http://100.105.238.37`)
- n8n running at `n8n.irrigationengineers.com`
- A Google Workspace account (for Apps Script deployment)

## Installation

### Step 1: Create a Podium API Key

1. Log in to Podium
2. Go to your **Profile** (click your avatar in the sidebar)
3. Scroll down to **API Keys**
4. Click **New API Key**, enter a name like "Gmail Add-on"
5. **Copy the `pod_...` key immediately** — it's only shown once

### Step 2: Create n8n Workflows

Log in to n8n at `https://n8n.irrigationengineers.com` and create two workflows:

#### Workflow 1: "Podium — Create Task"

**Node 1: Webhook**
- Type: Webhook
- HTTP Method: POST
- Path: `podium/create-task`
- Response Mode: "Using 'Respond to Webhook' Node"

**Node 2: HTTP Request**
- Method: POST
- URL: `http://100.105.238.37/api/projects/{{ $json.body.project_id }}/tasks`
- Authentication: None (we pass it as a header)
- Send Headers: Yes
  - Header Name: `Authorization`
  - Header Value: `Bearer {{ $json.body.api_key }}`
- Send Body: Yes (JSON)
  ```json
  {
    "title": "{{ $json.body.title }}",
    "description": "{{ $json.body.description }}",
    "due_date": "{{ $json.body.due_date }}",
    "status": "todo"
  }
  ```

**Node 3: Respond to Webhook**
- Respond With: All Incoming Items (passes the Podium API response back to the add-on)

Wire: Webhook → HTTP Request → Respond to Webhook

**Activate the workflow.**

#### Workflow 2: "Podium — List Projects"

**Node 1: Webhook**
- Type: Webhook
- HTTP Method: POST
- Path: `podium/list-projects`
- Response Mode: "Using 'Respond to Webhook' Node"

**Node 2: HTTP Request**
- Method: GET
- URL: `http://100.105.238.37/api/projects`
- Authentication: None
- Send Headers: Yes
  - Header Name: `Authorization`
  - Header Value: `Bearer {{ $json.body.api_key }}`

**Node 3: Respond to Webhook**
- Respond With: All Incoming Items

Wire: Webhook → HTTP Request → Respond to Webhook

**Activate the workflow.**

#### Test the webhooks

From any terminal on the Tailnet:

```bash
# Test list projects
curl -s -X POST https://n8n.irrigationengineers.com/webhook/podium/list-projects \
  -H "Content-Type: application/json" \
  -d '{"api_key": "pod_YOUR_KEY_HERE"}' | head -c 200

# Test create task (use a real project ID from the list above)
curl -s -X POST https://n8n.irrigationengineers.com/webhook/podium/create-task \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "pod_YOUR_KEY_HERE",
    "project_id": "YOUR_PROJECT_ID",
    "title": "Test task from n8n",
    "description": "Testing the webhook relay",
    "status": "todo"
  }'
```

Both should return JSON responses. If the first returns a project list and the second returns a task object, the relay is working.

### Step 3: Deploy the Gmail Add-on

1. Go to [script.google.com](https://script.google.com)
2. Click **New Project**
3. Name it "Podium Task Creator"

**Add the code:**

4. In the editor, replace the contents of `Code.gs` with the code from [`Code.gs`](./Code.gs) in this directory
5. Click **Project Settings** (gear icon on the left)
6. Check **Show "appsscript.json" manifest file in editor**
7. Go back to the Editor, click `appsscript.json`, and replace its contents with [`appsscript.json`](./appsscript.json) from this directory

**Set Script Properties:**

8. Go to **Project Settings** again
9. Under **Script Properties**, add these three:

| Property | Value |
|----------|-------|
| `N8N_WEBHOOK_URL` | `https://n8n.irrigationengineers.com/webhook/podium/create-task` |
| `N8N_PROJECTS_WEBHOOK_URL` | `https://n8n.irrigationengineers.com/webhook/podium/list-projects` |
| `PODIUM_API_KEY` | `pod_...` (the key from Step 1) |

**Deploy for testing:**

10. Click **Deploy** > **Test deployments**
11. Under **Application type**, select **Gmail Add-on**
12. Click **Install**
13. Open Gmail — the add-on sidebar should appear when you open any email

### Step 4: Verify End-to-End

1. Open any email in Gmail
2. The "Podium Task Creator" sidebar should appear on the right
3. The **Project** dropdown should be populated with your active projects
4. The **Title** is pre-filled from the email subject
5. The **Description** is pre-filled from the email body (first 500 chars)
6. Optionally set a **Due Date**
7. Click **Create Task**
8. You should see a "Task created in Podium!" notification
9. Verify the task appears in Podium under the selected project

## Troubleshooting

**Sidebar doesn't appear:**
- Check that the add-on is installed: Gmail Settings > Add-ons
- Try reloading Gmail
- Check the Apps Script execution log for errors

**Project dropdown is empty:**
- Verify `N8N_PROJECTS_WEBHOOK_URL` is correct in Script Properties
- Test the n8n webhook directly with curl (see Step 2)
- Check n8n workflow execution history for errors

**"Failed to create task" error:**
- Check the Apps Script execution log (View > Executions in script.google.com)
- Check n8n workflow execution history
- Verify the API key is valid (test with curl)
- Ensure the Podium server is running

**n8n webhook returns error:**
- Check that both n8n workflows are **activated** (toggle in top-right)
- Verify Podium is reachable from n8n: `curl http://100.105.238.37/api/projects` from the n8n server
- Check n8n execution logs for HTTP errors

## Publishing (Optional)

The test deployment is private to your Google account. To share with other TIE team members:

1. Go to **Deploy** > **New deployment**
2. Select type: **Add-on**
3. Fill in the description
4. Click **Deploy**
5. Share the deployment link with team members

For wider distribution, you'd publish to the Google Workspace Marketplace, but for internal TIE use, sharing the deployment is sufficient.
