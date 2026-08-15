-- Add invoice_date column for user-editable date shown on invoices
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_date TEXT;
