-- Conductor Database Schema
-- SQLite 3.x
--
-- Naming conventions:
--   - Tables: plural, snake_case
--   - Primary keys: id (auto-increment) or natural key where appropriate
--   - Foreign keys: singular_table_id
--   - Timestamps: created_at, updated_at, deleted_at (soft delete)

PRAGMA foreign_keys = ON;

-- ============================================================================
-- CLIENTS
-- Companies or individuals we do business with
-- ============================================================================
CREATE TABLE clients (
    id TEXT PRIMARY KEY,                    -- e.g., 'c-abc123' (generated)
    name TEXT NOT NULL,
    email TEXT,
    company TEXT,
    phone TEXT,
    address TEXT,
    notes TEXT,                             -- markdown
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    deleted_at TEXT                         -- soft delete
);

CREATE INDEX idx_clients_email ON clients(email);
CREATE INDEX idx_clients_company ON clients(company);

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
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    deleted_at TEXT
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
    status TEXT DEFAULT 'proposal',         -- proposal, contract, invoiced, paid, complete
    data_path TEXT,                         -- dropbox folder path, e.g., 'TBG/HeronLakes'
    notes TEXT,                             -- markdown
    current_invoice_id TEXT,                -- active/working invoice (FK added after invoices table)
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    deleted_at TEXT
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
    total_amount REAL DEFAULT 0,            -- contracted amount
    signed_at TEXT,                         -- when contract was signed
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    deleted_at TEXT
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
    amount REAL DEFAULT 0,                  -- total fee for this task
    billed_amount REAL DEFAULT 0,           -- cumulative amount already billed
    billed_percent REAL DEFAULT 0,          -- cumulative percent already billed (0-100)
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
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
    total_fee REAL DEFAULT 0,
    engineer_key TEXT,                      -- tim/ally/matara
    engineer_name TEXT,
    engineer_title TEXT,
    contact_method TEXT,                    -- e.g., 'site meeting', 'phone call'
    proposal_date TEXT,                     -- date shown on proposal doc
    sent_at TEXT,
    status TEXT DEFAULT 'draft',            -- draft, sent, accepted, rejected
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    deleted_at TEXT
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
    amount REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
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
    sent_status TEXT DEFAULT 'unsent',      -- unsent, sent
    paid_status TEXT DEFAULT 'unpaid',      -- unpaid, partial, paid
    total_due REAL DEFAULT 0,
    sent_at TEXT,
    paid_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    deleted_at TEXT
);

CREATE UNIQUE INDEX idx_invoices_number ON invoices(invoice_number);
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
    quantity REAL DEFAULT 1,                -- hours, units, etc. (or percent complete)
    unit_price REAL DEFAULT 0,              -- rate per unit (or task fee)
    amount REAL DEFAULT 0,                  -- current billing (quantity * unit_price, or flat)
    previous_billing REAL DEFAULT 0,        -- cumulative billing from prior invoices
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_invoice_items_invoice ON invoice_line_items(invoice_id);

-- ============================================================================
-- VIEWS
-- Computed totals and useful joins
-- ============================================================================

-- Project summary with computed totals
CREATE VIEW v_project_summary AS
SELECT
    p.id,
    p.name,
    p.status,
    p.client_id,
    p.pm_name,
    p.pm_email,
    p.client_project_number,
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
GROUP BY p.id;

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
    c.name AS client_name,
    c.email AS client_email
FROM invoices i
JOIN projects p ON i.project_id = p.id
LEFT JOIN clients c ON p.client_id = c.id
WHERE i.deleted_at IS NULL;
