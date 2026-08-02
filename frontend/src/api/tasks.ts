import type { Task, MyTask, TaskCreatePayload, TaskUpdatePayload, TaskNote } from '../types'
import { apiFetch } from './client'

export interface MyTaskFilters {
  due_before?: string
  due_after?: string
  stale?: boolean
  status?: string
  no_due_date?: boolean
  assignee_ids?: string[]
  tags?: string[]
}

export function getMyTasks(employeeId: string, filters?: MyTaskFilters): Promise<MyTask[]> {
  const params = new URLSearchParams({ employee_id: employeeId })
  if (filters?.due_before) params.set('due_before', filters.due_before)
  if (filters?.due_after) params.set('due_after', filters.due_after)
  if (filters?.stale) params.set('stale', 'true')
  if (filters?.status) params.set('status', filters.status)
  if (filters?.no_due_date) params.set('no_due_date', 'true')
  if (filters?.assignee_ids?.length) params.set('assignee_ids', filters.assignee_ids.join(','))
  if (filters?.tags?.length) params.set('tags', filters.tags.join(','))
  return apiFetch(`/tasks/my?${params.toString()}`)
}

export function getDoneToday(employeeId: string, today: string): Promise<MyTask[]> {
  const params = new URLSearchParams({ employee_id: employeeId, today })
  return apiFetch(`/tasks/done-today?${params.toString()}`)
}

export interface BulkPatchFields {
  due_date?: string | null
  status?: string
  assignee_ids?: string[]
  priority?: number | null
  is_pinned?: boolean
  tags?: string[]
  add_tags?: string[]
}

export function bulkUpdateTasks(taskIds: string[], patch: BulkPatchFields): Promise<MyTask[]> {
  return apiFetch('/tasks/bulk', {
    method: 'PATCH',
    body: JSON.stringify({ task_ids: taskIds, patch }),
  })
}

export function bulkDeleteTasks(taskIds: string[]): Promise<{ success: boolean; deleted_count: number }> {
  return apiFetch('/tasks/bulk', {
    method: 'DELETE',
    body: JSON.stringify({ task_ids: taskIds }),
  })
}

export function getTags(): Promise<string[]> {
  return apiFetch('/tasks/tags')
}

export function reorderTasks(items: { task_id: string; sort_order: number }[]): Promise<{ success: boolean }> {
  return apiFetch('/tasks/reorder', {
    method: 'PATCH',
    body: JSON.stringify({ items }),
  })
}

export function getProjectTasks(projectId: string): Promise<Task[]> {
  return apiFetch(`/projects/${projectId}/tasks`)
}

export function getTask(taskId: string): Promise<Task> {
  return apiFetch(`/tasks/${taskId}`)
}

export function createTask(projectId: string, data: TaskCreatePayload): Promise<Task> {
  return apiFetch(`/projects/${projectId}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateTask(taskId: string, data: TaskUpdatePayload): Promise<Task> {
  return apiFetch(`/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteTask(taskId: string): Promise<void> {
  return apiFetch(`/tasks/${taskId}`, { method: 'DELETE' })
}

export function addTaskNote(taskId: string, data: { content: string; author_id?: string | null }): Promise<TaskNote> {
  return apiFetch(`/tasks/${taskId}/notes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateTaskNote(noteId: string, data: { content: string }): Promise<TaskNote> {
  return apiFetch(`/tasks/notes/${noteId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteTaskNote(noteId: string): Promise<void> {
  return apiFetch(`/tasks/notes/${noteId}`, { method: 'DELETE' })
}

export async function uploadImage(file: File): Promise<{ url: string }> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch('/uploads/images', { method: 'POST', body: form })
}
