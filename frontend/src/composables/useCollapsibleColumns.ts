import { ref } from 'vue'

/**
 * Collapsible-column behavior for Kanban boards (mirrors the Hermes desktop
 * board): an empty column collapses to a thin vertical strip that gets out of
 * the way, and clicking it expands it (so you can drop cards into it).
 *
 * A column is collapsed when it has zero cards AND hasn't been explicitly
 * expanded this session. Expanding is sticky per column status so a user can
 * keep an empty column open if they're about to drop into it.
 */
export function useCollapsibleColumns() {
  const expanded = ref<Set<string>>(new Set())

  /** A column with no cards collapses unless the user explicitly expanded it. */
  function isCollapsed(status: string, count: number): boolean {
    return count === 0 && !expanded.value.has(status)
  }

  function toggleColumn(status: string) {
    const next = new Set(expanded.value)
    if (next.has(status)) next.delete(status)
    else next.add(status)
    expanded.value = next
  }

  function expandColumn(status: string) {
    if (!expanded.value.has(status)) {
      const next = new Set(expanded.value)
      next.add(status)
      expanded.value = next
    }
  }

  return { isCollapsed, toggleColumn, expandColumn }
}
