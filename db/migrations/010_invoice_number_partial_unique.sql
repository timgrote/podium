-- Make invoice_number unique only among non-deleted invoices
-- This allows soft-deleted invoices to have duplicate numbers without blocking new ones
DROP INDEX IF EXISTS idx_invoices_number;
CREATE UNIQUE INDEX idx_invoices_number ON invoices (invoice_number) WHERE deleted_at IS NULL;
