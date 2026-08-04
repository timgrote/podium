-- Add updated_by column to track who last updated a deliverable's status/progress
-- FK to employees, nullable for legacy rows

ALTER TABLE project_deliverables
    ADD COLUMN IF NOT EXISTS updated_by TEXT REFERENCES employees(id);
