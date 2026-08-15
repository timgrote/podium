-- Add is_pinned and tags columns to project_tasks
ALTER TABLE project_tasks ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT FALSE;
ALTER TABLE project_tasks ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

-- Index for pinned tasks (used in sorting queries)
CREATE INDEX IF NOT EXISTS idx_project_tasks_pinned ON project_tasks(is_pinned);
-- GIN index for tag array queries
CREATE INDEX IF NOT EXISTS idx_project_tasks_tags ON project_tasks USING GIN (tags);
