-- Consolidate clients: merge company into name, drop company column.
-- Client.name now represents the company/entity name. Individual people are contacts.

-- Merge: prefer company name over person name where company was set
UPDATE clients
SET name = company
WHERE company IS NOT NULL
  AND company != ''
  AND company != name;

-- Drop the column
ALTER TABLE clients DROP COLUMN IF EXISTS company;

-- Recreate v_project_summary without c.company
DROP VIEW IF EXISTS v_project_summary;
CREATE VIEW v_project_summary AS
SELECT
    p.id,
    p.name,
    p.status,
    p.client_id,
    p.pm_name,
    p.pm_email,
    p.client_project_number,
    p.location,
    p.project_number,
    p.job_code,
    c.name AS client_name,
    c.email AS client_email,
    c.address AS client_address,
    COALESCE(SUM(CASE WHEN i.deleted_at IS NULL THEN i.total_due END), 0) AS total_invoiced,
    COALESCE(SUM(CASE WHEN i.paid_status = 'paid' AND i.deleted_at IS NULL THEN i.total_due END), 0) AS total_paid,
    COALESCE(SUM(CASE WHEN i.paid_status != 'paid' AND i.deleted_at IS NULL THEN i.total_due END), 0) AS total_outstanding,
    COALESCE(ct.total_contracted, 0) AS total_contracted
FROM projects p
LEFT JOIN clients c ON p.client_id = c.id
LEFT JOIN invoices i ON p.id = i.project_id
LEFT JOIN (
    SELECT project_id, SUM(total_amount) AS total_contracted
    FROM contracts
    WHERE deleted_at IS NULL
    GROUP BY project_id
) ct ON p.id = ct.project_id
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name, p.status, p.client_id, p.pm_name, p.pm_email,
         p.client_project_number, p.location, p.project_number, p.job_code,
         c.name, c.email, c.address,
         ct.total_contracted;
