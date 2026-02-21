import type { Contract } from '../types'
import { apiFetch } from './client'

export function getContract(id: string): Promise<Contract> {
  return apiFetch(`/contracts/${id}`)
}

export function createContract(data: {
  project_id: string
  total_amount?: number
  signed_at?: string
  file_path?: string
  notes?: string
  tasks?: { name: string; description?: string; amount?: number }[]
}): Promise<Contract> {
  return apiFetch('/contracts', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateContract(
  id: string,
  data: {
    signed_at?: string
    file_path?: string
    notes?: string
    tasks?: {
      name: string
      description?: string
      amount?: number
    }[]
  },
): Promise<Contract> {
  return apiFetch(`/contracts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteContract(id: string): Promise<{ success: boolean }> {
  return apiFetch(`/contracts/${id}`, { method: 'DELETE' })
}

export function addContractTask(
  contractId: string,
  data: { name: string; description?: string; amount?: number },
): Promise<Contract> {
  return apiFetch(`/contracts/${contractId}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateContractTask(
  contractId: string,
  taskId: string,
  data: Record<string, unknown>,
): Promise<Contract> {
  return apiFetch(`/contracts/${contractId}/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteContractTask(
  contractId: string,
  taskId: string,
): Promise<{ success: boolean }> {
  return apiFetch(`/contracts/${contractId}/tasks/${taskId}`, {
    method: 'DELETE',
  })
}

export function createInvoiceFromContract(
  contractId: string,
  data: {
    tasks: { task_id: string; percent_this_invoice: number }[]
    pm_email?: string
    invoice_number?: string
  },
): Promise<Record<string, unknown>> {
  return apiFetch(`/contracts/${contractId}/invoices`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
