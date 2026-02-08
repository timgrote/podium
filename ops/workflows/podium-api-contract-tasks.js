// Updated Parse & Build Query code for Podium - Projects API (SQLite)
// Add these cases to the existing switch statement in the "Parse & Build Query" node
// Workflow ID: sqlite-projects-api

// ============================================================================
// CONTRACT TASK ACTIONS - Add to the switch(action) block
// ============================================================================

    case 'get_contract':
      // Get a single contract with its tasks
      if (!body.contract_id) {
        return [{ json: { sql: '', action, query_type: 'select', result_type: 'error', error: 'Missing contract_id', debug } }];
      }
      sql = `SELECT
        c.id, c.project_id, c.file_path, c.total_amount, c.signed_at, c.notes,
        c.created_at, c.updated_at,
        COALESCE((SELECT json_group_array(json_object(
          'id', ct.id, 'name', ct.name, 'description', ct.description,
          'amount', ct.amount, 'billed_amount', ct.billed_amount,
          'billed_percent', ct.billed_percent, 'sort_order', ct.sort_order
        )) FROM contract_tasks ct WHERE ct.contract_id = c.id ORDER BY ct.sort_order), '[]') as tasks_json
      FROM contracts c
      WHERE c.id = '${esc(body.contract_id)}' AND c.deleted_at IS NULL`;
      result_type = 'contract';
      break;

    case 'add_contract_task':
      // Add a task to a contract
      if (!body.contract_id || !body.task) {
        return [{ json: { sql: '', action, query_type: 'select', result_type: 'error', error: 'Missing contract_id or task', debug } }];
      }
      const newTaskId = 'ctask-' + Date.now().toString(36);
      const taskName = esc(body.task.name || '');
      const taskDesc = body.task.description ? `'${esc(body.task.description)}'` : 'NULL';
      const taskAmount = Number(body.task.amount) || 0;
      const taskOrder = Number(body.task.sort_order) || 0;

      sql = `INSERT INTO contract_tasks (id, contract_id, sort_order, name, description, amount, billed_amount, billed_percent, created_at, updated_at)
             VALUES ('${newTaskId}', '${esc(body.contract_id)}', ${taskOrder}, '${taskName}', ${taskDesc}, ${taskAmount}, 0, 0, datetime('now'), datetime('now'))`;
      query_type = 'write';
      result_type = 'write';
      debug.new_task_id = newTaskId;
      break;

    case 'update_contract_task':
      // Update an existing contract task
      if (!body.task_id) {
        return [{ json: { sql: '', action, query_type: 'select', result_type: 'error', error: 'Missing task_id', debug } }];
      }
      const taskUpdates = [];
      if (body.task) {
        if (body.task.name !== undefined) taskUpdates.push(`name = '${esc(body.task.name)}'`);
        if (body.task.description !== undefined) taskUpdates.push(`description = ${body.task.description ? "'" + esc(body.task.description) + "'" : 'NULL'}`);
        if (body.task.amount !== undefined) taskUpdates.push(`amount = ${Number(body.task.amount) || 0}`);
        if (body.task.sort_order !== undefined) taskUpdates.push(`sort_order = ${Number(body.task.sort_order) || 0}`);
      }
      taskUpdates.push(`updated_at = datetime('now')`);

      sql = `UPDATE contract_tasks SET ${taskUpdates.join(', ')} WHERE id = '${esc(body.task_id)}'`;
      query_type = 'write';
      result_type = 'write';
      break;

    case 'delete_contract_task':
      // Delete a contract task
      if (!body.task_id) {
        return [{ json: { sql: '', action, query_type: 'select', result_type: 'error', error: 'Missing task_id', debug } }];
      }
      sql = `DELETE FROM contract_tasks WHERE id = '${esc(body.task_id)}'`;
      query_type = 'write';
      result_type = 'write';
      break;

    case 'create_invoice_from_contract':
      // Creates invoice line items from contract tasks
      // This is complex - requires multiple SQL statements
      // For now, return the data needed to create the invoice
      if (!body.contract_id || !body.tasks || !Array.isArray(body.tasks)) {
        return [{ json: { sql: '', action, query_type: 'select', result_type: 'error', error: 'Missing contract_id or tasks array', debug } }];
      }
      // First, get the contract and its tasks to validate
      sql = `SELECT
        c.id as contract_id, c.project_id, c.total_amount,
        p.id as job_id, p.name as project_name,
        (SELECT COUNT(*) + 1 FROM invoices WHERE project_id = c.project_id AND deleted_at IS NULL) as next_invoice_num,
        COALESCE((SELECT json_group_array(json_object(
          'id', ct.id, 'name', ct.name, 'amount', ct.amount,
          'billed_amount', ct.billed_amount, 'billed_percent', ct.billed_percent
        )) FROM contract_tasks ct WHERE ct.contract_id = c.id), '[]') as tasks_json
      FROM contracts c
      JOIN projects p ON c.project_id = p.id
      WHERE c.id = '${esc(body.contract_id)}' AND c.deleted_at IS NULL`;
      result_type = 'invoice_prep';
      debug.requested_tasks = body.tasks;
      break;

// ============================================================================
// UPDATE get_detail to include contract_tasks
// Replace the existing get_detail case with this version:
// ============================================================================

    case 'get_detail':
      sql = `SELECT
        p.id as job_id, p.name as project_name, p.status, p.data_path, p.notes,
        p.current_invoice_id, p.created_at, p.updated_at,
        c.id as client_id, c.name as client_name, c.email as client_email,
        c.company as client_company, c.phone as client_phone, c.address as client_address,
        COALESCE((SELECT json_group_array(json_object(
          'id', pr.id, 'status', pr.status, 'total_fee', pr.total_fee,
          'sent_at', pr.sent_at, 'created_at', pr.created_at
        )) FROM proposals pr WHERE pr.project_id = p.id AND pr.deleted_at IS NULL), '[]') as proposals_json,
        COALESCE((SELECT json_group_array(json_object(
          'id', ct.id, 'total_amount', ct.total_amount, 'signed_at', ct.signed_at,
          'file_path', ct.file_path, 'created_at', ct.created_at,
          'tasks', (SELECT json_group_array(json_object(
            'id', ctt.id, 'name', ctt.name, 'description', ctt.description,
            'amount', ctt.amount, 'billed_amount', ctt.billed_amount,
            'billed_percent', ctt.billed_percent, 'sort_order', ctt.sort_order
          )) FROM contract_tasks ctt WHERE ctt.contract_id = ct.id ORDER BY ctt.sort_order)
        )) FROM contracts ct WHERE ct.project_id = p.id AND ct.deleted_at IS NULL), '[]') as contracts_json,
        COALESCE((SELECT json_group_array(json_object(
          'id', inv.id, 'invoice_number', inv.invoice_number, 'total_due', inv.total_due,
          'sent_status', inv.sent_status, 'paid_status', inv.paid_status,
          'data_path', inv.data_path, 'previous_invoice_id', inv.previous_invoice_id,
          'sent_at', inv.sent_at, 'paid_at', inv.paid_at, 'created_at', inv.created_at
        )) FROM invoices inv WHERE inv.project_id = p.id AND inv.deleted_at IS NULL ORDER BY inv.created_at DESC), '[]') as invoices_json
      FROM projects p
      LEFT JOIN clients c ON p.client_id = c.id
      WHERE p.id = '${esc(job_id)}' AND p.deleted_at IS NULL`;
      result_type = 'detail';
      break;


// ============================================================================
// ADD to Format Response node - handle new result types
// ============================================================================

// Add these cases to the Format Response code node:

if (action === 'get_contract') {
  if (rows.length === 0) return [{ json: { success: false, error: 'Contract not found' } }];
  const row = rows[0];
  const contract = {
    ...row,
    tasks: JSON.parse(row.tasks_json || '[]')
  };
  delete contract.tasks_json;
  return [{ json: { contract } }];
}

if (result_type === 'invoice_prep') {
  if (rows.length === 0) return [{ json: { success: false, error: 'Contract not found' } }];
  const row = rows[0];
  const contractTasks = JSON.parse(row.tasks_json || '[]');
  const requestedTasks = context.debug.requested_tasks || [];

  // Calculate invoice amounts
  let totalDue = 0;
  const lineItems = requestedTasks.map((req, idx) => {
    const task = contractTasks.find(t => t.id === req.task_id);
    if (!task) return null;
    const percentThisInvoice = Number(req.percent_this_invoice) || 0;
    const currentBilling = (task.amount * percentThisInvoice) / 100;
    totalDue += currentBilling;
    return {
      task_id: task.id,
      name: task.name,
      amount: task.amount,
      percent_this_invoice: percentThisInvoice,
      previous_billing: task.billed_amount,
      current_billing: currentBilling,
      sort_order: idx + 1
    };
  }).filter(Boolean);

  const invoiceNumber = `${row.job_id}-${row.next_invoice_num}`;

  return [{ json: {
    success: true,
    invoice_prep: {
      contract_id: row.contract_id,
      project_id: row.project_id,
      job_id: row.job_id,
      project_name: row.project_name,
      invoice_number: invoiceNumber,
      total_due: totalDue,
      line_items: lineItems
    }
  } }];
}
