import { computed, ref } from 'vue'
import type { ProjectSummary } from '../types'
import { getProjects } from '../api/projects'

const projects = ref<ProjectSummary[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref('')
const pmFilter = ref('')
const clientFilter = ref('')
const sortField = ref<'next_task_deadline' | 'project_name' | 'client_name' | 'status' | 'last_activity' | 'job_code' | 'total_contracted' | 'total_invoiced' | 'total_outstanding' | 'id'>('next_task_deadline')
const sortOrder = ref<'asc' | 'desc'>('asc')

export function useProjects() {
  async function load() {
    loading.value = true
    error.value = null
    try {
      projects.value = await getProjects()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load projects'
      console.error('Failed to load projects:', e)
    } finally {
      loading.value = false
    }
  }

  const filtered = computed(() => {
    let result = projects.value

    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      result = result.filter(
        (p) =>
          (p.job_code || '').toLowerCase().includes(q) ||
          (p.project_name || '').toLowerCase().includes(q) ||
          (p.client_name || '').toLowerCase().includes(q) ||
          (p.location || '').toLowerCase().includes(q),
      )
    }

    if (statusFilter.value) {
      result = result.filter((p) => p.status === statusFilter.value)
    }

    if (pmFilter.value) {
      result = result.filter((p) => p.pm_name === pmFilter.value)
    }

    if (clientFilter.value) {
      result = result.filter((p) => p.client_id === clientFilter.value)
    }

    const field = sortField.value
    const order = sortOrder.value === 'asc' ? 1 : -1
    const isDateField = field === 'next_task_deadline' || field === 'last_activity'
    result = [...result].sort((a, b) => {
      const aVal = a[field]
      const bVal = b[field]
      // Null-last: projects without values sort to end regardless of order
      if (aVal == null && bVal == null) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1
      if (isDateField) {
        return (new Date(aVal).getTime() - new Date(bVal).getTime()) * order
      }
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return (aVal - bVal) * order
      }
      return String(aVal).localeCompare(String(bVal)) * order
    })

    return result
  })

  const stats = computed(() => {
    const all = projects.value
    return {
      totalProjects: all.length,
      totalInvoiced: all.reduce((sum, p) => sum + (p.total_invoiced || 0), 0),
      totalPaid: all.reduce((sum, p) => sum + (p.total_paid || 0), 0),
      totalOutstanding: all.reduce(
        (sum, p) => sum + (p.total_outstanding || 0),
        0,
      ),
    }
  })

  const uniquePMs = computed(() => {
    const pms = new Set<string>()
    projects.value.forEach((p) => {
      if (p.pm_name) pms.add(p.pm_name)
    })
    return [...pms].sort()
  })

  const uniqueStatuses = computed(() => {
    const statuses = new Set<string>()
    projects.value.forEach((p) => statuses.add(p.status))
    return [...statuses].sort()
  })

  function toggleSort(field: string) {
    if (sortField.value === field) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortField.value = field as typeof sortField.value
      const descFirst = ['next_task_deadline', 'last_activity', 'total_contracted', 'total_invoiced', 'total_outstanding']
      sortOrder.value = descFirst.includes(field) ? 'desc' : 'asc'
    }
  }

  return {
    projects,
    loading,
    error,
    searchQuery,
    statusFilter,
    pmFilter,
    clientFilter,
    sortField,
    sortOrder,
    filtered,
    stats,
    uniquePMs,
    uniqueStatuses,
    load,
    toggleSort,
  }
}
