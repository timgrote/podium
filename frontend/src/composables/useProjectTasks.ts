import { computed, ref, type Ref } from 'vue'
import type { Task } from '../types'

type SortField = 'title' | 'due_date' | 'assignee' | 'priority'

export function useProjectTasks(activeTasks: Ref<Task[]>) {
  const searchQuery = ref('')
  const sortField = ref<SortField | null>(null)
  const sortOrder = ref<'asc' | 'desc'>('asc')

  function toggleSort(field: SortField) {
    if (sortField.value === field) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortField.value = field
      sortOrder.value = field === 'due_date' || field === 'priority' ? 'desc' : 'asc'
    }
  }

  const filteredTasks = computed(() => {
    let result = activeTasks.value

    // Search filter
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      result = result.filter((t) => {
        if (t.title.toLowerCase().includes(q)) return true
        if (t.assignees?.some(a =>
          (a.first_name || '').toLowerCase().includes(q) ||
          (a.last_name || '').toLowerCase().includes(q)
        )) return true
        return false
      })
    }

    // Sort
    if (sortField.value) {
      const field = sortField.value
      const order = sortOrder.value === 'asc' ? 1 : -1
      result = [...result].sort((a, b) => {
        if (field === 'title') {
          return a.title.localeCompare(b.title) * order
        }
        if (field === 'due_date') {
          const aVal = a.due_date
          const bVal = b.due_date
          if (aVal == null && bVal == null) return 0
          if (aVal == null) return 1
          if (bVal == null) return -1
          return (new Date(aVal).getTime() - new Date(bVal).getTime()) * order
        }
        if (field === 'priority') {
          const aVal = a.priority ?? 0
          const bVal = b.priority ?? 0
          return (aVal - bVal) * order
        }
        if (field === 'assignee') {
          const aName = a.assignees?.[0]?.first_name || null
          const bName = b.assignees?.[0]?.first_name || null
          if (aName == null && bName == null) return 0
          if (aName == null) return 1
          if (bName == null) return -1
          return aName.localeCompare(bName) * order
        }
        return 0
      })
    }

    return result
  })

  return {
    searchQuery,
    sortField,
    sortOrder,
    toggleSort,
    filteredTasks,
  }
}
