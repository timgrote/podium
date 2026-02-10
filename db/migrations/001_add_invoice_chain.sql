-- Migration: Add invoice chain support
-- Date: 2026-01-20
--
-- Changes:
-- 1. Add current_invoice_id to projects (points to the active/working invoice)
-- 2. Add previous_invoice_id to invoices (links invoices in a chain)
-- 3. Add previous_billing column to invoice_line_items

-- Add current_invoice_id to projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS current_invoice_id TEXT;

-- Add previous_invoice_id to invoices for chain linkage
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS previous_invoice_id TEXT;

-- Add previous_billing to track cumulative billing per line item
ALTER TABLE invoice_line_items ADD COLUMN IF NOT EXISTS previous_billing REAL DEFAULT 0;

-- Create index for invoice chain traversal
CREATE INDEX IF NOT EXISTS idx_invoices_previous ON invoices(previous_invoice_id);
