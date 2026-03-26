-- Optimize v_project_summary: add next_task_deadline, last_activity, and entity counts
-- so the list endpoint can be a single query instead of 300+ N+1 queries.
DROP VIEW IF EXISTS v_project_summary;
CREATE VIEW v_project_summary AS
SELECT
    p.id,
    p.name AS project_name,
    p.project_number,
    p.job_code,
    p.status,
    p.client_id,
    p.pm_id,
    p.client_pm_id,
    p.client_project_number,
    p.location,
    p.data_path,
    c.name AS client_name,
    c.accounting_email AS client_accounting_email,
    c.address AS client_address,
    (e.first_name || ' ' || e.last_name) AS pm_name,
    e.email AS pm_email,
    e.avatar_url AS pm_avatar_url,
    ct.name AS client_pm_name,
    ct.email AS client_pm_email,
    COALESCE(SUM(con.total_amount), 0) AS total_contracted,
    COALESCE((SELECT SUM(i.total_due) FROM invoices i WHERE i.project_id = p.id AND i.deleted_at IS NULL), 0) AS total_invoiced,
    COALESCE((SELECT SUM(i.total_due) FROM invoices i WHERE i.project_id = p.id AND i.deleted_at IS NULL AND i.paid_status = 'paid'), 0) AS total_paid,
    COALESCE((SELECT SUM(i.total_due) FROM invoices i WHERE i.project_id = p.id AND i.deleted_at IS NULL AND i.paid_status != 'paid'), 0) AS total_outstanding,
    -- Next task deadline: earliest due_date from incomplete tasks
    (SELECT MIN(pt.due_date) FROM project_tasks pt
     WHERE pt.project_id = p.id AND pt.completed_at IS NULL
     AND pt.due_date IS NOT NULL AND pt.deleted_at IS NULL
    ) AS next_task_deadline,
    -- Last activity: most recent timestamp across project, notes, and task notes
    GREATEST(
        p.updated_at,
        (SELECT MAX(pn.created_at) FROM project_notes pn WHERE pn.project_id = p.id),
        (SELECT MAX(ptn.created_at) FROM project_task_notes ptn
         JOIN project_tasks pt2 ON ptn.task_id = pt2.id WHERE pt2.project_id = p.id)
    ) AS last_activity,
    -- Entity counts for sidebar badges
    (SELECT COUNT(*) FROM contracts con2 WHERE con2.project_id = p.id AND con2.deleted_at IS NULL) AS contract_count,
    (SELECT COUNT(*) FROM invoices inv WHERE inv.project_id = p.id AND inv.deleted_at IS NULL) AS invoice_count,
    (SELECT COUNT(*) FROM proposals prop WHERE prop.project_id = p.id AND prop.deleted_at IS NULL) AS proposal_count
FROM projects p
LEFT JOIN clients c ON p.client_id = c.id
LEFT JOIN employees e ON p.pm_id = e.id
LEFT JOIN contacts ct ON p.client_pm_id = ct.id
LEFT JOIN contracts con ON con.project_id = p.id AND con.deleted_at IS NULL
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name, p.status, p.client_id, p.pm_name, p.pm_email,
         p.client_project_number, p.location, p.data_path, p.project_number,
         p.job_code, p.pm_id, p.client_pm_id,
         c.name, c.accounting_email, c.address,
         e.first_name, e.last_name, e.email, e.avatar_url,
         ct.name, ct.email;
