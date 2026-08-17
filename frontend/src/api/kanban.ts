import type { KanbanBoard, KanbanTaskBoard } from '../types'
import { apiFetch } from './client'

export function getBoard(): Promise<KanbanBoard> {
  return apiFetch('/kanban')
}

export function moveCard(data: {
  project_id: string
  status: string
  board_order: number
}): Promise<KanbanBoard> {
  return apiFetch('/kanban/move', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getTaskBoard(assignee?: string): Promise<KanbanTaskBoard> {
  const qs = assignee ? `?assignee=${encodeURIComponent(assignee)}` : ''
  return apiFetch(`/kanban/tasks${qs}`)
}

export function moveTaskCard(data: {
  task_id: string
  status: string
  sort_order: number
}): Promise<KanbanTaskBoard> {
  return apiFetch('/kanban/tasks/move', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
