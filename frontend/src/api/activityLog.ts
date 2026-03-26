import { apiFetch } from './client'

export interface ActivityItem {
  id: string
  source: 'loki' | 'github' | 'conductor'
  timestamp: string
  employee_id: string
  description: string
  detail: string | null
  duration_minutes: number | null
  project_id: string | null
  project_name: string | null
  source_path: string | null
  mapping_source: 'auto' | 'manual' | 'dismissed' | null
}

export interface PathMapping {
  id: string
  pattern: string
  source: string
  project_id: string
  project_name?: string
  created_at: string
}

export function getActivityLog(params: {
  employee_id: string
  date_from: string
  date_to: string
}): Promise<ActivityItem[]> {
  const qs = new URLSearchParams()
  qs.set('employee_id', params.employee_id)
  qs.set('date_from', params.date_from)
  qs.set('date_to', params.date_to)
  return apiFetch(`/activity-log?${qs}`)
}

export function getPathMappings(): Promise<PathMapping[]> {
  return apiFetch('/activity-log/mappings')
}

export function createPathMapping(data: {
  pattern: string
  source: string
  project_id: string
}): Promise<PathMapping> {
  return apiFetch('/activity-log/mappings', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function deletePathMapping(id: string): Promise<void> {
  return apiFetch(`/activity-log/mappings/${id}`, { method: 'DELETE' })
}

export function createOverride(data: {
  source: string
  source_key: string
  employee_id: string
  project_id: string
  remember?: boolean
  pattern?: string
}): Promise<void> {
  return apiFetch('/activity-log/overrides', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
