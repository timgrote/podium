import { apiFetch } from './client'

export interface TimeEntry {
  id: string
  employee_id: string
  project_id: string
  contract_task_id: string | null
  hours: number
  date: string
  description: string | null
  employee_name: string | null
  project_name: string | null
  contract_task_name: string | null
  created_at: string | null
  updated_at: string | null
}

export interface TimeEntryCreatePayload {
  employee_id: string
  project_id: string
  contract_task_id?: string | null
  hours: number
  date: string
  description?: string | null
}

export interface TimeSummary {
  total_hours: number
  by_employee: { employee_id: string; employee_name: string; total_hours: number }[]
  by_task: { contract_task_id: string | null; task_name: string | null; total_hours: number }[]
}

export function getTimeEntries(params: {
  employee_id?: string
  project_id?: string
  date_from?: string
  date_to?: string
} = {}): Promise<TimeEntry[]> {
  const qs = new URLSearchParams()
  if (params.employee_id) qs.set('employee_id', params.employee_id)
  if (params.project_id) qs.set('project_id', params.project_id)
  if (params.date_from) qs.set('date_from', params.date_from)
  if (params.date_to) qs.set('date_to', params.date_to)
  const q = qs.toString()
  return apiFetch(`/time-entries${q ? '?' + q : ''}`)
}

export function getTimeSummary(projectId: string): Promise<TimeSummary> {
  return apiFetch(`/time-entries/summary?project_id=${encodeURIComponent(projectId)}`)
}

export function createTimeEntry(data: TimeEntryCreatePayload): Promise<TimeEntry> {
  return apiFetch('/time-entries', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateTimeEntry(id: string, data: Partial<TimeEntryCreatePayload>): Promise<TimeEntry> {
  return apiFetch(`/time-entries/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteTimeEntry(id: string): Promise<void> {
  return apiFetch(`/time-entries/${id}`, { method: 'DELETE' })
}
