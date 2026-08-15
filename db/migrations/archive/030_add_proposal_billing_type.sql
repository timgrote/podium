-- Add billing_type to proposal_tasks so proposals can mark tasks as fixed or T&E.
-- Mirrors contract_tasks.billing_type; carried through on promote-to-contract.
ALTER TABLE proposal_tasks
    ADD COLUMN IF NOT EXISTS billing_type TEXT NOT NULL DEFAULT 'fixed';
