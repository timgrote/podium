<script setup lang="ts">
import { ref } from 'vue'
import type { ProjectSummary } from '../../types'

const props = defineProps<{
  project: ProjectSummary
}>()

const emit = defineEmits<{
  editProject: []
  deleteProject: []
  createContract: [projectId: string]
  editContract: [contractId: string]
  deleteContract: [contractId: string]
  createInvoice: [contractId: string]
  editInvoice: [invoiceId: string]
  deleteInvoice: [invoiceId: string]
  invoiceActions: [invoiceId: string]
  createProposal: [projectId: string]
  editProposal: [proposalId: string]
  deleteProposal: [proposalId: string]
  promoteProposal: [proposalId: string]
  viewNotes: [projectId: string]
}>()

const activeTab = ref<'financial' | 'tasks' | 'notes'>('financial')

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString()
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}
</script>

<template>
  <div class="project-detail">
    <div class="detail-header">
      <div class="detail-meta">
        <span v-if="project.location" class="meta-item">
          <i class="pi pi-map-marker" /> {{ project.location }}
        </span>
        <span v-if="project.pm_name" class="meta-item">
          <i class="pi pi-user" /> {{ project.pm_name }}
        </span>
      </div>
      <div class="detail-actions">
        <button class="btn btn-sm" @click="emit('editProject')">
          <i class="pi pi-pencil" /> Edit
        </button>
        <button class="btn btn-sm btn-danger" @click="emit('deleteProject')">
          <i class="pi pi-trash" /> Delete
        </button>
      </div>
    </div>

    <div class="tabs">
      <button
        class="tab"
        :class="{ active: activeTab === 'financial' }"
        @click="activeTab = 'financial'"
      >
        Financial
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'notes' }"
        @click="activeTab = 'notes'"
      >
        Notes
      </button>
    </div>

    <div v-if="activeTab === 'financial'" class="tab-content">
      <!-- Contracts -->
      <div class="section">
        <div class="section-header">
          <h4>Contracts</h4>
          <button class="btn btn-sm btn-primary" @click="emit('createContract', project.id)">
            <i class="pi pi-plus" /> Add
          </button>
        </div>
        <div v-if="project.contracts.length === 0" class="empty">No contracts</div>
        <div v-for="contract in project.contracts" :key="contract.id" class="sub-card">
          <div class="sub-card-header">
            <span class="sub-card-title">{{ formatCurrency(contract.total_amount) }}</span>
            <span v-if="contract.signed_at" class="sub-card-date">
              Signed {{ formatDate(contract.signed_at) }}
            </span>
            <div class="sub-card-actions">
              <button class="btn-icon" title="Create Invoice" @click="emit('createInvoice', contract.id)">
                <i class="pi pi-file" />
              </button>
              <button class="btn-icon" title="Edit" @click="emit('editContract', contract.id)">
                <i class="pi pi-pencil" />
              </button>
              <button class="btn-icon" title="Delete" @click="emit('deleteContract', contract.id)">
                <i class="pi pi-trash" />
              </button>
            </div>
          </div>
          <div v-if="contract.tasks.length" class="task-table">
            <div class="task-row task-header-row">
              <span class="task-name">Task</span>
              <span class="task-amount">Fee</span>
              <span class="task-billed">Billed</span>
              <span class="task-pct">%</span>
            </div>
            <div v-for="task in contract.tasks" :key="task.id" class="task-row">
              <span class="task-name">{{ task.name }}</span>
              <span class="task-amount">{{ formatCurrency(task.amount) }}</span>
              <span class="task-billed">{{ formatCurrency(task.billed_amount) }}</span>
              <span class="task-pct">{{ formatPercent(task.billed_percent) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Invoices -->
      <div class="section">
        <div class="section-header">
          <h4>Invoices</h4>
        </div>
        <div v-if="project.invoices.length === 0" class="empty">No invoices</div>
        <div v-for="invoice in project.invoices" :key="invoice.id" class="sub-card">
          <div class="sub-card-header">
            <span class="sub-card-title">{{ invoice.invoice_number }}</span>
            <span class="sub-card-amount">{{ formatCurrency(invoice.total_due) }}</span>
            <span
              class="status-pill"
              :class="{
                sent: invoice.sent_status === 'sent',
                paid: invoice.paid_status === 'paid',
              }"
            >
              {{ invoice.paid_status === 'paid' ? 'Paid' : invoice.sent_status === 'sent' ? 'Sent' : 'Draft' }}
            </span>
            <div class="sub-card-actions">
              <button class="btn-icon" title="Actions" @click="emit('invoiceActions', invoice.id)">
                <i class="pi pi-ellipsis-h" />
              </button>
              <button class="btn-icon" title="Edit" @click="emit('editInvoice', invoice.id)">
                <i class="pi pi-pencil" />
              </button>
              <button class="btn-icon" title="Delete" @click="emit('deleteInvoice', invoice.id)">
                <i class="pi pi-trash" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Proposals -->
      <div class="section">
        <div class="section-header">
          <h4>Proposals</h4>
          <button class="btn btn-sm btn-primary" @click="emit('createProposal', project.id)">
            <i class="pi pi-plus" /> Add
          </button>
        </div>
        <div v-if="project.proposals.length === 0" class="empty">No proposals</div>
        <div v-for="proposal in project.proposals" :key="proposal.id" class="sub-card">
          <div class="sub-card-header">
            <span class="sub-card-title">{{ formatCurrency(proposal.total_fee) }}</span>
            <span
              class="status-pill"
              :class="{ sent: proposal.status === 'sent', accepted: proposal.status === 'accepted' }"
            >
              {{ proposal.status }}
            </span>
            <div class="sub-card-actions">
              <button
                v-if="proposal.status !== 'accepted'"
                class="btn-icon"
                title="Promote to Contract"
                @click="emit('promoteProposal', proposal.id)"
              >
                <i class="pi pi-arrow-up" />
              </button>
              <button class="btn-icon" title="Edit" @click="emit('editProposal', proposal.id)">
                <i class="pi pi-pencil" />
              </button>
              <button class="btn-icon" title="Delete" @click="emit('deleteProposal', proposal.id)">
                <i class="pi pi-trash" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'notes'" class="tab-content">
      <button class="btn btn-sm btn-primary" @click="emit('viewNotes', project.id)">
        <i class="pi pi-comments" /> View Notes
      </button>
    </div>
  </div>
</template>

<style scoped>
.project-detail {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-meta {
  display: flex;
  gap: 1rem;
}

.meta-item {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.detail-actions {
  display: flex;
  gap: 0.5rem;
}

.tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--p-content-border-color);
}

.tab {
  padding: 0.5rem 1rem;
  background: none;
  border: none;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
}

.tab.active {
  color: var(--p-text-color);
  border-bottom-color: var(--p-primary-color);
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.section-header h4 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.sub-card {
  background: var(--p-content-hover-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
}

.sub-card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.sub-card-title {
  font-weight: 600;
  font-size: 0.875rem;
}

.sub-card-amount {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.sub-card-date {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.sub-card-actions {
  margin-left: auto;
  display: flex;
  gap: 0.25rem;
}

.status-pill {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  background: var(--p-content-hover-background);
  color: var(--p-text-muted-color);
  font-weight: 600;
}

.status-pill.sent {
  background: var(--p-blue-100);
  color: var(--p-blue-700);
}

.status-pill.paid,
.status-pill.accepted {
  background: var(--p-green-100);
  color: var(--p-green-700);
}

.task-table {
  margin-top: 0.5rem;
}

.task-row {
  display: grid;
  grid-template-columns: 1fr 6rem 6rem 4rem;
  gap: 0.5rem;
  padding: 0.25rem 0;
  font-size: 0.8125rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.task-header-row {
  font-weight: 600;
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--p-content-border-color);
}

.task-amount,
.task-billed,
.task-pct {
  text-align: right;
}

.empty {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all 0.15s;
  color: var(--p-text-color);
}

.btn:hover {
  background: var(--p-content-hover-background);
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.btn-primary {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.btn-primary:hover {
  background: var(--p-primary-hover-color);
}

.btn-danger {
  color: var(--p-red-600);
  border-color: var(--p-red-300);
}

.btn-danger:hover {
  background: var(--p-red-50);
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--p-text-muted-color);
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.btn-icon:hover {
  background: var(--p-content-hover-background);
  color: var(--p-text-color);
}
</style>
