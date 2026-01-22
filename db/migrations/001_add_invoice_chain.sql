-- Migration: Add invoice chain support
-- Date: 2026-01-20
--
-- Changes:
-- 1. Add current_invoice_id to projects (points to the active/working invoice)
-- 2. Add previous_invoice_id to invoices (links invoices in a chain)
-- 3. Add previous_billing column to invoice_line_items

-- Add current_invoice_id to projects
ALTER TABLE projects ADD COLUMN current_invoice_id TEXT REFERENCES invoices(id);

-- Add previous_invoice_id to invoices for chain linkage
ALTER TABLE invoices ADD COLUMN previous_invoice_id TEXT REFERENCES invoices(id);

-- Add previous_billing to track cumulative billing per line item
ALTER TABLE invoice_line_items ADD COLUMN previous_billing REAL DEFAULT 0;

-- Create index for invoice chain traversal
CREATE INDEX idx_invoices_previous ON invoices(previous_invoice_id);
