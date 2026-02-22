import type { Task, TaskCreatePayload, TaskUpdatePayload, TaskNote } from '../types'
import { apiFetch } from './client'

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
