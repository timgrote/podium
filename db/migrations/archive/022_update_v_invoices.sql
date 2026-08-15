-- Add client_id and job_code to v_invoices for financial reporting filters
DROP VIEW IF EXISTS v_invoices;

CREATE VIEW v_invoices AS
SELECT
    i.*,
    p.name AS project_name,
    p.job_code,
    p.client_id,
    c.name AS client_name,
    c.accounting_email AS client_email
FROM invoices i
JOIN projects p ON i.project_id = p.id
LEFT JOIN clients c ON p.client_id = c.id
WHERE i.deleted_at IS NULL;
