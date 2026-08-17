import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Task } from '../types'
import {
  TASK_STATUSES,
  TASK_STATUS_LABELS,
  groupTasksByStatus,
  isTaskStatus,
  listTasks,
  reorderTasksForBoard,
  sortTasksForBoard,
  updateTaskStatus,
  type TaskStatus,
} from '../api/projectTasks'

const apiFetch = vi.fn()
vi.mock('../api/client', () => ({
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}))

function task(overrides: Partial<Task>): Task {
  return {
    id: 'task-x',
    project_id: 'proj-x',
    parent_id: null,
    title: 't',
    description: null,
    status: 'todo',
    priority: null,
    start_date: null,
    due_date: null,
    sort_order: 0,
    created_by: null,
    completed_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
    is_pinned: false,
    tags: [],
    assignees: [],
    notes: [],
    subtasks: [],
    ...overrides,
  }
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('status values', () => {
  it('matches the canonical column set used by the backend', () => {
    expect(TASK_STATUSES).toEqual(['triage', 'todo', 'in_progress', 'blocked', 'done', 'canceled'])
  })

  it('defines a human label for every status', () => {
    for (const s of TASK_STATUSES) {
      expect(TASK_STATUS_LABELS[s]).toBeTruthy()
    }
  })

  it('isTaskStatus guards and narrows correctly', () => {
    expect(isTaskStatus('in_progress')).toBe(true)
    expect(isTaskStatus('done')).toBe(true)
    expect(isTaskStatus('archived')).toBe(false)
    expect(isTaskStatus('')).toBe(false)
  })
})

describe('sortTasksForBoard', () => {
  it('orders by status column then sort_order', () => {
    const rows = [
      task({ id: 'a', status: 'done', sort_order: 0 }),
      task({ id: 'b', status: 'todo', sort_order: 1 }),
      task({ id: 'c', status: 'todo', sort_order: 0 }),
      task({ id: 'd', status: 'in_progress', sort_order: 2 }),
    ]
    const sorted = sortTasksForBoard(rows)
    expect(sorted.map((t) => t.id)).toEqual(['c', 'b', 'd', 'a'])
  })

  it('puts pinned tasks before unpinned within a column', () => {
    const rows = [
      task({ id: 'a', status: 'todo', sort_order: 0 }),
      task({ id: 'b', status: 'todo', sort_order: 1, is_pinned: true }),
    ]
    expect(sortTasksForBoard(rows).map((t) => t.id)).toEqual(['b', 'a'])
  })

  it('sorts unknown statuses last without dropping them', () => {
    const rows = [
      task({ id: 'x', status: 'mystery' as TaskStatus, sort_order: 0 }),
      task({ id: 'a', status: 'todo', sort_order: 0 }),
    ]
    expect(sortTasksForBoard(rows).map((t) => t.id)).toEqual(['a', 'x'])
  })

  it('does not mutate the input array', () => {
    const rows = [task({ id: 'a', status: 'done' }), task({ id: 'b', status: 'todo' })]
    const before = rows.map((r) => r.id)
    sortTasksForBoard(rows)
    expect(rows.map((r) => r.id)).toEqual(before)
  })
})

describe('listTasks', () => {
  it('fetches project tasks and returns them sorted', async () => {
    apiFetch.mockResolvedValue([
      task({ id: 'done1', status: 'done', sort_order: 0 }),
      task({ id: 'todo1', status: 'todo', sort_order: 5 }),
      task({ id: 'todo0', status: 'todo', sort_order: 0 }),
    ])
    const rows = await listTasks('proj-1')
    expect(apiFetch).toHaveBeenCalledWith('/projects/proj-1/tasks')
    expect(rows.map((t) => t.id)).toEqual(['todo0', 'todo1', 'done1'])
  })
})

describe('groupTasksByStatus', () => {
  it('produces one column per canonical status in column order', () => {
    const cols = groupTasksByStatus([])
    expect(cols.map((c) => c.status)).toEqual(TASK_STATUSES)
    expect(cols.map((c) => c.label)).toEqual(['Triage', 'To Do', 'In Progress', 'Blocked', 'Done', 'Canceled'])
    expect(cols.every((c) => c.tasks.length === 0)).toBe(true)
  })

  it('places tasks into their status column, preserving input order', () => {
    const rows = [
      task({ id: 't1', status: 'todo', sort_order: 0 }),
      task({ id: 't2', status: 'done', sort_order: 1 }),
      task({ id: 't3', status: 'todo', sort_order: 1 }),
    ]
    const cols = groupTasksByStatus(rows)
    const todo = cols.find((c) => c.status === 'todo')!
    const done = cols.find((c) => c.status === 'done')!
    expect(todo.tasks.map((t) => t.id)).toEqual(['t1', 't3'])
    expect(done.tasks.map((t) => t.id)).toEqual(['t2'])
  })

  it('collects unknown statuses into a trailing Other column', () => {
    const rows = [
      task({ id: 'a', status: 'todo', sort_order: 0 }),
      task({ id: 'b', status: 'mystery' as TaskStatus, sort_order: 0 }),
    ]
    const cols = groupTasksByStatus(rows)
    expect(cols.length).toBe(TASK_STATUSES.length + 1)
    const other = cols[cols.length - 1]!
    expect(other.label).toBe('Other')
    expect(other.tasks.map((t) => t.id)).toEqual(['b'])
  })
})

describe('reorderTasksForBoard', () => {
  it('moves a task to another column, updating its status', () => {
    const rows = [
      task({ id: 'a', status: 'todo', sort_order: 0 }),
      task({ id: 'b', status: 'in_progress', sort_order: 0 }),
    ]
    const out = reorderTasksForBoard(rows, 'a', 'done', 0)
    expect(out.map((t) => t.id)).toEqual(['b', 'a'])
    expect(out.find((t) => t.id === 'a')!.status).toBe('done')
  })

  it('reorders within the same column by index', () => {
    const rows = [
      task({ id: 'a', status: 'todo', sort_order: 0 }),
      task({ id: 'b', status: 'todo', sort_order: 1 }),
      task({ id: 'c', status: 'todo', sort_order: 2 }),
    ]
    // Move 'c' before 'a'.
    expect(reorderTasksForBoard(rows, 'c', 'todo', 0).map((t) => t.id)).toEqual(['c', 'a', 'b'])
    // Move 'a' after 'c' (append).
    expect(reorderTasksForBoard(rows, 'a', 'todo', 2).map((t) => t.id)).toEqual(['b', 'c', 'a'])
  })

  it('clamps the target index to the destination column bounds', () => {
    const rows = [task({ id: 'a', status: 'todo' }), task({ id: 'b', status: 'done' })]
    const out = reorderTasksForBoard(rows, 'b', 'todo', 99)
    expect(out.map((t) => t.id)).toEqual(['a', 'b'])
    expect(out.find((t) => t.id === 'b')!.status).toBe('todo')
  })

  it('does not mutate the input array or its tasks', () => {
    const rows = [task({ id: 'a', status: 'todo' }), task({ id: 'b', status: 'in_progress' })]
    const before = rows.map((r) => r.id)
    reorderTasksForBoard(rows, 'a', 'blocked', 0)
    expect(rows.map((r) => r.id)).toEqual(before)
    expect(rows.every((r) => r.status === 'todo' || r.status === 'in_progress')).toBe(true)
  })

  it('returns the input unchanged when the task id is not found', () => {
    const rows = [task({ id: 'a', status: 'todo' })]
    expect(reorderTasksForBoard(rows, 'missing', 'done', 0)).toBe(rows)
  })
})

describe('updateTaskStatus', () => {
  it('persists via the Kanban move endpoint', async () => {
    apiFetch.mockResolvedValue({ columns: [] })
    await updateTaskStatus('proj-1', 'task-9', 'in_progress', 3)
    expect(apiFetch).toHaveBeenCalledWith('/kanban/tasks/move', {
      method: 'POST',
      body: JSON.stringify({ task_id: 'task-9', status: 'in_progress', sort_order: 3 }),
    })
  })

  it('rejects unknown statuses before hitting the API', async () => {
    await expect(
      updateTaskStatus('proj-1', 'task-9', 'nope' as TaskStatus, 0),
    ).rejects.toThrow("Unknown task status 'nope'")
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
