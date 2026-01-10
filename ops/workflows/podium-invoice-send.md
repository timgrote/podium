# Podium Invoice Send Workflow

**Webhook URL:** `https://n8n.irrigationengineers.com/webhook/podium-invoice-send`

## Overview

Exports a Google Sheet invoice to PDF and emails it to the client. Updates invoice status and logs to tracking spreadsheet.

## Input

```json
{
  "job_id": "JBHL21",
  "invoice_number": "JBHL21-1"
}
```

## Output

```json
{
  "success": true,
  "sent_to": ["jim@birdsall.com", "accounting@birdsall.com"],
  "pdf_url": "https://drive.google.com/..."
}
```

## Workflow Nodes

### 1. Webhook (Trigger)
- **Method:** POST
- **Path:** podium-invoice-send
- **Response Mode:** Last Node

### 2. Get Project Data (HTTP Request)
- **URL:** `https://n8n.irrigationengineers.com/webhook/podium-api?action=get&job_id={{ $json.job_id }}`
- **Method:** GET

### 3. Find Invoice (Code Node)
```javascript
const project = $('Get Project Data').first().json.project;
const invoiceNumber = $('Webhook').first().json.body.invoice_number;

const invoice = project.invoices?.find(inv => inv.invoice_number === invoiceNumber);

if (!invoice) {
  throw new Error(`Invoice ${invoiceNumber} not found`);
}

return {
  invoice,
  project,
  sheet_id: invoice.sheet_url.match(/\/d\/([^\/]+)/)?.[1]
};
```

### 4. Get Company Data (HTTP Request)
- **URL:** `https://n8n.irrigationengineers.com/webhook/podium-company`
- **Method:** GET

### 5. Export Sheet as PDF (Google Drive)
- **Operation:** Export
- **File ID:** `{{ sheet_id }}`
- **MIME Type:** `application/pdf`

**Alternative using HTTP Request:**
```
GET https://docs.google.com/spreadsheets/d/{{ sheet_id }}/export?format=pdf&portrait=true&fitw=true
```

### 6. Upload PDF to Drive (Google Drive)
- **Operation:** Upload
- **File Name:** `{{ invoice_number }}.pdf`
- **Parent Folder:** Same folder as the sheet
- **Binary Data:** PDF from previous step

### 7. Send Email with PDF (Gmail or SMTP)
- **To:** `{{ invoice.send_to.join(', ') }}`
- **Subject:** `Invoice {{ invoice_number }} from {{ company.company_name }}`
- **Body:**
```
Dear {{ project.client_name }},

Please find attached invoice {{ invoice_number }} for {{ project.project_name }}.

Invoice Amount: ${{ invoice.amount.toLocaleString() }}

If you have any questions, please don't hesitate to contact us.

Best regards,
{{ company.company_name }}
{{ company.company_email }}
{{ company.company_phone }}
```
- **Attachments:** PDF from step 5

### 8. Log to Invoice Tracking Sheet (Google Sheets)
- **Spreadsheet ID:** `{{ $env.INVOICE_TRACKING_SHEET_ID }}`
- **Sheet:** `Invoices`
- **Operation:** Append
- **Values:**
  | Column | Value |
  |--------|-------|
  | A | `{{ invoice_number }}` |
  | B | `{{ project.job_id }}` |
  | C | `{{ project.project_name }}` |
  | D | `{{ project.client_name }}` |
  | E | `{{ invoice.amount }}` |
  | F | `sent` |
  | G | `{{ invoice.created_at }}` |
  | H | `{{ $today.format('YYYY-MM-DD') }}` |
  | I | `{{ invoice.sheet_url }}` |
  | J | `{{ pdf_url }}` |

### 9. Update Invoice Status (HTTP Request)
- **URL:** `https://n8n.irrigationengineers.com/webhook/podium-api`
- **Method:** POST
- **Body:**
```json
{
  "action": "update_invoice",
  "job_id": "{{ job_id }}",
  "invoice_number": "{{ invoice_number }}",
  "status": "sent",
  "sent_at": "{{ $today.format('YYYY-MM-DD') }}",
  "pdf_url": "{{ pdf_url }}"
}
```

### 10. Update Task Invoiced Percentages (Code Node)
```javascript
// Calculate new invoiced_percent for each task based on all sent invoices
const project = $('Get Project Data').first().json.project;

const updatedTasks = project.tasks.map(task => {
  let totalInvoicedPercent = 0;

  project.invoices?.forEach(inv => {
    if (inv.status === 'sent' || inv.status === 'paid') {
      const invoicedTask = inv.tasks_invoiced?.find(t => t.name === task.name);
      if (invoicedTask) {
        totalInvoicedPercent += invoicedTask.percent;
      }
    }
  });

  return {
    ...task,
    invoiced_percent: Math.min(totalInvoicedPercent, 100)
  };
});

return { updated_tasks: updatedTasks };
```

### 11. Save Updated Tasks (HTTP Request)
- **URL:** `https://n8n.irrigationengineers.com/webhook/podium-api`
- **Method:** POST
- **Body:**
```json
{
  "action": "update",
  "job_id": "{{ job_id }}",
  "tasks": "{{ updated_tasks }}"
}
```

### 12. Return Response (Respond to Webhook)
```json
{
  "success": true,
  "sent_to": "{{ invoice.send_to }}",
  "pdf_url": "{{ pdf_url }}"
}
```

## Required Environment Variables

| Variable | Description |
|----------|-------------|
| `INVOICE_TRACKING_SHEET_ID` | Google Sheets ID for invoice tracking |

## Required Credentials

- Google OAuth2 (Sheets + Drive + Gmail scopes)
- Or SMTP credentials for email sending

## Invoice Tracking Spreadsheet Structure

| Invoice # | Job ID | Project | Client | Amount | Status | Created | Sent | Sheet Link | PDF Link |
|-----------|--------|---------|--------|--------|--------|---------|------|------------|----------|
| JBHL21-1 | JBHL21 | Heron Lakes 21 | Jim Birdsall | $2,000 | Sent | 2026-01-10 | 2026-01-10 | [Link] | [Link] |

## API Updates Required

The `podium-api` workflow needs a new action: `update_invoice`

```javascript
case 'update_invoice':
  const project = projects.find(p => p.job_id === body.job_id);
  if (project && project.invoices) {
    const invoice = project.invoices.find(inv => inv.invoice_number === body.invoice_number);
    if (invoice) {
      if (body.status) invoice.status = body.status;
      if (body.sent_at) invoice.sent_at = body.sent_at;
      if (body.pdf_url) invoice.pdf_url = body.pdf_url;
    }
  }
  break;
```
