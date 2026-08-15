-- Add billing_type to contract_tasks and invoice_line_items
-- 'fixed' = percentage input (default, existing behavior)
-- 'time_expense' = dollar amount input, percent back-calculated

ALTER TABLE contract_tasks ADD COLUMN IF NOT EXISTS billing_type TEXT NOT NULL DEFAULT 'fixed';
ALTER TABLE invoice_line_items ADD COLUMN IF NOT EXISTS billing_type TEXT NOT NULL DEFAULT 'fixed';
