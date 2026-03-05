import { computed, ref } from 'vue'
import type { InvoiceListItem } from '../types'
import { getInvoices } from '../api/invoices'

const invoices = ref<InvoiceListItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref('')
const clientFilter = ref('')
const sortField = ref<string>('created_at')
const sortOrder = ref<'asc' | 'desc'>('desc')

export function useInvoices() {
  async function load() {
    loading.value = true
    error.value = null
    try {
      invoices.value = await getInvoices()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load invoices'
    } finally {
      loading.value = false
    }
  }

  const filtered = computed(() => {
    let result = invoices.value

    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      result = result.filter(
        (inv) =>
          inv.invoice_number.toLowerCase().includes(q) ||
          (inv.project_name || '').toLowerCase().includes(q) ||
          (inv.client_name || '').toLowerCase().includes(q) ||
          (inv.job_code || '').toLowerCase().includes(q),
      )
    }

    if (statusFilter.value) {
      switch (statusFilter.value) {
        case 'unsent':
          result = result.filter((i) => i.sent_status === 'unsent')
          break
        case 'outstanding':
          result = result.filter((i) => i.sent_status === 'sent' && i.paid_status !== 'paid')
          break
        case 'paid':
          result = result.filter((i) => i.paid_status === 'paid')
          break
      }
    }

    if (clientFilter.value) {
      result = result.filter((i) => i.client_name === clientFilter.value)
    }

    const field = sortField.value
    const order = sortOrder.value === 'asc' ? 1 : -1
    result = [...result].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[field] ?? ''
      const bVal = (b as Record<string, unknown>)[field] ?? ''
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return (aVal - bVal) * order
      }
      return String(aVal).localeCompare(String(bVal)) * order
    })

    return result
  })

  const stats = computed(() => {
    const all = invoices.value
    const now = new Date()
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)

    return {
      outstanding: all
        .filter((i) => i.sent_status === 'sent' && i.paid_status !== 'paid')
        .reduce((s, i) => s + i.total_due, 0),
      unsent: all
        .filter((i) => i.sent_status === 'unsent')
        .reduce((s, i) => s + i.total_due, 0),
      collectedThisMonth: all
        .filter(
          (i) => i.paid_status === 'paid' && i.paid_at && new Date(i.paid_at) >= monthStart,
        )
        .reduce((s, i) => s + i.total_due, 0),
      invoicedThisMonth: all
        .filter(
          (i) => i.sent_status === 'sent' && i.sent_at && new Date(i.sent_at) >= monthStart,
        )
        .reduce((s, i) => s + i.total_due, 0),
    }
  })

  const uniqueClients = computed(() => {
    const clients = new Set<string>()
    invoices.value.forEach((i) => {
      if (i.client_name) clients.add(i.client_name)
    })
    return [...clients].sort()
  })

  function toggleSort(field: string) {
    if (sortField.value === field) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortField.value = field
      sortOrder.value = field === 'total_due' || field === 'created_at' ? 'desc' : 'asc'
    }
  }

  return {
    invoices,
    loading,
    error,
    searchQuery,
    statusFilter,
    clientFilter,
    sortField,
    sortOrder,
    filtered,
    stats,
    uniqueClients,
    load,
    toggleSort,
  }
}
