<script setup lang="ts">
import { computed } from 'vue'
import type { ProjectSummary } from '../../types'

const props = defineProps<{
  project: ProjectSummary
  expanded: boolean
}>()

const emit = defineEmits<{
  toggle: []
  edit: []
  delete: []
}>()

const pmInitials = computed(() => {
  const name = props.project.pm_name
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?'
})

const invoicedSent = computed(() =>
  props.project.invoices
    ?.filter(i => i.sent_status === 'sent')
    .reduce((sum, i) => sum + (Number(i.total_due) || 0), 0) ?? 0
)

const invoicedUnsent = computed(() =>
  props.project.invoices
    ?.filter(i => i.sent_status === 'unsent')
    .reduce((sum, i) => sum + (Number(i.total_due) || 0), 0) ?? 0
)

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
        <img
          v-if="project.pm_avatar_url"
          :src="project.pm_avatar_url"
          :alt="project.pm_name || 'PM'"
          class="pm-avatar"
          :title="project.pm_name || ''"
        />
        <span
          v-else-if="project.pm_name"
          class="pm-avatar-initials"
          :title="project.pm_name"
        >{{ pmInitials }}</span>
        <i
          class="pi status-icon"
          :class="(statusConfig[project.status] || defaultStatus).icon"
          :style="{ color: (statusConfig[project.status] || defaultStatus).color }"
          :title="(statusConfig[project.status] || defaultStatus).label"
        />
        <span class="project-name">{{ project.project_name }}</span>
      </div>
      <div class="project-financials">
        <span class="financial" title="Contract value">{{ formatCurrency(project.total_contracted) }}</span>
        <span class="financial invoiced-sent" title="Invoiced (sent)">{{ formatCurrency(invoicedSent) }}</span>
        <span class="financial invoiced-unsent" title="Invoiced (unsent)">{{ formatCurrency(invoicedUnsent) }}</span>
        <button class="btn-edit" title="Edit project" @click.stop="emit('edit')">
          <i class="pi pi-pencil" />
        </button>
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

.pm-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.pm-avatar-initials {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--p-surface-200);
  color: var(--p-surface-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6rem;
  font-weight: 600;
  flex-shrink: 0;
}

.status-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.project-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-color);
  overflow: hidden;
  text-overflow: ellipsis;
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

.financial.invoiced-sent {
  color: var(--p-green-600);
}

.financial.invoiced-unsent {
  color: var(--p-amber-600);
}

.btn-edit {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--p-text-muted-color);
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.btn-edit:hover {
  background: var(--p-content-hover-background);
  color: var(--p-text-color);
}

.project-detail-slot {
  border-top: 1px solid var(--p-content-border-color);
  padding: 1rem;
}
</style>
