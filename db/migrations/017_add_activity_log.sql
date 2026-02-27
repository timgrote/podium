-- Activity log for tracking who did what
-- Used by weekly review reports

CREATE TABLE IF NOT EXISTS activity_log (
    id TEXT PRIMARY KEY,
    actor_id TEXT REFERENCES employees(id),    -- who performed the action (NULL if unknown)
    action TEXT NOT NULL,                       -- 'created', 'sent', 'completed', 'signed', 'paid', 'deleted', 'promoted'
    entity_type TEXT NOT NULL,                  -- 'invoice', 'proposal', 'project', 'project_task', 'contract', 'project_note', 'task_note'
    entity_id TEXT NOT NULL,                    -- ID of the entity acted upon
    project_id TEXT REFERENCES projects(id),    -- denormalized for fast weekly queries
    metadata JSONB,                             -- optional context (e.g., {"old_status": "draft", "new_status": "sent"})
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_activity_log_actor ON activity_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_project ON activity_log(project_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_entity_type ON activity_log(entity_type);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at);
