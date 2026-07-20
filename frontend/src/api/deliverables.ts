import type { Deliverable } from '../types'
import { apiFetch } from './client'

export function getDeliverables(projectId: string): Promise<Deliverable[]> {
  return apiFetch(`/projects/${projectId}/deliverables`)
}

export function createDeliverable(
  projectId: string,
  data: {
    name: string
    contract_task_id?: string
    sort_order?: number
    status?: string
    progress_percent?: number
    deadline?: string
  },
): Promise<Deliverable> {
  return apiFetch(`/projects/${projectId}/deliverables`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateDeliverable(
  id: string,
  data: {
    name?: string
    contract_task_id?: string
    sort_order?: number
    status?: string
    progress_percent?: number
    deadline?: string
  },
): Promise<Deliverable> {
  return apiFetch(`/deliverables/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteDeliverable(id: string): Promise<{ success: boolean }> {
  return apiFetch(`/deliverables/${id}`, { method: 'DELETE' })
}
