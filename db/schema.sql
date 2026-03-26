-- Conductor Database Schema
-- PostgreSQL
--
-- Naming conventions:
--   - Tables: plural, snake_case
--   - Primary keys: id (application-generated text) or natural key where appropriate
--   - Foreign keys: singular_table_id
--   - Timestamps: created_at, updated_at, deleted_at (soft delete)

-- ============================================================================
-- CLIENTS
-- Companies or individuals we do business with
-- ============================================================================
CREATE TABLE clients (
    id TEXT PRIMARY KEY,                    -- e.g., 'c-abc123' (generated)
    name TEXT NOT NULL,                     -- company/entity name
    accounting_email TEXT,
    phone TEXT,
    address TEXT,
    notes TEXT,                             -- markdown
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ                  -- soft delete
);

CREATE INDEX idx_clients_email ON clients(email);
CREATE INDEX idx_clients_name ON clients(name);

-- ============================================================================
-- CONTACTS
-- Individual people associated with projects (PMs, engineers, etc.)
-- Separate from clients - a client might have multiple contacts
-- ============================================================================
CREATE TABLE contacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    role TEXT,                              -- e.g., 'Project Manager', 'Engineer'
    client_id TEXT REFERENCES clients(id),  -- optional link to parent client
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_contacts_client ON contacts(client_id);
CREATE INDEX idx_contacts_email ON contacts(email);

-- ============================================================================
-- PROJECTS
-- The core entity - a job/project we're working on
-- ============================================================================
CREATE TABLE projects (
    id TEXT PRIMARY KEY,                    -- e.g., 'JBHL21' (user-defined job_id)
    name TEXT NOT NULL,
    client_id TEXT REFERENCES clients(id),
    client_pm_id TEXT REFERENCES contacts(id),  -- project manager contact
    pm_name TEXT,                           -- project manager name (denormalized for convenience)
    pm_email TEXT,                          -- project manager email
    client_project_number TEXT,             -- client's internal project/PO number
    location TEXT,                           -- e.g., 'Austin, TX'
    project_number TEXT,                    -- user-facing identifier, e.g., '26-001' (auto-incremented)
    job_code TEXT,                          -- editable shorthand, e.g., 'rvi-absal'
    status TEXT DEFAULT 'lead',             -- lead, active, complete, archive
    data_path TEXT,                         -- relative folder path, e.g., 'TBG/HeronLakes'
    notes TEXT,                             -- markdown
    current_invoice_id TEXT,                -- active/working invoice (FK added after invoices table)
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_projects_client ON projects(client_id);
CREATE INDEX idx_projects_status ON projects(status);

-- ============================================================================
-- PROJECT_CONTACTS
-- Junction table: which contacts are associated with which projects
-- ============================================================================
CREATE TABLE project_contacts (
    project_id TEXT NOT NULL REFERENCES projects(id),
    contact_id TEXT NOT NULL REFERENCES contacts(id),
    role TEXT,                              -- role on this specific project
    PRIMARY KEY (project_id, contact_id)
);

-- ============================================================================
-- CONTRACTS
-- Signed agreements attached to projects
-- ============================================================================
CREATE TABLE contracts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    file_path TEXT,                         -- path to signed PDF
    total_amount NUMERIC(12,2) DEFAULT 0,   -- contracted amount
    signed_at TIMESTAMPTZ,                  -- when contract was signed
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_contracts_project ON contracts(project_id);

-- ============================================================================
-- CONTRACT_TASKS
-- Line items on a contract (tasks/phases to be billed)
-- Tracks cumulative billing for invoice chaining
-- ============================================================================
CREATE TABLE contract_tasks (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL REFERENCES contracts(id),
    sort_order INTEGER DEFAULT 0,           -- display order (1, 2, 3...)
    name TEXT NOT NULL,
    description TEXT,
    amount NUMERIC(12,2) DEFAULT 0,         -- total fee for this task
    billing_type TEXT NOT NULL DEFAULT 'fixed', -- 'fixed' or 'time_expense'
    billed_amount NUMERIC(12,2) DEFAULT 0,  -- cumulative amount already billed
    billed_percent NUMERIC(5,2) DEFAULT 0,  -- cumulative percent already billed (0-100)
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contract_tasks_contract ON contract_tasks(contract_id);

-- ============================================================================
-- PROPOSALS
-- Unsigned contracts / quotes sent to clients
-- ============================================================================
CREATE TABLE proposals (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    data_path TEXT,                         -- word doc / google doc URL
    pdf_path TEXT,                          -- generated PDF URL
    client_company TEXT,
    client_contact_email TEXT,
    total_fee NUMERIC(12,2) DEFAULT 0,
    engineer_key TEXT,                      -- tim/ally/matara
    engineer_name TEXT,
    engineer_title TEXT,
    contact_method TEXT,                    -- e.g., 'site meeting', 'phone call'
    proposal_date TEXT,                     -- date shown on proposal doc
    sent_at TIMESTAMPTZ,
    status TEXT DEFAULT 'draft',            -- draft, sent, accepted, rejected
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_proposals_project ON proposals(project_id);
CREATE INDEX idx_proposals_status ON proposals(status);

-- ============================================================================
-- PROPOSAL_TASKS
-- Line items on a proposal
-- ============================================================================
CREATE TABLE proposal_tasks (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL REFERENCES proposals(id),
    sort_order INTEGER DEFAULT 0,           -- display order (1, 2, 3...)
    name TEXT NOT NULL,
    description TEXT,
    amount NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_proposal_tasks_proposal ON proposal_tasks(proposal_id);

-- ============================================================================
-- INVOICES
-- Both task-based and list-based invoices in one table
-- Type column distinguishes them
-- ============================================================================
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    invoice_number TEXT NOT NULL,           -- e.g., 'JBHL21-1' (project_id + sequence)
    project_id TEXT NOT NULL REFERENCES projects(id),
    contract_id TEXT REFERENCES contracts(id),  -- optional link to contract
    previous_invoice_id TEXT REFERENCES invoices(id),  -- links invoices in a chain
    type TEXT DEFAULT 'task',               -- 'task' or 'list'
    description TEXT,                       -- mainly for list invoices
    data_path TEXT,                         -- excel/google sheet (URL)
    pdf_path TEXT,                          -- generated PDF
    invoice_date TEXT,                      -- user-editable date shown on invoice
    sent_status TEXT DEFAULT 'unsent',      -- unsent, sent
    paid_status TEXT DEFAULT 'unpaid',      -- unpaid, partial, paid
    total_due NUMERIC(12,2) DEFAULT 0,
    sent_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_invoices_number ON invoices(invoice_number) WHERE deleted_at IS NULL;
CREATE INDEX idx_invoices_project ON invoices(project_id);
CREATE INDEX idx_invoices_status ON invoices(sent_status, paid_status);
CREATE INDEX idx_invoices_previous ON invoices(previous_invoice_id);

-- ============================================================================
-- INVOICE_LINE_ITEMS
-- Line items for both invoice types
-- For task invoices: tasks from the proposal
-- For list invoices: hours, expenses, etc.
-- ============================================================================
CREATE TABLE invoice_line_items (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL REFERENCES invoices(id),
    sort_order INTEGER DEFAULT 0,
    name TEXT NOT NULL,
    description TEXT,
    quantity NUMERIC(12,2) DEFAULT 1,       -- hours, units, etc. (or percent complete)
    unit_price NUMERIC(12,2) DEFAULT 0,     -- rate per unit (or task fee)
    amount NUMERIC(12,2) DEFAULT 0,         -- current billing (quantity * unit_price, or flat)
    previous_billing NUMERIC(12,2) DEFAULT 0, -- cumulative billing from prior invoices
    billing_type TEXT NOT NULL DEFAULT 'fixed', -- 'fixed' or 'time_expense'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoice_items_invoice ON invoice_line_items(invoice_id);

-- ============================================================================
-- EMPLOYEES
-- Internal staff members (engineers, PMs, etc.)
-- ============================================================================
CREATE TABLE employees (
    id TEXT PRIMARY KEY,                    -- e.g., 'emp-abc123'
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    bot_id TEXT,                            -- Discord bot ID for future reminders
    password_hash TEXT,                     -- bcrypt hash for auth
    avatar_url TEXT,                        -- path to uploaded avatar image
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- ============================================================================
-- SESSIONS
-- Server-side session tokens for employee authentication
-- ============================================================================
CREATE TABLE sessions (
    token TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_sessions_employee ON sessions(employee_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- ============================================================================
-- PASSWORD RESETS
-- Time-limited tokens for admin-initiated password resets
-- ============================================================================
CREATE TABLE password_resets (
    token TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ              -- set when token is consumed
);
CREATE INDEX idx_password_resets_employee ON password_resets(employee_id);

-- ============================================================================
-- USER SETTINGS
-- Per-user key-value preferences (e.g., dropbox_base_path)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_settings (
    employee_id TEXT NOT NULL REFERENCES employees(id),
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (employee_id, key)
);

-- ============================================================================
-- PROJECT TASKS
-- Internal tasks on a project (separate from contract_tasks billing items)
-- ============================================================================
CREATE TABLE project_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    parent_id TEXT REFERENCES project_tasks(id),  -- one level of subtasks
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo',             -- todo, in_progress, blocked, done, canceled
    priority INTEGER,                       -- nullable, not in UI yet
    start_date DATE,
    due_date DATE,
    reminder_at TIMESTAMPTZ,               -- for future cron, not implemented yet
    sort_order INTEGER DEFAULT 0,
    created_by TEXT REFERENCES employees(id),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_project_tasks_project ON project_tasks(project_id);
CREATE INDEX idx_project_tasks_parent ON project_tasks(parent_id);
CREATE INDEX idx_project_tasks_status ON project_tasks(status);

-- ============================================================================
-- PROJECT TASK ASSIGNEES
-- Junction: which employees are assigned to which tasks
-- ============================================================================
CREATE TABLE project_task_assignees (
    task_id TEXT NOT NULL REFERENCES project_tasks(id) ON DELETE CASCADE,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    PRIMARY KEY (task_id, employee_id)
);

-- ============================================================================
-- PROJECT TASK NOTES
-- Timestamped comments on tasks
-- ============================================================================
CREATE TABLE project_task_notes (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES project_tasks(id) ON DELETE CASCADE,
    author_id TEXT REFERENCES employees(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_task_notes_task ON project_task_notes(task_id);

-- ============================================================================
-- PROJECT NOTES
-- Timestamped comments on projects (similar to task notes)
-- ============================================================================
CREATE TABLE project_notes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author_id TEXT REFERENCES employees(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_project_notes_project ON project_notes(project_id);

CREATE TABLE client_notes (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    author_id TEXT REFERENCES employees(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_client_notes_client ON client_notes(client_id);

CREATE TABLE contact_notes (
    id TEXT PRIMARY KEY,
    contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    author_id TEXT REFERENCES employees(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contact_notes_contact ON contact_notes(contact_id);
-- ============================================================================
-- TIME ENTRIES
-- Hours logged against projects for visibility/management
-- ============================================================================
CREATE TABLE IF NOT EXISTS time_entries (
    id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    project_id TEXT NOT NULL REFERENCES projects(id),
    contract_task_id TEXT REFERENCES contract_tasks(id),
    hours NUMERIC(6,2) NOT NULL,
    date DATE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_time_entries_employee ON time_entries(employee_id);
CREATE INDEX idx_time_entries_project ON time_entries(project_id);
CREATE INDEX idx_time_entries_date ON time_entries(date);

-- ============================================================================
-- VIEWS
-- Computed totals and useful joins
-- ============================================================================

-- Project summary with computed totals
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
    (SELECT MIN(pt.due_date) FROM project_tasks pt
     WHERE pt.project_id = p.id AND pt.completed_at IS NULL
     AND pt.due_date IS NOT NULL AND pt.deleted_at IS NULL
    ) AS next_task_deadline,
    GREATEST(
        p.updated_at,
        (SELECT MAX(pn.created_at) FROM project_notes pn WHERE pn.project_id = p.id),
        (SELECT MAX(ptn.created_at) FROM project_task_notes ptn
         JOIN project_tasks pt2 ON ptn.task_id = pt2.id WHERE pt2.project_id = p.id)
    ) AS last_activity,
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

-- Company settings (key-value store)
CREATE TABLE IF NOT EXISTS company_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Invoice list with project info
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
