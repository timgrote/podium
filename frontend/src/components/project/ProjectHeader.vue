<script setup lang="ts">
import { computed } from 'vue'
import type { ProjectSummary } from '../../types'
import { parseLocalDate, formatDateShort } from '../../utils/dates'
import { copyLink } from '../../utils/clipboard'

const props = defineProps<{
  project: ProjectSummary
}>()

const emit = defineEmits<{
  editProject: []
}>()

const statusConfig: Record<string, { icon: string; color: string; label: string }> = {
  lead: { icon: 'pi-star', color: 'var(--p-amber-500)', label: 'Lead' },
  active: { icon: 'pi-play', color: 'var(--p-green-600)', label: 'Active' },
  complete: { icon: 'pi-check-circle', color: 'var(--p-primary-color)', label: 'Complete' },
  archive: { icon: 'pi-box', color: 'var(--p-surface-500)', label: 'Archive' },
}
const defaultStatus = { icon: 'pi-circle', color: 'var(--p-surface-500)', label: 'Unknown' }

const status = computed(() => statusConfig[props.project.status] || defaultStatus)

const pmInitials = computed(() => {
  const name = props.project.pm_name
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?'
})

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
  return { label: formatDateShort(dl), severity: 'normal' as const }
})

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000) {
    return '$' + (value / 1000).toFixed(value % 1000 === 0 ? 0 : 1) + 'k'
  }
  return '$' + value.toFixed(0)
}
</script>

<template>
  <div class="project-header">
    <router-link to="/projects" class="back-link">
      <i class="pi pi-arrow-left" />
    </router-link>

    <div class="header-divider" />

    <i
      class="pi status-icon"
      :class="status.icon"
      :style="{ color: status.color }"
      :title="status.label"
    />

    <h1 class="project-name">{{ project.project_name }}</h1>

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

    <div class="header-spacer" />

    <div class="header-stats">
      <div class="stat">
        <span class="stat-label">Contracted</span>
        <span class="stat-value">{{ formatCurrency(project.total_contracted || 0) }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">Invoiced</span>
        <span class="stat-value">{{ formatCurrency(project.total_invoiced || 0) }}</span>
      </div>
      <div v-if="deadlineInfo" class="stat">
        <span class="stat-label">Next deadline</span>
        <span class="stat-value" :class="'deadline-' + deadlineInfo.severity">{{ deadlineInfo.label }}</span>
      </div>
    </div>

    <div class="header-divider" />

    <button class="header-btn" title="Copy link" @click="copyLink(`/projects/${project.project_number}`)">
      <i class="pi pi-link" />
    </button>
    <button class="header-btn" title="Edit project" @click="emit('editProject')">
      <i class="pi pi-pencil" />
    </button>
  </div>
</template>

<style scoped>
.project-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  background: var(--p-content-background);
  border-bottom: 1px solid var(--p-content-border-color);
}

.back-link {
  color: var(--p-text-muted-color);
  text-decoration: none;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  padding: 0.25rem;
  border-radius: 0.25rem;
}

.back-link:hover {
  color: var(--p-primary-color);
  background: var(--p-content-hover-background);
}

.header-divider {
  width: 1px;
  height: 1.25rem;
  background: var(--p-content-border-color);
}

.status-icon {
  font-size: 0.875rem;
}

.project-name {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.pm-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  object-fit: cover;
}

.pm-avatar-initials {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--p-primary-color);
  color: #fff;
  font-size: 0.5625rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-spacer {
  flex: 1;
}

.header-stats {
  display: flex;
  gap: 1.25rem;
}

.stat {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
}

.stat-label {
  color: var(--p-text-muted-color);
}

.stat-value {
  font-weight: 500;
  color: var(--p-text-color);
}

.deadline-overdue {
  color: var(--p-red-600);
  font-weight: 600;
}

.deadline-soon {
  color: var(--p-amber-500);
  font-weight: 600;
}

.header-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.375rem;
  color: var(--p-text-muted-color);
  border-radius: 0.25rem;
  font-size: 0.8125rem;
}

.header-btn:hover {
  background: var(--p-content-hover-background);
  color: var(--p-text-color);
}
</style>
