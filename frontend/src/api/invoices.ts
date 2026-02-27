import type { Invoice } from '../types'
import { apiFetch } from './client'

export function getInvoice(id: string): Promise<Invoice> {
  return apiFetch(`/invoices/${id}`)
}

export function getInvoiceByNumber(num: string): Promise<Invoice> {
  return apiFetch(`/invoices/by-number/${encodeURIComponent(num)}`)
}

export function updateInvoice(
  id: string,
  data: {
    invoice_number?: string
    sent_status?: string
    paid_status?: string
    paid_at?: string
    total_due?: number
    description?: string
    data_path?: string
    pdf_path?: string
    line_items?: {
      quantity?: number
      unit_price?: number
      previous_billing?: number
    }[]
  },
): Promise<Invoice> {
  return apiFetch(`/invoices/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteInvoice(id: string): Promise<{ success: boolean }> {
  return apiFetch(`/invoices/${id}`, { method: 'DELETE' })
}

export function generateSheet(
  id: string,
  opts?: { force?: boolean },
): Promise<{ success: boolean; data_path: string }> {
  const qs = opts?.force ? '?force=true' : ''
  return apiFetch(`/invoices/${id}/generate-sheet${qs}`, { method: 'POST' })
}

export function exportPdf(
  id: string,
): Promise<{ success: boolean; pdf_path: string }> {
  return apiFetch(`/invoices/${id}/export-pdf`, { method: 'POST' })
}

export function finalizeInvoice(
  id: string,
): Promise<{ success: boolean; total_due: number; pdf_path: string }> {
  return apiFetch(`/invoices/${id}/finalize`, { method: 'POST' })
}

export function sendInvoice(
  id: string,
): Promise<{ success: boolean; sent_to: string[]; pdf_path: string }> {
  return apiFetch(`/invoices/${id}/send`, { method: 'POST' })
}

export function createNextInvoice(
  id: string,
): Promise<Invoice> {
  return apiFetch(`/invoices/${id}/create-next`, { method: 'POST' })
}
