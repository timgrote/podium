# Gmail Integration

## Overview

Connect Gmail for client communication tracking and automated emails.

## Features

### Phase 1: Email Logging
- Log sent emails to project notes
- Associate incoming emails with projects by client_email

### Phase 2: Automated Sends
- Send proposal emails from Podium
- Send invoice reminders
- Send status updates

### Phase 3: Thread Tracking
- Link email threads to projects
- Display communication history in project view

## n8n Workflow Design

### Log Outgoing Email
```
Dashboard "Send Email" → n8n Webhook → Gmail Send → Update Project Notes
```

### Associate Incoming
```
Gmail Trigger (new email) → Match client_email → Append to project notes
```

## Gmail API via n8n

n8n has built-in Gmail node:
- Send email
- Get messages
- Search messages
- Watch for new messages

## Project Notes Format

When emails are logged:

```markdown
## Client Communication

### 2026-01-09 - Email Sent
**Subject:** Your irrigation proposal is ready
**To:** john@smithlandscape.com

Sent proposal PDF attached...

---

### 2026-01-08 - Email Received
**Subject:** RE: Project scope question
**From:** john@smithlandscape.com

Thanks for the clarification on zones...
```

## MCP Integration

Already have n8n-email MCP server configured:
- `get_recent_emails` - Fetch inbox
- `search_emails` - Query by sender/subject
- `send_email` - Send from connected account

## Implementation Steps

1. Use existing n8n Gmail credential
2. Build "Log Email to Project" workflow
3. Add email compose UI to project view
4. Build incoming email matcher workflow
5. Display communication log in dashboard
