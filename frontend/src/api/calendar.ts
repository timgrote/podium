import { apiFetch } from './client'

export interface CalendarAssignee {
  id: string
  first_name: string
  last_name: string
}

export interface CalendarItem {
  id: string
  kind: 'task' | 'deliverable'
  title: string
  date: string
  priority: number | null
  status: string
  progress_percent?: number
  project_id: string
  project_name: string | null
  client_id: string | null
  client_name: string | null
  assignees: CalendarAssignee[]
}

export interface CalendarFilters {
  from?: string
  to?: string
}

export function getCalendar(filters?: CalendarFilters): Promise<CalendarItem[]> {
  const params = new URLSearchParams()
  if (filters?.from) params.set('from_date', filters.from)
  if (filters?.to) params.set('to_date', filters.to)
  const qs = params.toString()
  return apiFetch(`/calendar${qs ? `?${qs}` : ''}`)
}
