# Podium Invoice Create Workflow

**Webhook URL:** `https://n8n.irrigationengineers.com/webhook/podium-invoice-create`

## Overview

Creates a new invoice by copying a Google Sheets template, populating it with project data, and storing the invoice record.

## Input

```json
{
  "job_id": "JBHL21",
  "tasks": [
    { "name": "Preliminary Design", "amount": 2000, "percent": 100 }
  ],
  "send_to": ["jim@birdsall.com", "accounting@birdsall.com"]
}
```

## Output

```json
{
  "invoice_number": "JBHL21-1",
  "sheet_url": "https://docs.google.com/spreadsheets/d/...",
  "amount": 2000
}
```

## Workflow Nodes

### 1. Webhook (Trigger)
- **Method:** POST
- **Path:** podium-invoice-create
- **Response Mode:** Last Node

### 2. Get Project Data (HTTP Request)
- **URL:** `https://n8n.irrigationengineers.com/webhook/podium-api?action=get&job_id={{ $json.job_id }}`
- **Method:** GET

### 3. Get Company Data (HTTP Request)
- **URL:** `https://n8n.irrigationengineers.com/webhook/podium-company`
- **Method:** GET

### 4. Calculate Invoice Number (Code Node)
```javascript
const project = $('Get Project Data').first().json.project;
const jobId = $('Webhook').first().json.body.job_id;

// Get existing invoices or empty array
const invoices = project.invoices || [];

// Find highest invoice number for this project
let maxNum = 0;
invoices.forEach(inv => {
  const match = inv.invoice_number.match(/-(\d+)$/);
  if (match) {
    maxNum = Math.max(maxNum, parseInt(match[1]));
  }
});

const invoiceNumber = `${jobId}-${maxNum + 1}`;

return {
  invoice_number: invoiceNumber,
  next_num: maxNum + 1
};
```

### 5. Copy Invoice Template (Google Sheets)
- **Operation:** Copy Sheet
- **Source Spreadsheet ID:** `{{ $env.INVOICE_TEMPLATE_ID }}`
- **Destination:** Create new spreadsheet named `{{ invoice_number }}`

**Alternative using Google Drive node:**
- **Operation:** Copy
- **File ID:** `{{ $env.INVOICE_TEMPLATE_ID }}`
- **Name:** `{{ invoice_number }}`
- **Parent Folder:** Get or create `/Projects/{{ client_name }}/{{ project_name }}/Invoices/`

### 6. Get/Create Project Folder (Google Drive - Code Node)
```javascript
const project = $('Get Project Data').first().json.project;
const clientName = project.client_name.replace(/[\/\\:*?"<>|]/g, '_');
const projectName = project.project_name.replace(/[\/\\:*?"<>|]/g, '_');

return {
  folderPath: `Projects/${clientName}/${projectName}/Invoices`,
  clientName,
  projectName
};
```

### 7. Populate Invoice Sheet (Google Sheets - Update)
- **Spreadsheet:** `{{ new_spreadsheet_id }}`
- **Range:** Various cells

**Values to set:**
| Cell | Value |
|------|-------|
| B2 | `{{ company.company_name }}` |
| B3 | `{{ company.company_address }}` |
| B4 | `{{ company.company_email }}` |
| B5 | `{{ company.company_phone }}` |
| E2 | `{{ invoice_number }}` |
| E3 | `{{ today's date }}` |
| B8 | `{{ project.client_name }}` |
| B9 | `{{ project.client_email }}` |
| A12:C... | Task line items (name, description, amount) |
| C20 | `{{ total_amount }}` |

### 8. Calculate Invoice Amount (Code Node)
```javascript
const tasks = $('Webhook').first().json.body.tasks;

let total = 0;
const lineItems = tasks.map(task => {
  const amount = (task.amount * task.percent) / 100;
  total += amount;
  return {
    name: task.name,
    percent: task.percent,
    amount: amount
  };
});

return {
  line_items: lineItems,
  total_amount: total
};
```

### 9. Store Invoice in Project (HTTP Request)
- **URL:** `https://n8n.irrigationengineers.com/webhook/podium-api`
- **Method:** POST
- **Body:**
```json
{
  "action": "add_invoice",
  "job_id": "{{ job_id }}",
  "invoice": {
    "invoice_number": "{{ invoice_number }}",
    "created_at": "{{ $today.format('YYYY-MM-DD') }}",
    "amount": "{{ total_amount }}",
    "status": "draft",
    "sheet_url": "{{ sheet_url }}",
    "send_to": "{{ send_to }}",
    "tasks_invoiced": "{{ line_items }}"
  }
}
```

### 10. Return Response (Respond to Webhook)
```json
{
  "invoice_number": "{{ invoice_number }}",
  "sheet_url": "{{ sheet_url }}",
  "amount": "{{ total_amount }}"
}
```

## Required Environment Variables

| Variable | Description |
|----------|-------------|
| `INVOICE_TEMPLATE_ID` | Google Sheets ID of the invoice template |
| `PROJECTS_FOLDER_ID` | Google Drive folder ID for `/Projects/` |

## Required Credentials

- Google OAuth2 (Sheets + Drive scopes)

## API Update Required

The `podium-api` workflow needs a new action: `add_invoice`

```javascript
// In podium-api workflow, add this case:
case 'add_invoice':
  const project = projects.find(p => p.job_id === body.job_id);
  if (project) {
    if (!project.invoices) project.invoices = [];
    project.invoices.push(body.invoice);
    // Update task invoiced_percent based on invoice
    // ... update logic
  }
  break;
```
