-- Migration: Add start_date column to project_tasks
-- Run: psql $CONDUCTOR_DATABASE_URL < db/migrations/004_add_task_start_date.sql

ALTER TABLE project_tasks ADD COLUMN IF NOT EXISTS start_date DATE;

-- Backfill existing tasks: set start_date to created_at date
UPDATE project_tasks SET start_date = created_at::date WHERE start_date IS NULL;
