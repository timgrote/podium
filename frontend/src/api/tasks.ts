import type { Task } from '../types'
import { apiFetch } from './client'

export function getProjectTasks(projectId: string): Promise<Task[]> {
  return apiFetch(`/tasks?project_id=${projectId}`)
}
