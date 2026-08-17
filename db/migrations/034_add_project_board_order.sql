-- Add per-column ordering for the Kanban board.
-- board_order controls card order WITHIN a single status column (0 = top).
-- Cross-column position is already expressed by the existing status column.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS board_order INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_projects_board ON projects(status, board_order);
