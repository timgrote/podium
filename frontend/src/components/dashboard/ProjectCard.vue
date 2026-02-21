<script setup lang="ts">
import type { ProjectSummary } from '../../types'

defineProps<{
  project: ProjectSummary
  expanded: boolean
}>()

const emit = defineEmits<{
  toggle: []
  edit: []
  delete: []
}>()

const statusColors: Record<string, string> = {
  proposal: 'var(--p-violet-500)',
  contract: 'var(--p-primary-color)',
  invoiced: 'var(--p-amber-500)',
  paid: 'var(--p-green-600)',
  complete: 'var(--p-surface-500)',
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}
</script>

<template>
  <div class="project-card" :class="{ expanded }">
    <div class="project-row" @click="emit('toggle')">
      <div class="project-info">
        <span
          class="status-badge"
          :style="{ backgroundColor: statusColors[project.status] || 'var(--p-surface-500)' }"
        >
          {{ project.status }}
        </span>
        <span class="job-code">{{ project.job_code || project.id }}</span>
        <span class="project-name">{{ project.project_name }}</span>
        <span v-if="project.client_name" class="client-name">{{ project.client_name }}</span>
      </div>
      <div class="project-financials">
        <span class="financial">{{ formatCurrency(project.total_contracted) }}</span>
        <span class="financial invoiced">{{ formatCurrency(project.total_invoiced) }}</span>
        <span class="financial paid">{{ formatCurrency(project.total_paid) }}</span>
        <i :class="expanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" />
      </div>
    </div>
    <div v-if="expanded" class="project-detail-slot">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.project-card {
  background: var(--p-content-background);
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: box-shadow 0.15s;
}

.project-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.project-card.expanded {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.project-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1rem;
  cursor: pointer;
  gap: 1rem;
}

.project-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.status-badge {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #fff;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  white-space: nowrap;
  font-weight: 600;
}

.job-code {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-surface-800);
  white-space: nowrap;
}

.project-name {
  color: var(--p-surface-600);
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.client-name {
  color: var(--p-surface-400);
  font-size: 0.8125rem;
  white-space: nowrap;
}

.project-financials {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-shrink: 0;
}

.financial {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--p-surface-600);
  min-width: 5rem;
  text-align: right;
}

.financial.invoiced {
  color: var(--p-amber-600);
}

.financial.paid {
  color: var(--p-green-600);
}

.project-detail-slot {
  border-top: 1px solid var(--p-surface-200);
  padding: 1rem;
}
</style>
