-- Password reset tokens
CREATE TABLE IF NOT EXISTS password_resets (
    token TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ              -- set when token is consumed
);
CREATE INDEX IF NOT EXISTS idx_password_resets_employee ON password_resets(employee_id);
