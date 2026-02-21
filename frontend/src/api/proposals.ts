import type { Proposal } from '../types'
import { apiFetch } from './client'

export function getProposals(params?: {
  project_id?: string
  status?: string
}): Promise<Proposal[]> {
  const query = new URLSearchParams()
  if (params?.project_id) query.set('project_id', params.project_id)
  if (params?.status) query.set('status', params.status)
  const qs = query.toString()
  return apiFetch(`/proposals${qs ? `?${qs}` : ''}`)
}

export function getProposal(id: string): Promise<Proposal> {
  return apiFetch(`/proposals/${id}`)
}

export function createProposal(data: {
  project_id: string
  client_company?: string
  client_contact_email?: string
  total_fee?: number
  engineer_key?: string
  engineer_name?: string
  engineer_title?: string
  contact_method?: string
  proposal_date?: string
  status?: string
  tasks?: { name: string; description?: string; amount?: number }[]
}): Promise<Proposal> {
  return apiFetch('/proposals', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateProposal(
  id: string,
  data: Record<string, unknown>,
): Promise<Proposal> {
  return apiFetch(`/proposals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteProposal(id: string): Promise<{ success: boolean }> {
  return apiFetch(`/proposals/${id}`, { method: 'DELETE' })
}

export function getProposalDefaults(): Promise<{
  tasks: { name: string; description?: string; amount: number }[]
  changes_task: { name: string; description?: string; amount: number }
  engineers: Record<string, { name: string; title: string }>
  rates: Record<string, unknown>
}> {
  return apiFetch('/proposals/defaults')
}

export function generateDoc(id: string): Promise<Proposal> {
  return apiFetch(`/proposals/${id}/generate-doc`, { method: 'POST' })
}

export function exportProposalPdf(id: string): Promise<Proposal> {
  return apiFetch(`/proposals/${id}/export-pdf`, { method: 'POST' })
}

export function sendProposal(id: string): Promise<Proposal & { sent_to: string[] }> {
  return apiFetch(`/proposals/${id}/send`, { method: 'POST' })
}

export function addProposalTask(
  proposalId: string,
  data: { name: string; description?: string; amount?: number },
): Promise<Proposal> {
  return apiFetch(`/proposals/${proposalId}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateProposalTask(
  proposalId: string,
  taskId: string,
  data: Record<string, unknown>,
): Promise<Proposal> {
  return apiFetch(`/proposals/${proposalId}/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteProposalTask(
  proposalId: string,
  taskId: string,
): Promise<{ success: boolean }> {
  return apiFetch(`/proposals/${proposalId}/tasks/${taskId}`, {
    method: 'DELETE',
  })
}

export function promoteToContract(
  proposalId: string,
  data?: { signed_at?: string; file_path?: string },
): Promise<Record<string, unknown>> {
  const params = new URLSearchParams()
  if (data?.signed_at) params.set('signed_at', data.signed_at)
  if (data?.file_path) params.set('file_path', data.file_path)
  const qs = params.toString()
  return apiFetch(`/proposals/${proposalId}/promote${qs ? `?${qs}` : ''}`, {
    method: 'POST',
  })
}
