import { ref, watch } from 'vue'
import { getUserSettings, updateUserSettings } from '../api/auth'

/**
 * The employee scope selected on the cross-project Tasks page.
 *
 * Values are 'me', 'everyone', or an employee id. Store the selection both
 * locally (instant restore) and in the user's settings (cross-device restore).
 */
export function usePersistentTaskAssignee() {
  const storageKey = 'conductor.tasks.assignee'
  const settingsKey = 'tasks_assignee_filter'
  const local = localStorage.getItem(storageKey)
  const hasLocalPreference = Boolean(local)
  const assignee = ref(local || 'me')

  let saveTimer: ReturnType<typeof setTimeout> | undefined
  watch(assignee, (value) => {
    localStorage.setItem(storageKey, value)
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      updateUserSettings({ [settingsKey]: value }).catch(() => {})
    }, 400)
  })

  getUserSettings()
    .then((settings) => {
      const saved = settings[settingsKey]
      if (!hasLocalPreference && saved) assignee.value = saved
    })
    .catch(() => {})

  return assignee
}
