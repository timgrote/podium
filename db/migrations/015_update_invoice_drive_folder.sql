-- Update invoice_drive_folder_id from TIE/Podium/Invoices to TIE shared drive root
-- so sheets/PDFs are saved to TIE/Client/Project structure matching Dropbox
UPDATE company_settings
SET value = '0AMtARvjeroXbUk9PVA'
WHERE key = 'invoice_drive_folder_id'
  AND value = '1ZY47YUzPF7mE9dFnkdoyZgk38Qv4GfuL';
