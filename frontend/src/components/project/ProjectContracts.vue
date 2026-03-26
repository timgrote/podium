<script setup lang="ts">
import type { ProjectSummary } from '../../types'
import { formatDate } from '../../utils/dates'

const props = defineProps<{
  project: ProjectSummary
}>()

const emit = defineEmits<{
  createContract: [projectId: string]
  editContract: [contractId: string]
  deleteContract: [contractId: string]
  createInvoice: [contractId: string]
}>()

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', minimumFractionDigits: 2,
  }).format(value)
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}
</script>

<template>
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
          <button class="btn-icon btn-icon-green" title="Create Invoice" @click="emit('createInvoice', contract.id)">
            <i class="pi pi-dollar" />
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
</template>

<style scoped>
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
.sub-card-title { font-weight: 600; font-size: 0.875rem; }
.sub-card-amount { font-weight: 500; font-size: 0.875rem; color: var(--p-text-muted-color); }
.sub-card-date { font-size: 0.75rem; color: var(--p-text-muted-color); }
.sub-card-actions { margin-left: auto; display: flex; gap: 0.25rem; }
.status-pill {
  font-size: 0.625rem; text-transform: uppercase; letter-spacing: 0.05em;
  padding: 0.125rem 0.5rem; border-radius: 9999px;
  background: var(--p-content-hover-background); color: var(--p-text-muted-color); font-weight: 600;
}
.status-pill.sent { background: var(--p-blue-100); color: var(--p-blue-700); }
.status-pill.paid, .status-pill.accepted { background: var(--p-green-100); color: var(--p-green-700); }
.btn-icon {
  background: none; border: none; cursor: pointer; padding: 0.25rem;
  color: var(--p-text-muted-color); border-radius: 0.25rem; font-size: 0.875rem;
}
.btn-icon-green { color: var(--p-green-600); }
.btn-icon-green:hover { color: var(--p-green-700); }
.btn-icon:hover { background: var(--p-content-hover-background); color: var(--p-text-color); }
.btn { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.375rem 0.75rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.75rem; font-weight: 500; color: var(--p-text-color); }
.btn:hover { background: var(--p-content-hover-background); }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.empty { font-size: 0.8125rem; color: var(--p-text-muted-color); font-style: italic; }
.task-table { margin-top: 0.5rem; }
.task-row {
  display: grid; grid-template-columns: 1fr 6rem 6rem 4rem;
  gap: 0.5rem; padding: 0.25rem 0; font-size: 0.8125rem;
  border-bottom: 1px solid var(--p-content-border-color);
}
.task-header-row {
  font-weight: 600; color: var(--p-text-muted-color); font-size: 0.6875rem;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.task-amount, .task-billed, .task-pct { text-align: right; }
</style>
