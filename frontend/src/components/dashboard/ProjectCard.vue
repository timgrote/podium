<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { ProjectSummary } from '../../types'
import { parseLocalDate, formatDateShort } from '../../utils/dates'

const props = defineProps<{
  project: ProjectSummary
  pinned: boolean
}>()

const emit = defineEmits<{
  edit: []
  delete: []
  togglePin: []
}>()

const router = useRouter()

function navigateToProject() {
  router.push(`/projects/${props.project.project_number || props.project.id}`)
}

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

const statusConfig: Record<string, { icon: string; color: string; label: string }> = {
  lead: { icon: 'pi-star', color: 'var(--p-amber-500)', label: 'Lead' },
  active: { icon: 'pi-play', color: 'var(--p-green-600)', label: 'Active' },
  complete: { icon: 'pi-check-circle', color: 'var(--p-primary-color)', label: 'Complete' },
  archive: { icon: 'pi-box', color: 'var(--p-surface-500)', label: 'Archive' },
}

const defaultStatus = { icon: 'pi-circle', color: 'var(--p-surface-500)', label: 'Unknown' }

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000) {
    return '$' + (value / 1000).toFixed(value % 1000 === 0 ? 0 : 1) + 'k'
  }
  return '$' + value.toFixed(0)
}
</script>

<template>
  <div class="project-card">
    <div class="project-row" @click="navigateToProject">
      <div class="col-pm">
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
        <button class="btn-pin" :class="{ active: pinned }" :title="pinned ? 'Unpin project' : 'Pin project'" @click.stop="emit('togglePin')">
          <i class="pi pi-thumbtack" />
        </button>
      </div>
      <div class="col-project">
        <i
          class="pi status-icon"
          :class="(statusConfig[project.status] || defaultStatus).icon"
          :style="{ color: (statusConfig[project.status] || defaultStatus).color }"
          :title="(statusConfig[project.status] || defaultStatus).label"
        />
        <span class="project-name">{{ project.project_name }}</span>
      </div>
      <div class="col-deadline">
        <span v-if="deadlineInfo" class="deadline-badge" :class="deadlineInfo.severity">{{ deadlineInfo.label }}</span>
      </div>
      <div class="col-financial">
        <span class="financial">{{ formatCurrency(project.total_contracted) }}</span>
      </div>
      <div class="col-financial">
        <span class="financial">{{ formatCurrency(project.total_invoiced) }}</span>
      </div>
      <div class="col-edit">
        <button class="btn-edit" title="Edit project" @click.stop="emit('edit')">
          <i class="pi pi-pencil" />
        </button>
      </div>
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


.project-row {
  display: flex;
  align-items: center;
  padding: 0.875rem 1rem;
  cursor: pointer;
  gap: 0.75rem;
}

.col-pm { width: 48px; flex-shrink: 0; display: flex; align-items: center; gap: 0.125rem; }
.col-project { flex: 1; min-width: 0; display: flex; align-items: center; gap: 0.5rem; overflow: hidden; }
.col-deadline { width: 6.5rem; flex-shrink: 0; }
.col-financial { width: 5rem; flex-shrink: 0; text-align: right; }
.col-edit { width: 1.5rem; flex-shrink: 0; display: flex; justify-content: center; }

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

.financial {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
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

.btn-pin {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--p-surface-400);
  border-radius: 0.25rem;
  font-size: 0.875rem;
  opacity: 0;
  transition: opacity 0.15s, color 0.15s;
}

.project-row:hover .btn-pin,
.btn-pin.active {
  opacity: 1;
}

.btn-pin.active {
  color: var(--p-primary-color);
}

.btn-pin:hover {
  color: var(--p-primary-color);
}

</style>
