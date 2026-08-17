<script setup lang="ts">
import { computed, ref } from 'vue'
import type { InvoiceListItem } from '../../types'
import { updateInvoice } from '../../api/invoices'
import { useToast } from '../../composables/useToast'
import { daysPastDue } from '../../utils/dates'

const props = defineProps<{
  invoices: InvoiceListItem[]
}>()

const emit = defineEmits<{
  edit: [invoiceId: string]
  changed: []
}>()

const toast = useToast()
const dragging = ref<InvoiceListItem | null>(null)
const dragOverStatus = ref<string | null>(null)

// Column definitions mirror the list view's status buckets.
const COLUMNS = [
  { status: 'draft', label: 'Draft' },
  { status: 'ready', label: 'Ready to Send' },
  { status: 'sent', label: 'Sent' },
  { status: 'partial', label: 'Partial' },
  { status: 'paid', label: 'Paid' },
] as const

type ColumnStatus = (typeof COLUMNS)[number]['status']

function columnOf(inv: InvoiceListItem): ColumnStatus {
  if (inv.paid_status === 'paid') return 'paid'
  if (inv.paid_status === 'partial') return 'partial'
  if (inv.sent_status === 'sent') return 'sent'
  if (inv.total_due > 0 && inv.data_path) return 'ready'
  return 'draft'
}

const columns = computed(() =>
  COLUMNS.map((c) => ({
    ...c,
    invoices: props.invoices.filter((inv) => columnOf(inv) === c.status),
  })),
)

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function statusMeta(inv: InvoiceListItem) {
  if (inv.paid_status === 'paid') return { label: 'Paid', cls: 'status-paid' }
  if (inv.paid_status === 'partial') {
    return inv.due_date && daysPastDue(inv.due_date) > 0
      ? { label: 'Past Due', cls: 'status-past-due' }
      : { label: 'Partial', cls: 'status-partial' }
  }
  if (inv.sent_status === 'sent') {
    return inv.due_date && daysPastDue(inv.due_date) > 0
      ? { label: 'Past Due', cls: 'status-past-due' }
      : { label: 'Sent', cls: 'status-sent' }
  }
  return { label: 'Draft', cls: 'status-draft' }
}

function onDragStart(inv: InvoiceListItem) {
  dragging.value = inv
}
function onDragEnd() {
  dragging.value = null
  dragOverStatus.value = null
}
function onDragEnter(status: string) {
  dragOverStatus.value = status
}

async function onDrop(status: ColumnStatus) {
  const inv = dragging.value
  dragOverStatus.value = null
  if (!inv) return
  const from = columnOf(inv)
  if (from === status) {
    dragging.value = null
    return
  }

  // Map the target column to the underlying sent/paid status updates.
  const patch: { sent_status?: string; paid_status?: string; paid_at?: string } = {}
  if (status === 'draft' || status === 'ready') {
    patch.sent_status = 'unsent'
    patch.paid_status = 'unpaid'
  } else if (status === 'sent') {
    patch.sent_status = 'sent'
    patch.paid_status = 'unpaid'
  } else if (status === 'partial') {
    patch.sent_status = 'sent'
    patch.paid_status = 'partial'
  } else if (status === 'paid') {
    patch.sent_status = 'sent'
    patch.paid_status = 'paid'
    patch.paid_at = new Date().toISOString().split('T')[0]
  }

  try {
    await updateInvoice(inv.id, patch)
    toast.success('Updated', `${inv.invoice_number} → ${status}`)
    emit('changed')
  } catch (e) {
    toast.error('Update failed', e instanceof Error ? e.message : undefined)
  } finally {
    dragging.value = null
  }
}

function deadlineBadge(inv: InvoiceListItem) {
  if (inv.paid_status === 'paid') return null
  const days = daysPastDue(inv.due_date)
  if (days > 0 && inv.sent_status === 'sent') return { label: `${days}d`, cls: 'overdue' }
  if (days > 0) return { label: `${days}d`, cls: 'soon' }
  return null
}
</script>

<template>
  <div class="invoice-board">
    <div
      v-for="col in columns"
      :key="col.status"
      class="kanban-column"
      :class="{ 'drag-over': dragOverStatus === col.status }"
      @dragover.prevent
      @dragenter.prevent="onDragEnter(col.status)"
      @drop.prevent="onDrop(col.status)"
    >
      <div class="kanban-column-header">
        <span class="kanban-dot" :class="col.status"></span>
        <span class="kanban-column-label">{{ col.label }}</span>
        <span class="kanban-count">{{ col.invoices.length }}</span>
      </div>

      <div class="kanban-column-body">
        <div
          v-for="inv in col.invoices"
          :key="inv.id"
          class="kanban-card"
          :class="{ dragging: dragging?.id === inv.id }"
          draggable="true"
          @dragstart="onDragStart(inv)"
          @dragend="onDragEnd"
          @click="emit('edit', inv.id)"
        >
          <div class="card-title-row">
            <span class="card-title">{{ inv.invoice_number }}</span>
            <span class="card-amount">{{ formatCurrency(inv.total_due) }}</span>
          </div>

          <div class="card-meta">
            <span class="card-project">{{ inv.project_name }}</span>
            <span class="card-client">{{ inv.client_name }}</span>
          </div>

          <div class="card-footer">
            <div class="card-footer-left">
              <span v-if="deadlineBadge(inv)" class="deadline-badge" :class="deadlineBadge(inv)!.cls">
                {{ deadlineBadge(inv)!.label }}
              </span>
            </div>
            <div class="card-right">
              <span class="status-pill" :class="statusMeta(inv).cls">{{ statusMeta(inv).label }}</span>
            </div>
          </div>
        </div>

        <div v-if="col.invoices.length === 0" class="kanban-empty">No invoices</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.invoice-board {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  overflow-x: auto;
  padding-bottom: 1rem;
}

.kanban-column {
  /* Stretch columns to fill the available width — no narrow cap. */
  flex: 1 1 0;
  min-width: 240px;
  background: var(--p-surface-100);
  border-radius: 0.625rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 240px);
  transition: background 0.15s, outline 0.15s;
}
.app-dark .kanban-column {
  background: var(--p-surface-900);
}
.kanban-column.drag-over {
  background: var(--p-primary-100);
  outline: 2px dashed var(--p-primary-color);
}

.kanban-column-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.25rem 0.75rem;
}

.kanban-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--p-surface-400);
}
.kanban-dot.draft { background: var(--p-yellow-600); }
.kanban-dot.ready { background: var(--p-blue-500); }
.kanban-dot.sent { background: var(--p-orange-500); }
.kanban-dot.partial { background: var(--p-purple-500); }
.kanban-dot.paid { background: var(--p-green-600); }

.kanban-column-label {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-color);
}

.kanban-count {
  margin-left: auto;
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 1rem;
  padding: 0.125rem 0.5rem;
}

.kanban-column-body {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  overflow-y: auto;
  min-height: 60px;
}

.kanban-card {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 0.75rem;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.15s, transform 0.15s;
}
.kanban-card:hover {
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
}
.kanban-card.dragging {
  opacity: 0.5;
  transform: rotate(2deg);
}

.card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}
.card-title {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-color);
  line-height: 1.3;
  word-break: break-word;
}
.card-amount {
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--p-text-color);
  white-space: nowrap;
}

.card-meta {
  margin-top: 0.375rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}
.card-project {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.card-client {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.card-footer {
  margin-top: 0.625rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.card-footer-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.card-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
}

.deadline-badge {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
  white-space: nowrap;
}
.deadline-badge.overdue {
  background: var(--p-red-50, #fef2f2);
  color: var(--p-red-600, #dc2626);
}
.deadline-badge.soon {
  background: var(--p-amber-50, #fffbeb);
  color: var(--p-amber-600, #d97706);
}

.status-pill {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
}
.status-paid { background: var(--p-green-50, #f0fdf4); color: var(--p-green-700, #15803d); }
.status-partial { background: var(--p-purple-50, #faf5ff); color: var(--p-purple-700, #7e22ce); }
.status-sent { background: var(--p-blue-50, #eff6ff); color: var(--p-blue-700, #1d4ed8); }
.status-past-due { background: var(--p-red-50, #fef2f2); color: var(--p-red-700, #b91c1c); }
.status-draft { background: var(--p-surface-100); color: var(--p-text-muted-color); }

.kanban-empty {
  padding: 1rem;
  text-align: center;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  border: 1px dashed var(--p-content-border-color);
  border-radius: 0.5rem;
}
</style>
