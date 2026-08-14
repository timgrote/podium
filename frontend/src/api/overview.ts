import { apiFetch } from './client'

export interface OverviewAssignee {
  id: string
  first_name: string
  last_name: string
}

export interface OverviewTask {
  id: string
  kind: 'task'
  title: string
  status: string
  priority: number | null
  due_date: string | null
  project_id: string
  project_name: string
  client_id: string | null
  client_name: string | null
  assignees: OverviewAssignee[]
}

export interface OverviewDeliverable {
  id: string
  kind: 'deliverable'
  title: string
  status: string
  progress_percent: number
  deadline: string | null
  project_id: string
  project_name: string
  client_id: string | null
  client_name: string | null
}

export interface OverviewItems {
  tasks: OverviewTask[]
  deliverables: OverviewDeliverable[]
}

export function getOverviewItems(projectIds: string[]): Promise<OverviewItems> {
  const qs = new URLSearchParams({ project_ids: projectIds.join(',') })
  return apiFetch(`/overview/items?${qs}`)
}
