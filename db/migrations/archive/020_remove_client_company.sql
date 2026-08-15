-- Consolidate clients: merge company into name, drop company column.
-- Client.name now represents the company/entity name. Individual people are contacts.

-- Merge: prefer company name over person name where company was set
UPDATE clients
SET name = company
WHERE company IS NOT NULL
  AND company != ''
  AND company != name;

-- Must drop view first since it depends on company column
DROP VIEW IF EXISTS v_project_summary;

-- Drop the column
ALTER TABLE clients DROP COLUMN IF EXISTS company;

-- Recreate v_project_summary without c.company (matching production view structure)
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
    COALESCE((SELECT SUM(i.total_due) FROM invoices i WHERE i.project_id = p.id AND i.deleted_at IS NULL AND i.paid_status != 'paid'), 0) AS total_outstanding
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
