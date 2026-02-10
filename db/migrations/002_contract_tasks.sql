-- Migration 002: Add contract_tasks table
-- Stores tasks/phases on contracts for billing

CREATE TABLE IF NOT EXISTS contract_tasks (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL REFERENCES contracts(id),
    sort_order INTEGER DEFAULT 0,
    name TEXT NOT NULL,
    description TEXT,
    amount NUMERIC(12,2) DEFAULT 0,
    billed_amount NUMERIC(12,2) DEFAULT 0,
    billed_percent NUMERIC(5,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contract_tasks_contract ON contract_tasks(contract_id);
