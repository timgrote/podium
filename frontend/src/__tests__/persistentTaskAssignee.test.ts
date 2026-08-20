import { afterEach, describe, expect, it, vi } from 'vitest'

const { getUserSettings, updateUserSettings } = vi.hoisted(() => ({
  getUserSettings: vi.fn(),
  updateUserSettings: vi.fn(),
}))

vi.mock('../api/auth', () => ({ getUserSettings, updateUserSettings }))

import { usePersistentTaskAssignee } from '../composables/usePersistentTaskAssignee'

function installStorage(initial: Record<string, string> = {}) {
  const values = new Map(Object.entries(initial))
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear(),
    },
  })
}

afterEach(() => {
  vi.clearAllMocks()
  vi.useRealTimers()
})

describe('usePersistentTaskAssignee', () => {
  it('restores the selected employee from this browser instead of an older server value', async () => {
    installStorage({ 'conductor.tasks.assignee': 'emp-matara' })
    getUserSettings.mockResolvedValue({ tasks_assignee_filter: 'me' })

    const assignee = usePersistentTaskAssignee()
    await Promise.resolve()

    expect(assignee.value).toBe('emp-matara')
  })

  it('uses the per-user server setting when this browser has no saved choice', async () => {
    installStorage()
    getUserSettings.mockResolvedValue({ tasks_assignee_filter: 'emp-teva' })

    const assignee = usePersistentTaskAssignee()
    await Promise.resolve()

    expect(assignee.value).toBe('emp-teva')
  })
})
