<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { KanbanTaskBoard, KanbanTaskCard, KanbanTaskColumn } from '../../types'
import { getTaskBoard, moveTaskCard } from '../../api/kanban'
import { useToast } from '../../composables/useToast'
import { parseLocalDate, formatDateShort } from '../../utils/dates'

const props = defineProps<{
  assignee?: string
}>()

const router = useRouter()
const toast = useToast()

const board = ref<KanbanTaskBoard | null>(null)
const loading = ref(false)

// Drag state
const dragging = ref<KanbanTaskCard | null>(null)
const dragOverStatus = ref<string | null>(null)

const columns = computed<KanbanTaskColumn[]>(() => board.value?.columns ?? [])

function taskCount(col: KanbanTaskColumn): number {
  return col.tasks.length
}

function deadlineInfo(task: KanbanTaskCard) {
  const dl = task.due_date
  if (!dl) return null
  if (task.status === 'done' || task.status === 'canceled') return null
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const due = parseLocalDate(dl)
  const diffDays = Math.round((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  if (diffDays < 0) return { label: `${Math.abs(diffDays)}d overdue`, severity: 'overdue' as const }
  if (diffDays <= 7) return { label: `Due ${formatDateShort(dl)}`, severity: 'soon' as const }
  return { label: formatDateShort(dl), severity: 'normal' as const }
}

function initials(name: string | null): string {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?'
}

function navigateToTask(task: KanbanTaskCard) {
  router.push(`/projects/${task.project_number || task.project_id}`)
}

async function load() {
  loading.value = true
  try {
    board.value = await getTaskBoard(props.assignee)
  } catch (e) {
    toast.error('Failed to load task board', e instanceof Error ? e.message : undefined)
  } finally {
    loading.value = false
  }
}

watch(() => props.assignee, () => load())
onMounted(load)

// --- Drag & drop ---
function onDragStart(task: KanbanTaskCard) {
  dragging.value = task
}
function onDragEnd() {
  dragging.value = null
  dragOverStatus.value = null
}

function onDragEnter(status: string) {
  dragOverStatus.value = status
}

async function onDrop(status: string) {
  const task = dragging.value
  dragOverStatus.value = null
  if (!task) return

  if (task.status === status) {
    dragging.value = null
    return
  }

  const targetCol = columns.value.find((c) => c.status === status)
  const insertIndex = targetCol ? targetCol.tasks.length : 0

  try {
    board.value = await moveTaskCard({ task_id: task.id, status, sort_order: insertIndex })
    toast.success('Moved', `${task.title} → ${status}`)
  } catch (e) {
    toast.error('Move failed', e instanceof Error ? e.message : undefined)
  } finally {
    dragging.value = null
  }
}
</script>

<template>
  <div v-if="loading && !board" class="kanban-loading">
    <i class="pi pi-spin pi-spinner" /> Loading board…
  </div>

  <div v-else class="kanban-board">
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
        <span class="kanban-count">{{ taskCount(col) }}</span>
      </div>

      <div class="kanban-column-body">
        <div
          v-for="task in col.tasks"
          :key="task.id"
          class="kanban-card"
          :class="{ dragging: dragging?.id === task.id }"
          draggable="true"
          @dragstart="onDragStart(task)"
          @dragend="onDragEnd"
          @click="navigateToTask(task)"
        >
          <div class="card-title-row">
            <span class="card-title">{{ task.title }}</span>
          </div>

          <div class="card-meta">
            <span class="card-project">
              <i class="pi pi-briefcase" />
              {{ task.project_name }}
              <span v-if="task.job_code" class="card-job">({{ task.job_code }})</span>
            </span>
          </div>

          <div class="card-tags" v-if="task.tags && task.tags.length">
            <span v-for="tag in task.tags.slice(0, 3)" :key="tag" class="tag-chip">{{ tag }}</span>
          </div>

          <div class="card-footer">
            <div class="card-footer-left">
              <span v-if="task.subtask_count > 0" class="subtask-badge">
                <i class="pi pi-list" /> {{ task.subtask_count }}
              </span>
              <span v-if="deadlineInfo(task)" class="deadline-badge" :class="deadlineInfo(task)!.severity">
                {{ deadlineInfo(task)!.label }}
              </span>
            </div>
            <div class="card-right">
              <span v-if="task.assignee_name" class="pm-avatar" :title="task.assignee_name">
                {{ initials(task.assignee_name) }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="col.tasks.length === 0" class="kanban-empty">No tasks</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kanban-loading {
  padding: 3rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

.kanban-board {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  overflow-x: auto;
  padding-bottom: 1rem;
}

.kanban-column {
  flex: 1 1 0;
  min-width: 240px;
  max-width: 280px;
  background: var(--p-surface-100);
  border-radius: 0.625rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 200px);
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
.kanban-dot.todo { background: var(--p-surface-400); }
.kanban-dot.in_progress { background: var(--p-blue-500); }
.kanban-dot.blocked { background: var(--p-red-500); }
.kanban-dot.done { background: var(--p-green-600); }
.kanban-dot.canceled { background: var(--p-surface-500); }

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

.card-meta {
  margin-top: 0.375rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}
.card-project {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
.card-project .pi {
  font-size: 0.6875rem;
}
.card-job {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.card-tags {
  margin-top: 0.375rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
.tag-chip {
  background: var(--p-surface-100);
  color: var(--p-text-muted-color);
  font-size: 0.625rem;
  font-weight: 500;
  padding: 0.0625rem 0.375rem;
  border-radius: 0.25rem;
}
.app-dark .tag-chip {
  background: var(--p-surface-800);
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
  flex-wrap: wrap;
}
.card-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
}

.subtask-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}
.subtask-badge .pi {
  font-size: 0.625rem;
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
.deadline-badge.normal {
  color: var(--p-text-muted-color);
}

.pm-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--p-surface-200);
  color: var(--p-surface-600);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6rem;
  font-weight: 600;
  flex-shrink: 0;
}

.kanban-empty {
  padding: 1rem;
  text-align: center;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  border: 1px dashed var(--p-content-border-color);
  border-radius: 0.5rem;
}
</style>
