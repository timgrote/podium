-- Rename clients.email to clients.accounting_email
-- This field is the company-level accounting email, used as CC on invoice sends.
-- Person-level emails live on the contacts table.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clients' AND column_name = 'email'
  ) THEN
    ALTER TABLE clients RENAME COLUMN email TO accounting_email;
  END IF;
END $$;

-- Drop old index, create new one
DROP INDEX IF EXISTS idx_clients_email;
CREATE INDEX IF NOT EXISTS idx_clients_accounting_email ON clients(accounting_email);

-- Recreate v_project_summary with updated column name
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
    p.client_project_number,
    p.location,
    p.data_path,
    c.name AS client_name,
    c.company AS client_company,
    c.accounting_email AS client_accounting_email,
    c.address AS client_address,
    e.first_name || ' ' || e.last_name AS pm_name,
    e.email AS pm_email,
    e.avatar_url AS pm_avatar_url,
    COALESCE(SUM(con.total_amount), 0) AS total_contracted,
    COALESCE((SELECT SUM(i.total_due) FROM invoices i WHERE i.project_id = p.id AND i.deleted_at IS NULL), 0) AS total_invoiced,
    COALESCE((SELECT SUM(i.total_due) FROM invoices i WHERE i.project_id = p.id AND i.deleted_at IS NULL AND i.paid_status = 'paid'), 0) AS total_paid
FROM projects p
LEFT JOIN clients c ON p.client_id = c.id
LEFT JOIN employees e ON p.pm_id = e.id
LEFT JOIN contracts con ON con.project_id = p.id AND con.deleted_at IS NULL
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name, p.status, p.client_id, p.pm_name, p.pm_email,
         p.client_project_number, p.location, p.data_path, p.project_number,
         p.job_code, p.pm_id,
         c.name, c.company, c.accounting_email, c.address,
         e.first_name, e.last_name, e.email, e.avatar_url;
