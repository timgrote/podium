-- Project ID redesign: separate internal PK from user-facing identifiers
-- id (PK) stays as-is for existing projects, new projects use proj-xxxx format
-- project_number: auto-incremented YY-NNN format (e.g., 26-001)
-- job_code: editable shorthand (e.g., rvi-absal)

ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_number TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS job_code TEXT;

-- Backfill existing projects with project_number based on creation order
DO $$
DECLARE
    rec RECORD;
    seq INT := 0;
    yr TEXT;
BEGIN
    yr := to_char(CURRENT_DATE, 'YY');
    FOR rec IN
        SELECT id FROM projects WHERE project_number IS NULL ORDER BY created_at ASC
    LOOP
        seq := seq + 1;
        UPDATE projects SET project_number = yr || '-' || LPAD(seq::TEXT, 3, '0') WHERE id = rec.id;
    END LOOP;
END $$;

-- Backfill job_code from existing id (since old ids were user-defined job codes)
UPDATE projects SET job_code = id WHERE job_code IS NULL;

-- Recreate view to include new columns
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
    c.company AS client_company,
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
         c.name, c.company, c.email, c.address,
         ct.total_contracted;
