-- Migration 010: Rename data_path → dropbox_path on projects, add Dropbox/Drive fields
-- Part of Phase 1 file storage strategy: link, don't copy

-- Rename projects.data_path to dropbox_path
ALTER TABLE projects RENAME COLUMN data_path TO dropbox_path;

-- Strip the local filesystem prefix from existing values
-- Converts '/mnt/d/Dropbox/TIE/TBG/Heartside Hill' → 'TBG/Heartside Hill'
UPDATE projects
SET dropbox_path = REPLACE(dropbox_path, '/mnt/d/Dropbox/TIE/', '')
WHERE dropbox_path LIKE '/mnt/d/Dropbox/TIE/%';

-- Add Google Drive folder ID for future use (Phase 4)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS drive_folder_id TEXT;

-- Add Dropbox URL field for contracts (link to signed contract in Dropbox)
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS dropbox_url TEXT;

-- Store the configurable Dropbox base path
INSERT INTO company_settings (key, value)
VALUES ('dropbox_base_path', 'TIE')
ON CONFLICT (key) DO NOTHING;
