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

const statusConfig: Record<string, { icon: string; color: string; label: string }> = {
  proposal: { icon: 'pi-file-edit', color: 'var(--p-violet-500)', label: 'Proposal' },
  contract: { icon: 'pi-file-check', color: 'var(--p-primary-color)', label: 'Contract' },
  in_process: { icon: 'pi-spinner', color: 'var(--p-cyan-500)', label: 'In Process' },
  invoiced: { icon: 'pi-send', color: 'var(--p-amber-500)', label: 'Invoiced' },
  paid: { icon: 'pi-dollar', color: 'var(--p-green-600)', label: 'Paid' },
  complete: { icon: 'pi-check-circle', color: 'var(--p-surface-500)', label: 'Complete' },
}

const defaultStatus = { icon: 'pi-circle', color: 'var(--p-surface-500)', label: 'Unknown' }

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
        <i
          class="pi status-icon"
          :class="(statusConfig[project.status] || defaultStatus).icon"
          :style="{ color: (statusConfig[project.status] || defaultStatus).color }"
          :title="(statusConfig[project.status] || defaultStatus).label"
        />
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

.status-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.job-code {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-color);
  white-space: nowrap;
}

.project-name {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.client-name {
  color: var(--p-text-muted-color);
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
  color: var(--p-text-muted-color);
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
  border-top: 1px solid var(--p-content-border-color);
  padding: 1rem;
}
</style>
