-- Per-user settings (key-value, same pattern as company_settings)
CREATE TABLE IF NOT EXISTS user_settings (
    employee_id TEXT NOT NULL REFERENCES employees(id),
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (employee_id, key)
);
