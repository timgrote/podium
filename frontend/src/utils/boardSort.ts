/**
 * Pure board sorting/filtering helpers shared by the Kanban board components.
 *
 * These are intentionally free of any DOM/API dependency so they can be unit
 * tested in isolation (see __tests__/boardSort.test.ts).
 */
import type { KanbanCard, KanbanTaskCard } from '../types'

/**
 * Sort keys for the project board. Each is a "view" applied to a column —
 * it never mutates stored order (board_order / sort_order), so dragging still
 * works off the persisted positions.
 */
export type ProjectSortKey =
  | 'manual' // board_order (persisted position) — the default
  | 'name' // project name, A→Z
  | 'deadline' // earliest next_task_deadline first (most urgent)
  | 'outstanding' // most $ outstanding first
  | 'activity' // most recently updated first

export const PROJECT_SORT_OPTIONS: { key: ProjectSortKey; label: string }[] = [
  { key: 'manual', label: 'Manual order' },
  { key: 'name', label: 'Name (A–Z)' },
  { key: 'deadline', label: 'Most urgent deadline' },
  { key: 'outstanding', label: 'Most $ outstanding' },
  { key: 'activity', label: 'Recently updated' },
]

/** Compare ISO/local date strings, nulls sorting to the end. */
function compareDateString(a: string | null, b: string | null): number {
  if (a === null && b === null) return 0
  if (a === null) return 1 // null goes after any real date
  if (b === null) return -1
  return a.localeCompare(b)
}

export function sortProjects(cards: KanbanCard[], key: ProjectSortKey): KanbanCard[] {
  const copy = [...cards]
  switch (key) {
    case 'name':
      return copy.sort((a, b) => (a.project_name ?? '').localeCompare(b.project_name ?? ''))
    case 'deadline':
      return copy.sort(
        (a, b) =>
          compareDateString(a.next_task_deadline, b.next_task_deadline) ||
          (a.board_order - b.board_order),
      )
    case 'outstanding':
      return copy.sort((a, b) => b.total_outstanding - a.total_outstanding)
    case 'activity':
      return copy.sort((a, b) => {
        const ad = a.last_activity ?? ''
        const bd = b.last_activity ?? ''
        // Nulls always sink to the bottom; real dates sort newest-first.
        if (!ad && !bd) return a.board_order - b.board_order
        if (!ad) return 1
        if (!bd) return -1
        return bd.localeCompare(ad) || (a.board_order - b.board_order)
      })
    case 'manual':
    default:
      return copy.sort((a, b) => a.board_order - b.board_order)
  }
}

/**
 * Sort keys for the task board columns. Applied per-column as a view; does not
 * change the persisted sort_order used for drag-and-drop.
 */
export type TaskSortKey =
  | 'manual' // is_pinned first, then sort_order — the default
  | 'priority' // highest priority first
  | 'due' // earliest due_date first (most urgent)
  | 'title' // title, A→Z

export const TASK_SORT_OPTIONS: { key: TaskSortKey; label: string }[] = [
  { key: 'manual', label: 'Manual order' },
  { key: 'priority', label: 'Priority (high → low)' },
  { key: 'due', label: 'Due date (soonest)' },
  { key: 'title', label: 'Title (A–Z)' },
]

export function sortTasks(cards: KanbanTaskCard[], key: TaskSortKey): KanbanTaskCard[] {
  const copy = [...cards]
  switch (key) {
    case 'priority':
      return copy.sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0))
    case 'due':
      return copy.sort(
        (a, b) => compareDateString(a.due_date, b.due_date) || (a.sort_order - b.sort_order),
      )
    case 'title':
      return copy.sort((a, b) => (a.title ?? '').localeCompare(b.title ?? ''))
    case 'manual':
    default:
      // Pinned always float to the top, then persisted position.
      return copy.sort((a, b) => {
        if (!!a.is_pinned !== !!b.is_pinned) return a.is_pinned ? -1 : 1
        return a.sort_order - b.sort_order
      })
  }
}

/**
 * Case-insensitive filter over a card's key text fields. Used for the board
 * search box.
 */
export function projectMatchesSearch(card: KanbanCard, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  const haystack = [
    card.project_name,
    card.project_number,
    card.job_code,
    card.client_name,
    card.pm_name,
    card.location,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return haystack.includes(q)
}
