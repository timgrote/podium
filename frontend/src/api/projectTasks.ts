/**
 * Project task data access — the single source the project-level Kanban board
 * uses to load a project's tasks and persist status/order changes.
 *
 * Contract (matches `app/routers/kanban.py` TASK_COLUMNS):
 *   status: 'todo' | 'in_progress' | 'blocked' | 'done' | 'canceled'
 *
 * Persistence is delegated to the existing Kanban move endpoint, which sets the
 * task's status, places it at the requested sort position, and reindexes the
 * source + destination columns so `sort_order` stays dense (0..n).
 */
import type { Task } from '../types'
import { apiFetch } from './client'

/** Canonical column order for the project task board. */
export const TASK_STATUSES = ['todo', 'in_progress', 'blocked', 'done', 'canceled'] as const
export type TaskStatus = (typeof TASK_STATUSES)[number]

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  todo: 'To Do',
  in_progress: 'In Progress',
  blocked: 'Blocked',
  done: 'Done',
  canceled: 'Canceled',
}

export function isTaskStatus(value: string): value is TaskStatus {
  return (TASK_STATUSES as readonly string[]).includes(value)
}

const STATUS_INDEX: Record<TaskStatus, number> = {
  todo: 0,
  in_progress: 1,
  blocked: 2,
  done: 3,
  canceled: 4,
}

/**
 * Sort top-level tasks for the board: by status column (canonical order), then
 * pinned-first, then sort_order, then created_at. Unknown statuses sort last so
 * nothing is ever hidden. Pure — exported for unit testing.
 */
export function sortTasksForBoard(tasks: Task[]): Task[] {
  return [...tasks].sort((a, b) => {
    const ia = STATUS_INDEX[a.status as TaskStatus]
    const ib = STATUS_INDEX[b.status as TaskStatus]
    const statusDiff = (ia ?? STATUS_INDEX.canceled + 1) - (ib ?? STATUS_INDEX.canceled + 1)
    if (statusDiff !== 0) return statusDiff
    if (!!a.is_pinned !== !!b.is_pinned) return a.is_pinned ? -1 : 1
    if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
    return (a.created_at ?? '').localeCompare(b.created_at ?? '')
  })
}

/**
 * Load a project's tasks, sorted by status column and position for the board.
 */
export function listTasks(projectId: string): Promise<Task[]> {
  return apiFetch<Task[]>(`/projects/${projectId}/tasks`).then(sortTasksForBoard)
}

/**
 * Persist a task's status and in-column position via the existing Kanban move
 * endpoint. Throws on API failure; the caller owns optimistic-UI rollback.
 */
export async function updateTaskStatus(
  projectId: string,
  taskId: string,
  newStatus: TaskStatus,
  newPosition: number,
): Promise<void> {
  if (!isTaskStatus(newStatus)) {
    throw new Error(`Unknown task status '${newStatus}'`)
  }
  if (!projectId) {
    throw new Error('projectId is required')
  }
  // The move endpoint is keyed on task_id; the board is project-scoped and only
  // drags tasks belonging to this project, so no project-level check is needed
  // server-side. projectId is kept as part of the contract.
  await apiFetch('/kanban/tasks/move', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId, status: newStatus, sort_order: newPosition }),
  })
}
