const items = $input.all();
const context = $('Parse & Build Query').first().json;
const action = context.action;
const result_type = context.result_type;
const job_id = context.job_id;
const debug = context.debug || {};

// Check for errors from parse stage
if (result_type === 'error') {
  return [{ json: {
    success: false,
    error: context.error || 'Unknown error in query building',
    debug
  } }];
}

// Check for SQL execution errors
if (items.length > 0 && items[0].json && items[0].json.error) {
  return [{ json: {
    success: false,
    error: `SQL Error: ${items[0].json.error}`,
    sql: context.sql,
    debug
  } }];
}

if (result_type === 'write') {
  return [{ json: { success: true, action, job_id } }];
}

const rows = items.map(item => item.json);

if (action === 'list') {
  const projects = rows.map(row => {
    const project = { ...row };
    try {
      project.contracts = JSON.parse(row.contracts_json || '[]');
      project.invoices = JSON.parse(row.invoices_json || '[]');
    } catch (e) {
      project.contracts = [];
      project.invoices = [];
      project._parse_error = e.message;
    }
    delete project.contracts_json;
    delete project.invoices_json;
    return project;
  });
  return [{ json: { projects } }];
}

return [{ json: { success: true, data: rows } }];
