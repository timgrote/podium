const items = $input.all();
const context = $('Parse & Build Query').first().json;
const action = context.action;
const result_type = context.result_type;
const job_id = context.job_id;

if (result_type === 'error') {
  return [{ json: { error: items[0]?.json?.error || 'Unknown error' } }];
}

if (result_type === 'write') {
  return [{ json: { success: true, action, job_id } }];
}

const rows = items.map(item => item.json);

if (action === 'list') {
  const projects = rows.map(row => {
    const project = { ...row };
    project.contracts = JSON.parse(row.contracts_json || '[]');
    project.invoices = JSON.parse(row.invoices_json || '[]');
    delete project.contracts_json;
    delete project.invoices_json;
    return project;
  });
  return [{ json: { projects } }];
}

return [{ json: { success: true, data: rows } }];
