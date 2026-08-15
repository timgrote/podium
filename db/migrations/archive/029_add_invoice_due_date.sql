ALTER TABLE invoices ADD COLUMN IF NOT EXISTS due_date TEXT;

-- Recreate v_invoices to pick up the new column
DROP VIEW IF EXISTS v_invoices;

CREATE VIEW v_invoices AS
SELECT
    i.*,
    p.name AS project_name,
    p.job_code,
    p.client_id,
    p.pm_id,
    c.name AS client_name,
    c.accounting_email AS client_email,
    CONCAT_WS(' ', e.first_name, e.last_name) AS pm_name
FROM invoices i
JOIN projects p ON i.project_id = p.id
LEFT JOIN clients c ON p.client_id = c.id
LEFT JOIN employees e ON p.pm_id = e.id
WHERE i.deleted_at IS NULL;
