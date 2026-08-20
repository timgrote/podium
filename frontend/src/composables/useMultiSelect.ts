import { computed, ref } from 'vue'

/**
 * Multi-select behavior for Kanban boards.
 *
 * - A plain click opens/selects a single card and clears any prior group.
 * - Ctrl/Cmd+click toggles a card in/out of the selection without clearing
 *   the rest, so you build up a group across columns.
 * - Shift+click extends the selection to everything between the last-clicked
 *   card and the clicked card (in the board's displayed order).
 * - Exposes the selected id set, toggle/clear/isSelected, and a
 *   `multiSelecting` flag (2+ selected) that drives a group action toolbar.
 *
 * The selection survives board reloads (it's keyed on card ids), so after a
 * bulk "move to status" the group stays selected in its new column.
 */
export function useMultiSelect() {
  const selected = ref<Set<string>>(new Set())
  const lastClicked = ref<string | null>(null)

  /** True when a real multi-selection (2+) is active. */
  const multiSelecting = computed(() => selected.value.size > 1)

  /**
   * Handle a card click. `orderedIds` is the board's current display order of
   * card ids (used to resolve shift-click ranges). Returns true if the event
   * was consumed by selection (caller should NOT navigate/open); false means
   * it was a plain click on a non-multi-select state → caller opens the card.
   */
  function handleClick(
    id: string,
    modifiers: { ctrl?: boolean; meta?: boolean; shift?: boolean },
    orderedIds: string[],
  ): boolean {
    const { ctrl = false, meta = false, shift = false } = modifiers
    const modified = ctrl || meta

    // Shift-click: extend from the last-clicked card to this one.
    if (shift && lastClicked.value) {
      const a = orderedIds.indexOf(lastClicked.value)
      const b = orderedIds.indexOf(id)
      if (a !== -1 && b !== -1) {
        const [lo, hi] = a < b ? [a, b] : [b, a]
        const next = new Set(selected.value)
        for (const rid of orderedIds.slice(lo, hi + 1)) next.add(rid)
        selected.value = next
        lastClicked.value = id
        return true
      }
    }

    if (modified) {
      toggle(id)
      lastClicked.value = id
      return true
    }

    // Plain click while a group is active: clear it and let the caller open
    // the clicked card (acts like a fresh single click).
    if (selected.value.size > 0) {
      selected.value = new Set()
    }
    lastClicked.value = id
    return false
  }

  function toggle(id: string) {
    const next = new Set(selected.value)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    selected.value = next
  }

  function selectOnly(id: string) {
    selected.value = new Set([id])
    lastClicked.value = id
  }

  function clear() {
    selected.value = new Set()
    lastClicked.value = null
  }

  function isSelected(id: string): boolean {
    return selected.value.has(id)
  }

  return {
    selected,
    multiSelecting,
    handleClick,
    toggle,
    selectOnly,
    clear,
    isSelected,
  }
}
