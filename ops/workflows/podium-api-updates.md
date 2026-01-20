# Podium API Updates

Add these actions to the existing `podium-api` workflow's Code node.

## Action: create

```javascript
case 'create': {
  // Check for duplicate job_id
  const existing = projects.find(p => p.job_id === body.job_id);
  if (existing) {
    return { error: 'Project with this job_id already exists' };
  }

  // Build project object
  const newProject = {
    job_id: body.job_id,
    project_name: body.project_name || '',
    client_name: body.client_name || '',
    client_email: body.client_email || '',
    status: body.status || 'proposal',
    tasks: body.tasks || [],
    invoices: [],
    created_at: body.created_at || new Date().toISOString().split('T')[0],
    updated_at: new Date().toISOString().split('T')[0]
  };

  // Add contract info if provided
  if (body.contract) {
    newProject.contract = body.contract;
  }

  // Compute total from tasks for legacy amount field
  if (newProject.tasks.length > 0) {
    newProject.amount = newProject.tasks.reduce((sum, t) => sum + Number(t.amount || 0), 0);
  }

  // Add to projects array
  projects.push(newProject);

  // Save projects back to static data
  $getWorkflowStaticData('global').projects = projects;

  return { success: true, project: newProject };
}
```

## Action: add_invoice

Add this case to the switch statement in the Code node:

```javascript
case 'add_invoice': {
  const project = projects.find(p => p.job_id === body.job_id);
  if (!project) {
    return { error: 'Project not found' };
  }

  // Initialize invoices array if needed
  if (!project.invoices) {
    project.invoices = [];
  }

  // Add the new invoice
  project.invoices.push(body.invoice);

  // Update task invoiced_percent based on invoice tasks
  if (body.invoice.tasks_invoiced && project.tasks) {
    body.invoice.tasks_invoiced.forEach(invTask => {
      const projectTask = project.tasks.find(t => t.name === invTask.name);
      if (projectTask) {
        // Add the invoiced percent (accumulate for multiple invoices)
        projectTask.invoiced_percent = Math.min(
          (projectTask.invoiced_percent || 0) + invTask.percent,
          100
        );
      }
    });
  }

  // Save projects back to static data
  $getWorkflowStaticData('global').projects = projects;

  return { success: true, invoice: body.invoice };
}
```

## Action: update_invoice

```javascript
case 'update_invoice': {
  const project = projects.find(p => p.job_id === body.job_id);
  if (!project || !project.invoices) {
    return { error: 'Project or invoices not found' };
  }

  const invoice = project.invoices.find(inv => inv.invoice_number === body.invoice_number);
  if (!invoice) {
    return { error: 'Invoice not found' };
  }

  // Update invoice fields
  if (body.status) invoice.status = body.status;
  if (body.sent_at) invoice.sent_at = body.sent_at;
  if (body.pdf_url) invoice.pdf_url = body.pdf_url;
  if (body.paid_at) {
    invoice.paid_at = body.paid_at;

    // If marking as paid, update task paid_percent
    if (body.status === 'paid' && invoice.tasks_invoiced && project.tasks) {
      invoice.tasks_invoiced.forEach(invTask => {
        const projectTask = project.tasks.find(t => t.name === invTask.name);
        if (projectTask) {
          projectTask.paid_percent = Math.min(
            (projectTask.paid_percent || 0) + invTask.percent,
            100
          );
        }
      });
    }
  }

  // Save projects back to static data
  $getWorkflowStaticData('global').projects = projects;

  return { success: true, invoice };
}
```

## Action: get (update existing)

Make sure the `get` action returns invoices:

```javascript
case 'get': {
  const project = projects.find(p => p.job_id === query.job_id);
  if (!project) {
    return { error: 'Project not found' };
  }
  return { project };  // This should include project.invoices
}
```

## Testing

After updating, test with:

```bash
# Create project
curl -X POST https://n8n.irrigationengineers.com/webhook/podium-api \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create",
    "job_id": "TEST-001",
    "project_name": "Test Project",
    "client_name": "Test Client",
    "client_email": "test@example.com",
    "status": "proposal",
    "tasks": [
      { "name": "Design", "amount": 1000, "invoiced_percent": 0, "paid_percent": 0 }
    ]
  }'

# Add invoice
curl -X POST https://n8n.irrigationengineers.com/webhook/podium-api \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_invoice",
    "job_id": "JBHL21",
    "invoice": {
      "invoice_number": "JBHL21-1",
      "created_at": "2026-01-10",
      "amount": 2000,
      "status": "draft",
      "sheet_url": "https://docs.google.com/...",
      "send_to": ["jim@birdsall.com"],
      "tasks_invoiced": [{"name": "Preliminary Design", "amount": 2000, "percent": 100}]
    }
  }'

# Update invoice status
curl -X POST https://n8n.irrigationengineers.com/webhook/podium-api \
  -H "Content-Type: application/json" \
  -d '{
    "action": "update_invoice",
    "job_id": "JBHL21",
    "invoice_number": "JBHL21-1",
    "status": "sent",
    "sent_at": "2026-01-10"
  }'
```
