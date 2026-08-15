-- Project Deliverables
-- Milestones/artifacts delivered to the client (preliminary plan, CDs, etc.)
-- Loosely linked to contract tasks; auto-created when a contract is signed

CREATE TABLE IF NOT EXISTS project_deliverables (
    id                TEXT PRIMARY KEY,                    -- 'del-xxxxx'
    project_id        TEXT NOT NULL REFERENCES projects(id),
    contract_task_id  TEXT REFERENCES contract_tasks(id),  -- optional loose link
    name              TEXT NOT NULL,
    sort_order        INTEGER DEFAULT 0,
    status            TEXT DEFAULT 'not_started',          -- not_started, in_progress, sent, accepted
    progress_percent  NUMERIC(5,2) DEFAULT 0,              -- 0-100, manual
    deadline          DATE,                                -- target delivery date
    sent_at           TIMESTAMPTZ,                         -- first time status → sent
    created_at        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at        TIMESTAMPTZ                           -- soft delete
);

CREATE INDEX IF NOT EXISTS idx_deliverables_project ON project_deliverables(project_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_contract_task ON project_deliverables(contract_task_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_status ON project_deliverables(status);
