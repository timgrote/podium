-- Migration: Add employees, project_tasks, project_task_assignees, project_task_notes
-- Run: psql $CONDUCTOR_DATABASE_URL < db/migrations/003_add_employees_and_tasks.sql

CREATE TABLE IF NOT EXISTS employees (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    bot_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS project_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    parent_id TEXT REFERENCES project_tasks(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo',
    priority INTEGER,
    due_date DATE,
    reminder_at TIMESTAMPTZ,
    sort_order INTEGER DEFAULT 0,
    created_by TEXT REFERENCES employees(id),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_project_tasks_project ON project_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_project_tasks_parent ON project_tasks(parent_id);
CREATE INDEX IF NOT EXISTS idx_project_tasks_status ON project_tasks(status);

CREATE TABLE IF NOT EXISTS project_task_assignees (
    task_id TEXT NOT NULL REFERENCES project_tasks(id) ON DELETE CASCADE,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    PRIMARY KEY (task_id, employee_id)
);

CREATE TABLE IF NOT EXISTS project_task_notes (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES project_tasks(id) ON DELETE CASCADE,
    author_id TEXT REFERENCES employees(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_notes_task ON project_task_notes(task_id);
