import { computed, ref } from 'vue'
import type { InvoiceListItem } from '../types'
import { getInvoices, generateSheet, sendInvoice, updateInvoice } from '../api/invoices'

const invoices = ref<InvoiceListItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref('')
const clientFilter = ref('')
const projectFilter = ref('')
const typeFilter = ref('')
const sentDateFrom = ref('')
const sentDateTo = ref('')
const sortField = ref<string>('created_at')
const sortOrder = ref<'asc' | 'desc'>('desc')

// Batch selection
const selectedIds = ref<Set<string>>(new Set())
const batchProcessing = ref(false)
const batchProgress = ref({ current: 0, total: 0, action: '' })

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
        case 'ready':
          result = result.filter((i) => i.total_due > 0 && i.sent_status === 'unsent' && i.data_path)
          break
        case 'needs_sheet':
          result = result.filter((i) => i.total_due > 0 && i.sent_status === 'unsent' && !i.data_path)
          break
        case 'draft':
          result = result.filter((i) => i.sent_status === 'unsent' && i.total_due === 0)
          break
        case 'sent':
          result = result.filter((i) => i.sent_status === 'sent' && i.paid_status === 'unpaid')
          break
        case 'paid':
          result = result.filter((i) => i.paid_status === 'paid')
          break
        case 'partial':
          result = result.filter((i) => i.paid_status === 'partial')
          break
      }
    }

    if (clientFilter.value) {
      result = result.filter((i) => i.client_name === clientFilter.value)
    }

    if (projectFilter.value) {
      result = result.filter((i) => i.project_id === projectFilter.value)
    }

    if (typeFilter.value) {
      result = result.filter((i) => i.type === typeFilter.value)
    }

    if (sentDateFrom.value) {
      result = result.filter((i) => i.sent_at && i.sent_at >= sentDateFrom.value)
    }

    if (sentDateTo.value) {
      result = result.filter((i) => i.sent_at && i.sent_at <= sentDateTo.value + 'T23:59:59')
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
      collectedYTD: all
        .filter(
          (i) => i.paid_status === 'paid' && i.paid_at && new Date(i.paid_at) >= new Date(now.getFullYear(), 0, 1),
        )
        .reduce((s, i) => s + i.total_due, 0),
    }
  })

  const filteredTotal = computed(() =>
    filtered.value.reduce((s, i) => s + i.total_due, 0),
  )

  const uniqueClients = computed(() => {
    const clients = new Set<string>()
    invoices.value.forEach((i) => {
      if (i.client_name) clients.add(i.client_name)
    })
    return [...clients].sort()
  })

  const uniqueProjects = computed(() => {
    const projects = new Map<string, string>()
    invoices.value.forEach((i) => {
      if (!projects.has(i.project_id)) {
        projects.set(i.project_id, i.project_name || i.project_id)
      }
    })
    return [...projects.entries()]
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name))
  })

  function toggleSort(field: string) {
    if (sortField.value === field) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortField.value = field
      sortOrder.value = field === 'total_due' || field === 'created_at' || field === 'sent_at' || field === 'paid_at' ? 'desc' : 'asc'
    }
  }

  // Batch selection
  function toggleSelect(id: string) {
    const next = new Set(selectedIds.value)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    selectedIds.value = next
  }

  function toggleSelectAll() {
    const filteredIds = filtered.value.map((i) => i.id)
    const allSelected = filteredIds.every((id) => selectedIds.value.has(id))
    if (allSelected) {
      selectedIds.value = new Set()
    } else {
      selectedIds.value = new Set(filteredIds)
    }
  }

  function clearSelection() {
    selectedIds.value = new Set()
  }

  const selectedInvoices = computed(() =>
    filtered.value.filter((i) => selectedIds.value.has(i.id)),
  )

  const selectedTotal = computed(() =>
    selectedInvoices.value.reduce((s, i) => s + i.total_due, 0),
  )

  const allFilteredSelected = computed(() => {
    const ids = filtered.value.map((i) => i.id)
    return ids.length > 0 && ids.every((id) => selectedIds.value.has(id))
  })

  // Batch actions
  async function batchGenerateSheets(): Promise<{ success: number; failed: number }> {
    const targets = selectedInvoices.value.filter((i) => !i.data_path)
    if (targets.length === 0) return { success: 0, failed: 0 }

    batchProcessing.value = true
    batchProgress.value = { current: 0, total: targets.length, action: 'Generating sheets' }
    let success = 0
    let failed = 0

    for (const inv of targets) {
      try {
        await generateSheet(inv.id)
        success++
      } catch {
        failed++
      }
      batchProgress.value.current++
    }

    batchProcessing.value = false
    await load()
    clearSelection()
    return { success, failed }
  }

  async function batchSend(): Promise<{ success: number; failed: number }> {
    const targets = selectedInvoices.value.filter((i) => i.data_path && i.total_due > 0 && i.sent_status === 'unsent')
    if (targets.length === 0) return { success: 0, failed: 0 }

    batchProcessing.value = true
    batchProgress.value = { current: 0, total: targets.length, action: 'Sending invoices' }
    let success = 0
    let failed = 0

    for (const inv of targets) {
      try {
        await sendInvoice(inv.id)
        success++
      } catch {
        failed++
      }
      batchProgress.value.current++
    }

    batchProcessing.value = false
    await load()
    clearSelection()
    return { success, failed }
  }

  async function batchMarkSent(): Promise<{ success: number; failed: number }> {
    const targets = selectedInvoices.value.filter((i) => i.sent_status === 'unsent')
    if (targets.length === 0) return { success: 0, failed: 0 }

    batchProcessing.value = true
    batchProgress.value = { current: 0, total: targets.length, action: 'Marking as sent' }
    let success = 0
    let failed = 0

    for (const inv of targets) {
      try {
        await updateInvoice(inv.id, { sent_status: 'sent' })
        success++
      } catch {
        failed++
      }
      batchProgress.value.current++
    }

    batchProcessing.value = false
    await load()
    clearSelection()
    return { success, failed }
  }

  async function batchMarkPaid(paidDate: string): Promise<{ success: number; failed: number }> {
    const targets = selectedInvoices.value.filter((i) => i.paid_status !== 'paid')
    if (targets.length === 0) return { success: 0, failed: 0 }

    batchProcessing.value = true
    batchProgress.value = { current: 0, total: targets.length, action: 'Marking as paid' }
    let success = 0
    let failed = 0

    for (const inv of targets) {
      try {
        await updateInvoice(inv.id, { paid_status: 'paid', paid_at: paidDate })
        success++
      } catch {
        failed++
      }
      batchProgress.value.current++
    }

    batchProcessing.value = false
    await load()
    clearSelection()
    return { success, failed }
  }

  return {
    invoices,
    loading,
    error,
    searchQuery,
    statusFilter,
    clientFilter,
    projectFilter,
    typeFilter,
    sentDateFrom,
    sentDateTo,
    sortField,
    sortOrder,
    filtered,
    filteredTotal,
    stats,
    uniqueClients,
    uniqueProjects,
    load,
    toggleSort,
    // Batch
    selectedIds,
    selectedInvoices,
    selectedTotal,
    allFilteredSelected,
    batchProcessing,
    batchProgress,
    toggleSelect,
    toggleSelectAll,
    clearSelection,
    batchGenerateSheets,
    batchSend,
    batchMarkSent,
    batchMarkPaid,
  }
}
