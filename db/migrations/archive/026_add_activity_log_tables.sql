-- Activity path mappings: learned associations between file paths and projects
CREATE TABLE IF NOT EXISTS activity_path_mappings (
    id TEXT PRIMARY KEY,
    pattern TEXT NOT NULL,
    source TEXT NOT NULL,
    project_id TEXT NOT NULL REFERENCES projects(id),
    created_by TEXT REFERENCES employees(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_apm_pattern_source
    ON activity_path_mappings(pattern, source) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_apm_project ON activity_path_mappings(project_id);

-- Activity overrides: manual project assignment for specific activity items
CREATE TABLE IF NOT EXISTS activity_overrides (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_key TEXT NOT NULL,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    project_id TEXT REFERENCES projects(id),
    dismissed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ao_source_key
    ON activity_overrides(source, source_key, employee_id);
