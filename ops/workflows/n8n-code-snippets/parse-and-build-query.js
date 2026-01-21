// Unified API handler - parses input and builds SQL
const input = $input.first().json;
const query = input.query || {};
const body = typeof input.body === 'string' ? JSON.parse(input.body) : (input.body || {});

// Determine action
const action = query.action || body.action || 'list';
const job_id = query.job_id || body.job_id;

// Helper to escape SQL strings
const esc = (val) => val ? String(val).replace(/'/g, "''") : '';

// Build the SQL query based on action
let sql = '';
let query_type = 'select';
let result_type = 'rows';

switch(action) {
  case 'list':
    sql = `SELECT
      p.id as job_id, p.name as project_name, p.status, p.data_path, p.notes,
      p.current_invoice_id, p.created_at, p.updated_at,
      c.id as client_id, c.name as client_name, c.email as client_email,
      c.company as client_company, c.phone as client_phone,
      COALESCE(inv_totals.total_invoiced, 0) as total_invoiced,
      COALESCE(inv_totals.total_paid, 0) as total_paid,
      COALESCE((SELECT json_group_array(json_object(
        'id', ct.id, 'total_amount', ct.total_amount, 'signed_at', ct.signed_at,
        'file_path', ct.file_path, 'created_at', ct.created_at
      )) FROM contracts ct WHERE ct.project_id = p.id AND ct.deleted_at IS NULL), '[]') as contracts_json,
      COALESCE((SELECT json_group_array(json_object(
        'id', inv.id, 'invoice_number', inv.invoice_number, 'total_due', inv.total_due,
        'sent_status', inv.sent_status, 'paid_status', inv.paid_status,
        'data_path', inv.data_path, 'previous_invoice_id', inv.previous_invoice_id,
        'sent_at', inv.sent_at, 'paid_at', inv.paid_at, 'created_at', inv.created_at
      )) FROM invoices inv WHERE inv.project_id = p.id AND inv.deleted_at IS NULL ORDER BY inv.created_at DESC), '[]') as invoices_json
    FROM projects p
    LEFT JOIN clients c ON p.client_id = c.id
    LEFT JOIN (
      SELECT project_id, SUM(total_due) as total_invoiced,
        SUM(CASE WHEN paid_status = 'paid' THEN total_due ELSE 0 END) as total_paid
      FROM invoices WHERE deleted_at IS NULL GROUP BY project_id
    ) inv_totals ON p.id = inv_totals.project_id
    WHERE p.deleted_at IS NULL ORDER BY p.created_at DESC`;
    break;

  case 'create':
    const newId = esc(body.job_id);
    const newName = esc(body.project_name || body.name || '');
    const newClientId = body.client_id ? `'${esc(body.client_id)}'` : 'NULL';
    const newStatus = esc(body.status || 'proposal');
    sql = `INSERT INTO projects (id, name, client_id, status, created_at, updated_at)
           VALUES ('${newId}', '${newName}', ${newClientId}, '${newStatus}', datetime('now'), datetime('now'))`;
    query_type = 'write';
    result_type = 'write';
    break;

  case 'update':
    const updates = [];
    if (body.project_name !== undefined) updates.push(`name = '${esc(body.project_name)}'`);
    if (body.status !== undefined) updates.push(`status = '${esc(body.status)}'`);
    if (body.client_id !== undefined) updates.push(`client_id = ${body.client_id ? "'" + esc(body.client_id) + "'" : 'NULL'}`);
    updates.push(`updated_at = datetime('now')`);
    sql = `UPDATE projects SET ${updates.join(', ')} WHERE id = '${esc(job_id)}' AND deleted_at IS NULL`;
    query_type = 'write';
    result_type = 'write';
    break;

  case 'delete':
    sql = `UPDATE projects SET deleted_at = datetime('now') WHERE id = '${esc(job_id)}'`;
    query_type = 'write';
    result_type = 'write';
    break;

  default:
    sql = `SELECT 'unknown action: ${action}' as error`;
    result_type = 'error';
}

return [{ json: { sql, action, query_type, result_type, job_id, body } }];
