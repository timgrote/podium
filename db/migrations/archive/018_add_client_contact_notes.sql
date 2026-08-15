-- Add notes tables for clients and contacts
-- Same structure as project_notes

CREATE TABLE IF NOT EXISTS client_notes (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    author_id TEXT REFERENCES employees(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_client_notes_client ON client_notes(client_id);

CREATE TABLE IF NOT EXISTS contact_notes (
    id TEXT PRIMARY KEY,
    contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    author_id TEXT REFERENCES employees(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contact_notes_contact ON contact_notes(contact_id);
