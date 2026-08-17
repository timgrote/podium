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

export interface TaskBoardColumn {
  status: TaskStatus
  label: string
  tasks: Task[]
}

/**
 * Group tasks into board columns, one per canonical status in column order.
 * Unknown statuses are collected into a trailing "Other" column so no task is
 * ever hidden. Assumes input is already in board sort order (listTasks output).
 */
export function groupTasksByStatus(tasks: Task[]): TaskBoardColumn[] {
  const cols: TaskBoardColumn[] = TASK_STATUSES.map((status) => ({
    status,
    label: TASK_STATUS_LABELS[status],
    tasks: [],
  }))

  for (const t of tasks) {
    const col = cols.find((c) => c.status === t.status)
    if (col) col.tasks.push(t)
  }

  const unknown = tasks.filter((t) => !isTaskStatus(t.status))
  if (unknown.length) {
    cols.push({ status: 'canceled' as TaskStatus, label: 'Other', tasks: unknown })
  }

  return cols
}

/**
 * Return a new array with the task moved to `targetStatus` at `targetIndex`
 * (index within the destination column's remaining tasks — the dragged task is
 * removed first, then inserted). The moved task's `status` is updated to the
 * target so grouping reflects the new column. Pure: never mutates the input
 * array or its tasks. targetIndex is clamped to the column bounds.
 */
export function reorderTasksForBoard(
  tasks: Task[],
  taskId: string,
  targetStatus: TaskStatus,
  targetIndex: number,
): Task[] {
  const task = tasks.find((t) => t.id === taskId)
  if (!task) return tasks

  const groups: Task[][] = TASK_STATUSES.map(() => [])
  const unknown: Task[] = []
  for (const t of tasks) {
    if (t.id === taskId) continue
    const i = TASK_STATUSES.indexOf(t.status as TaskStatus)
    if (i >= 0) groups[i]!.push(t)
    else unknown.push(t)
  }

  const destIndex = TASK_STATUSES.indexOf(targetStatus)
  const dest = destIndex >= 0 ? groups[destIndex]! : unknown
  const clamped = Math.max(0, Math.min(targetIndex, dest.length))
  dest.splice(clamped, 0, { ...task, status: targetStatus })

  return [...groups.flat(), ...unknown]
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
