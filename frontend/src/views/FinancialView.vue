<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useInvoices } from '../composables/useInvoices'
import { useToast } from '../composables/useToast'
import InvoiceEditModal from '../components/modals/InvoiceEditModal.vue'
import InvoiceActionsModal from '../components/modals/InvoiceActionsModal.vue'

const toast = useToast()
const {
  loading,
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
} = useInvoices()

const showEditModal = ref(false)
const editingInvoiceId = ref('')
const showActionsModal = ref(false)
const actionsInvoiceId = ref('')

onMounted(() => load())

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function openEdit(invoiceId: string) {
  editingInvoiceId.value = invoiceId
  showEditModal.value = true
}

function openActions(invoiceId: string) {
  actionsInvoiceId.value = invoiceId
  showActionsModal.value = true
}

function statusLabel(inv: { sent_status: string; paid_status: string }): string {
  if (inv.paid_status === 'paid') return 'Paid'
  if (inv.paid_status === 'partial') return 'Partial'
  if (inv.sent_status === 'sent') return 'Sent'
  return 'Draft'
}

function statusClass(inv: { sent_status: string; paid_status: string }): string {
  if (inv.paid_status === 'paid') return 'status-paid'
  if (inv.paid_status === 'partial') return 'status-partial'
  if (inv.sent_status === 'sent') return 'status-sent'
  return 'status-draft'
}

async function handleSaved() {
  await load()
}

function showError(msg: string) {
  toast.error(msg)
}
</script>

<template>
  <div class="financial-page">
    <div class="page-header">
      <h2>Financial</h2>
    </div>

    <!-- KPI Cards -->
    <div class="stats-bar">
      <div class="stat-card">
        <div class="stat-label">Outstanding</div>
        <div class="stat-value outstanding">{{ formatCurrency(stats.outstanding) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Unsent</div>
        <div class="stat-value unsent">{{ formatCurrency(stats.unsent) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Collected This Month</div>
        <div class="stat-value collected">{{ formatCurrency(stats.collectedThisMonth) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Invoiced This Month</div>
        <div class="stat-value">{{ formatCurrency(stats.invoicedThisMonth) }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters">
      <select v-model="statusFilter" class="filter-select">
        <option value="">All Statuses</option>
        <option value="unsent">Draft</option>
        <option value="outstanding">Outstanding</option>
        <option value="paid">Paid</option>
      </select>
      <select v-model="clientFilter" class="filter-select">
        <option value="">All Clients</option>
        <option v-for="c in uniqueClients" :key="c" :value="c">{{ c }}</option>
      </select>
      <input
        v-model="searchQuery"
        type="text"
        class="filter-input"
        placeholder="Search invoices..."
      />
      <span class="result-count">{{ filtered.length }} invoice{{ filtered.length !== 1 ? 's' : '' }}</span>
    </div>

    <!-- Invoice Table -->
    <div v-if="loading" class="loading">Loading invoices...</div>
    <div v-else-if="filtered.length === 0" class="empty-state">No invoices found</div>
    <table v-else class="invoice-table">
      <thead>
        <tr>
          <th class="sortable" @click="toggleSort('invoice_number')">
            Invoice #
            <i v-if="sortField === 'invoice_number'" :class="sortOrder === 'asc' ? 'pi pi-sort-up' : 'pi pi-sort-down'" />
          </th>
          <th class="sortable" @click="toggleSort('project_name')">
            Project
            <i v-if="sortField === 'project_name'" :class="sortOrder === 'asc' ? 'pi pi-sort-up' : 'pi pi-sort-down'" />
          </th>
          <th class="sortable" @click="toggleSort('client_name')">
            Client
            <i v-if="sortField === 'client_name'" :class="sortOrder === 'asc' ? 'pi pi-sort-up' : 'pi pi-sort-down'" />
          </th>
          <th class="sortable" @click="toggleSort('invoice_date')">
            Date
            <i v-if="sortField === 'invoice_date'" :class="sortOrder === 'asc' ? 'pi pi-sort-up' : 'pi pi-sort-down'" />
          </th>
          <th class="col-amount sortable" @click="toggleSort('total_due')">
            Amount
            <i v-if="sortField === 'total_due'" :class="sortOrder === 'asc' ? 'pi pi-sort-up' : 'pi pi-sort-down'" />
          </th>
          <th class="sortable" @click="toggleSort('paid_status')">
            Status
            <i v-if="sortField === 'paid_status'" :class="sortOrder === 'asc' ? 'pi pi-sort-up' : 'pi pi-sort-down'" />
          </th>
          <th class="sortable" @click="toggleSort('sent_at')">
            Sent
            <i v-if="sortField === 'sent_at'" :class="sortOrder === 'asc' ? 'pi pi-sort-up' : 'pi pi-sort-down'" />
          </th>
          <th class="sortable" @click="toggleSort('paid_at')">
            Paid
            <i v-if="sortField === 'paid_at'" :class="sortOrder === 'asc' ? 'pi pi-sort-up' : 'pi pi-sort-down'" />
          </th>
          <th class="col-actions"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="inv in filtered" :key="inv.id" class="row-clickable" @click="openEdit(inv.id)">
          <td class="cell-name">{{ inv.invoice_number }}</td>
          <td>{{ inv.project_name }}</td>
          <td>{{ inv.client_name || '' }}</td>
          <td>{{ formatDate(inv.invoice_date || inv.created_at) }}</td>
          <td class="col-amount">{{ formatCurrency(inv.total_due) }}</td>
          <td>
            <span class="status-pill" :class="statusClass(inv)">{{ statusLabel(inv) }}</span>
          </td>
          <td>{{ formatDate(inv.sent_at) }}</td>
          <td>{{ formatDate(inv.paid_at) }}</td>
          <td class="col-actions" @click.stop>
            <button class="btn-icon" title="Actions" @click="openActions(inv.id)">
              <i class="pi pi-ellipsis-h" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <InvoiceEditModal
      v-model:visible="showEditModal"
      :invoice-id="editingInvoiceId"
      @saved="handleSaved"
      @error="showError"
    />

    <InvoiceActionsModal
      v-model:visible="showActionsModal"
      :invoice-id="actionsInvoiceId"
      @saved="handleSaved"
      @error="showError"
    />
  </div>
</template>

<style scoped>
.financial-page {
  max-width: 1100px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0;
}

/* Stats */
.stats-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--p-content-background);
  border-radius: 0.5rem;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-text-muted-color);
  margin-bottom: 0.25rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.stat-value.outstanding { color: var(--p-orange-600); }
.stat-value.unsent { color: var(--p-yellow-600); }
.stat-value.collected { color: var(--p-green-600); }

/* Filters */
.filters {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.filter-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  min-width: 160px;
}

.filter-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  flex: 1;
}

.result-count {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

/* Table */
.invoice-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.invoice-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid var(--p-content-border-color);
}

.invoice-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
  color: var(--p-text-color);
}

.cell-name { font-weight: 500; }

.row-clickable { cursor: pointer; }
.row-clickable:hover td { background: var(--p-content-hover-background); }

.sortable {
  cursor: pointer;
  user-select: none;
}
.sortable:hover { color: var(--p-text-color); }
.sortable .pi { font-size: 0.5rem; margin-left: 0.25rem; }

.col-amount { text-align: right; }
.col-actions { width: 48px; text-align: right; }

/* Status pills */
.status-pill {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
  white-space: nowrap;
}

.status-draft {
  background: var(--p-surface-200);
  color: var(--p-surface-600);
}

.status-sent {
  background: var(--p-blue-100);
  color: var(--p-blue-700);
}

.status-paid {
  background: var(--p-green-100);
  color: var(--p-green-700);
}

.status-partial {
  background: var(--p-orange-100);
  color: var(--p-orange-700);
}

.btn-icon {
  background: none;
  border: none;
  color: var(--p-text-muted-color);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.btn-icon:hover {
  color: var(--p-text-color);
  background: var(--p-content-hover-background);
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--p-text-muted-color);
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .stats-bar {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
