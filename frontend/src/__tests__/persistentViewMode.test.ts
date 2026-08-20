import { afterEach, describe, expect, it, vi } from 'vitest'

const { getUserSettings, updateUserSettings } = vi.hoisted(() => ({
  getUserSettings: vi.fn(),
  updateUserSettings: vi.fn(),
}))

vi.mock('../api/auth', () => ({ getUserSettings, updateUserSettings }))

import { usePersistentViewMode } from '../composables/usePersistentViewMode'

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

describe('usePersistentViewMode', () => {
  it('keeps this browser’s saved mode when the server still has an older mode', async () => {
    installStorage({ 'conductor.viewmode.my_tasks': 'kanban' })
    getUserSettings.mockResolvedValue({ view_mode_my_tasks: 'list' })

    const mode = usePersistentViewMode('my_tasks', 'list')
    await Promise.resolve()

    expect(mode.value).toBe('kanban')
  })
})
