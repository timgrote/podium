-- Add data_path to v_project_summary so it's available in project list
DROP VIEW IF EXISTS v_project_summary;
CREATE VIEW v_project_summary AS
SELECT
    p.id,
    p.name,
    p.status,
    p.client_id,
    p.pm_id,
    COALESCE(e.first_name || ' ' || e.last_name, p.pm_name) AS pm_name,
    COALESCE(e.email, p.pm_email) AS pm_email,
    e.avatar_url AS pm_avatar_url,
    p.client_project_number,
    p.location,
    p.project_number,
    p.job_code,
    p.data_path,
    c.name AS client_name,
    c.company AS client_company,
    c.email AS client_email,
    c.address AS client_address,
    COALESCE(SUM(CASE WHEN i.deleted_at IS NULL THEN i.total_due END), 0) AS total_invoiced,
    COALESCE(SUM(CASE WHEN i.paid_status = 'paid' AND i.deleted_at IS NULL THEN i.total_due END), 0) AS total_paid,
    COALESCE(SUM(CASE WHEN i.paid_status != 'paid' AND i.deleted_at IS NULL THEN i.total_due END), 0) AS total_outstanding,
    COALESCE(ct.total_contracted, 0) AS total_contracted
FROM projects p
LEFT JOIN clients c ON p.client_id = c.id
LEFT JOIN employees e ON p.pm_id = e.id
LEFT JOIN invoices i ON p.id = i.project_id
LEFT JOIN (
    SELECT project_id, SUM(total_amount) AS total_contracted
    FROM contracts
    WHERE deleted_at IS NULL
    GROUP BY project_id
) ct ON p.id = ct.project_id
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name, p.status, p.client_id, p.pm_id,
         p.pm_name, p.pm_email,
         e.first_name, e.last_name, e.email, e.avatar_url,
         p.client_project_number, p.location, p.project_number, p.job_code,
         p.data_path,
         c.name, c.company, c.email, c.address,
         ct.total_contracted;
