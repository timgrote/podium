import { ref, watch } from 'vue'
import { getUserSettings, updateUserSettings } from '../api/auth'

/**
 * Persistent Board/List view mode.
 *
 * Stores the user's choice so a page renders the same view every time:
 * - localStorage for instant, per-browser persistence (survives reloads, no
 *   flash of the wrong view).
 * - The per-user settings API (user_settings table) so the preference follows
 *   the user across devices/browsers.
 *
 * The component just calls `usePersistentViewMode('projects')` and uses the
 * returned ref like its old `viewMode`. Reading is async (settings come from
 * the server), so the returned ref starts at `fallback` (list) and updates to
 * the saved value once settings load — the localStorage read is synchronous
 * and applied first to avoid a flash.
 */
export function usePersistentViewMode(key: string, fallback: 'list' | 'board' | 'kanban') {
  const storageKey = `conductor.viewmode.${key}`
  const settingsKey = `view_mode_${key}`

  const mode = ref<'list' | 'board' | 'kanban'>(fallback)

  // Instant local restore (synchronous) to avoid flashing the wrong view.
  const local = localStorage.getItem(storageKey)
  const hasLocalPreference = local === 'list' || local === 'board' || local === 'kanban'
  if (hasLocalPreference) {
    mode.value = local
  }

  // Persist locally on change immediately; push to server settings (debounced).
  let saveTimer: ReturnType<typeof setTimeout> | undefined
  watch(mode, (value) => {
    localStorage.setItem(storageKey, value)
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      updateUserSettings({ [settingsKey]: value }).catch(() => {})
    }, 400)
  })

  // A local choice is the freshest value for this browser. Only hydrate from
  // the server when this browser has no saved preference; otherwise an older
  // server value can flip Board back to List while navigating between pages.
  getUserSettings()
    .then((settings) => {
      const saved = settings[settingsKey]
      if (!hasLocalPreference && (saved === 'list' || saved === 'board' || saved === 'kanban')) {
        mode.value = saved
      }
    })
    .catch(() => {})

  return mode
}
