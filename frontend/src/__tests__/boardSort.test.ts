import { describe, expect, it } from 'vitest'
import type { KanbanCard, KanbanTaskCard } from '../types'
import {
  PROJECT_SORT_OPTIONS,
  projectMatchesSearch,
  sortProjects,
  sortTasks,
  TASK_SORT_OPTIONS,
} from '../utils/boardSort'

function card(overrides: Partial<KanbanCard>): KanbanCard {
  return {
    id: 'proj-x',
    project_number: null,
    job_code: null,
    project_name: 'Project',
    status: 'active',
    board_order: 0,
    client_id: null,
    client_name: null,
    pm_name: null,
    pm_avatar_url: null,
    location: null,
    data_path: null,
    next_task_deadline: null,
    last_activity: null,
    total_paid: 0,
    total_outstanding: 0,
    contract_count: 0,
    invoice_count: 0,
    proposal_count: 0,
    ...overrides,
  }
}

function task(overrides: Partial<KanbanTaskCard>): KanbanTaskCard {
  return {
    id: 'task-x',
    title: 'Task',
    status: 'todo',
    sort_order: 0,
    priority: null,
    due_date: null,
    is_pinned: false,
    tags: [],
    parent_id: null,
    project_id: null,
    project_number: null,
    job_code: null,
    project_name: null,
    subtask_count: 0,
    assignee_name: null,
    ...overrides,
  }
}

describe('PROJECT_SORT_OPTIONS', () => {
  it('defaults to manual order as the first option', () => {
    expect(PROJECT_SORT_OPTIONS[0]?.key).toBe('manual')
  })
})

describe('sortProjects', () => {
  it('sorts by name A→Z', () => {
    const rows = [card({ project_name: 'Zulu' }), card({ project_name: 'Alpha' })]
    expect(sortProjects(rows, 'name').map((c) => c.project_name)).toEqual(['Alpha', 'Zulu'])
  })

  it('sorts by earliest deadline first (most urgent), nulls last', () => {
    const rows = [
      card({ project_name: 'no-dl', next_task_deadline: null }),
      card({ project_name: 'late', next_task_deadline: '2026-09-01' }),
      card({ project_name: 'early', next_task_deadline: '2026-08-01' }),
    ]
    expect(sortProjects(rows, 'deadline').map((c) => c.project_name)).toEqual([
      'early',
      'late',
      'no-dl',
    ])
  })

  it('sorts by most $ outstanding first', () => {
    const rows = [
      card({ project_name: 'a', total_outstanding: 100 }),
      card({ project_name: 'b', total_outstanding: 9000 }),
      card({ project_name: 'c', total_outstanding: 0 }),
    ]
    expect(sortProjects(rows, 'outstanding').map((c) => c.project_name)).toEqual(['b', 'a', 'c'])
  })

  it('sorts by most recently active first, nulls last', () => {
    const rows = [
      card({ project_name: 'old', last_activity: '2026-01-01T00:00:00Z' }),
      card({ project_name: 'none', last_activity: null }),
      card({ project_name: 'new', last_activity: '2026-08-01T00:00:00Z' }),
    ]
    expect(sortProjects(rows, 'activity').map((c) => c.project_name)).toEqual(['new', 'old', 'none'])
  })

  it('manual order respects board_order', () => {
    const rows = [
      card({ id: 'b', board_order: 1 }),
      card({ id: 'a', board_order: 0 }),
    ]
    expect(sortProjects(rows, 'manual').map((c) => c.id)).toEqual(['a', 'b'])
  })

  it('does not mutate the input array', () => {
    const rows = [card({ project_name: 'b' }), card({ project_name: 'a' })]
    const before = rows.map((c) => c.id)
    sortProjects(rows, 'name')
    expect(rows.map((c) => c.id)).toEqual(before)
  })
})

describe('TASK_SORT_OPTIONS', () => {
  it('defaults to manual order as the first option', () => {
    expect(TASK_SORT_OPTIONS[0]?.key).toBe('manual')
  })
})

describe('sortTasks', () => {
  it('sorts by priority high→low, unpinned by default', () => {
    const rows = [
      task({ title: 'low', priority: 1 }),
      task({ title: 'high', priority: 5 }),
      task({ title: 'none', priority: null }),
    ]
    expect(sortTasks(rows, 'priority').map((t) => t.title)).toEqual(['high', 'low', 'none'])
  })

  it('sorts by soonest due date first, nulls last', () => {
    const rows = [
      task({ title: 'none', due_date: null }),
      task({ title: 'late', due_date: '2026-09-01' }),
      task({ title: 'early', due_date: '2026-08-01' }),
    ]
    expect(sortTasks(rows, 'due').map((t) => t.title)).toEqual(['early', 'late', 'none'])
  })

  it('sorts by title A→Z', () => {
    const rows = [task({ title: 'Zulu' }), task({ title: 'Alpha' })]
    expect(sortTasks(rows, 'title').map((t) => t.title)).toEqual(['Alpha', 'Zulu'])
  })

  it('manual order floats pinned first then sort_order', () => {
    const rows = [
      task({ id: 'a', is_pinned: false, sort_order: 0 }),
      task({ id: 'b', is_pinned: true, sort_order: 9 }),
      task({ id: 'c', is_pinned: false, sort_order: 1 }),
    ]
    expect(sortTasks(rows, 'manual').map((t) => t.id)).toEqual(['b', 'a', 'c'])
  })
})

describe('projectMatchesSearch', () => {
  it('matches across name, number, job code, client, pm, and location', () => {
    const c = card({
      project_name: 'Silver Peaks',
      project_number: '26-042',
      job_code: 'DRH-SP',
      client_name: 'DR Horton',
      pm_name: 'Tim Grote',
      location: 'Denver, CO',
    })
    expect(projectMatchesSearch(c, 'silver')).toBe(true)
    expect(projectMatchesSearch(c, '26-042')).toBe(true)
    expect(projectMatchesSearch(c, 'horton')).toBe(true)
    expect(projectMatchesSearch(c, 'grote')).toBe(true)
    expect(projectMatchesSearch(c, 'denver')).toBe(true)
    expect(projectMatchesSearch(c, 'xyz')).toBe(false)
  })

  it('empty query matches everything', () => {
    expect(projectMatchesSearch(card({}), '')).toBe(true)
    expect(projectMatchesSearch(card({}), '   ')).toBe(true)
  })
})
