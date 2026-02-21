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
const sortField = ref<'id' | 'project_name' | 'status' | 'total_contracted'>('id')
const sortOrder = ref<'asc' | 'desc'>('desc')

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
    result = [...result].sort((a, b) => {
      const aVal = a[field] ?? ''
      const bVal = b[field] ?? ''
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
  }
}
