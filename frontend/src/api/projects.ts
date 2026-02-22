import type { ProjectDetail, ProjectNote, ProjectSummary } from '../types'
import { apiFetch } from './client'

export function getProjects(): Promise<ProjectSummary[]> {
  return apiFetch('/projects')
}

export function getProject(id: string): Promise<ProjectDetail> {
  return apiFetch(`/projects/${id}`)
}

export function createProject(data: {
  project_name: string
  job_code?: string
  client_name?: string
  client_email?: string
  client_id?: string
  location?: string
  status?: string
  pm_id?: string
  data_path?: string
  notes?: string
  tasks?: { name: string; description?: string; amount?: number }[]
  contract?: { signed_date?: string; file_path?: string }
}): Promise<ProjectDetail> {
  return apiFetch('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateProject(
  id: string,
  data: Record<string, unknown>,
): Promise<ProjectDetail> {
  return apiFetch(`/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteProject(
  id: string,
  cascade = false,
): Promise<{ success: boolean }> {
  const params = cascade ? '?cascade=true' : ''
  return apiFetch(`/projects/${id}${params}`, { method: 'DELETE' })
}

export function getProjectNotes(projectId: string): Promise<ProjectNote[]> {
  return apiFetch(`/projects/${projectId}/notes`)
}

export function addProjectNote(
  projectId: string,
  data: { content: string; author_id?: string },
): Promise<ProjectNote> {
  return apiFetch(`/projects/${projectId}/notes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function deleteProjectNote(
  noteId: string,
): Promise<{ success: boolean }> {
  return apiFetch(`/projects/notes/${noteId}`, { method: 'DELETE' })
}
