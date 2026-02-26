import type { Task, MyTask, TaskCreatePayload, TaskUpdatePayload, TaskNote } from '../types'
import { apiFetch } from './client'

export function getMyTasks(employeeId: string): Promise<MyTask[]> {
  return apiFetch(`/tasks/my?employee_id=${encodeURIComponent(employeeId)}`)
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

export function deleteTaskNote(noteId: string): Promise<void> {
  return apiFetch(`/tasks/notes/${noteId}`, { method: 'DELETE' })
}

export async function uploadImage(file: File): Promise<{ url: string }> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch('/uploads/images', { method: 'POST', body: form })
}
