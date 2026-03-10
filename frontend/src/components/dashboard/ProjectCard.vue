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

function parseLocalDate(dateStr: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    const parts = dateStr.split('-').map(Number)
    return new Date(parts[0]!, parts[1]! - 1, parts[2]!)
  }
  return new Date(dateStr)
}

const deadlineInfo = computed(() => {
  const dl = props.project.next_task_deadline
  if (!dl) return null
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const due = parseLocalDate(dl)
  const diffDays = Math.round((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  const isComplete = props.project.status === 'complete' || props.project.status === 'archive'
  if (isComplete) return null
  if (diffDays < 0) return { label: `${Math.abs(diffDays)}d overdue`, severity: 'overdue' as const }
  if (diffDays <= 14) return { label: `Due in ${diffDays}d`, severity: 'soon' as const }
  return { label: due.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), severity: 'normal' as const }
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
  lead: { icon: 'pi-star', color: 'var(--p-amber-500)', label: 'Lead' },
  active: { icon: 'pi-play', color: 'var(--p-green-600)', label: 'Active' },
  complete: { icon: 'pi-check-circle', color: 'var(--p-primary-color)', label: 'Complete' },
  archive: { icon: 'pi-box', color: 'var(--p-surface-500)', label: 'Archive' },
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
        <span v-if="deadlineInfo" class="deadline-badge" :class="deadlineInfo.severity">{{ deadlineInfo.label }}</span>
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

.deadline-badge {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
  white-space: nowrap;
  flex-shrink: 0;
}

.deadline-badge.overdue {
  background: var(--p-red-50, #fef2f2);
  color: var(--p-red-600, #dc2626);
}

.deadline-badge.soon {
  background: var(--p-amber-50, #fffbeb);
  color: var(--p-amber-600, #d97706);
}

.deadline-badge.normal {
  color: var(--p-text-muted-color);
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
