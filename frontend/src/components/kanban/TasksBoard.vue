<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { KanbanTaskBoard, KanbanTaskCard, KanbanTaskColumn } from '../../types'
import { getTaskBoard, moveTaskCard } from '../../api/kanban'
import { bulkUpdateTasks, bulkDeleteTasks } from '../../api/tasks'
import { useToast } from '../../composables/useToast'
import { useMultiSelect } from '../../composables/useMultiSelect'
import { parseLocalDate, formatDateShort } from '../../utils/dates'
import { TASK_SORT_OPTIONS, sortTasks, type TaskSortKey } from '../../utils/boardSort'
import { useCollapsibleColumns } from '../../composables/useCollapsibleColumns'

const props = defineProps<{
  assignee?: string
}>()

const emit = defineEmits<{
  'open-task': [task: { id: string; project_id: string }]
}>()

const router = useRouter()
const toast = useToast()

const { isCollapsed, toggleColumn } = useCollapsibleColumns()
const { selected, multiSelecting, handleClick, clear, isSelected } = useMultiSelect()

/** Display order of all task card ids (for shift-click range selection). */
const orderedCardIds = computed<string[]>(() =>
  columns.value.flatMap((col) => col.tasks.map((t) => t.id)),
)

/** Canonical task status columns, used for the bulk "move to" action. */
const STATUS_OPTIONS: { status: string; label: string }[] = [
  { status: 'triage', label: 'Triage' },
  { status: 'todo', label: 'To Do' },
  { status: 'in_progress', label: 'In Progress' },
  { status: 'blocked', label: 'Blocked' },
  { status: 'done', label: 'Done' },
  { status: 'canceled', label: 'Canceled' },
]

const board = ref<KanbanTaskBoard | null>(null)
const loading = ref(false)

// Per-column sort (view only — never mutates stored sort_order).
const columnSort = ref<Record<string, TaskSortKey>>({})

// Project filter (multi-project boards only). Filters tasks by project_id.
const projectFilter = ref<string>('all')

// Drag state
const dragging = ref<KanbanTaskCard | null>(null)
const dragOverStatus = ref<string | null>(null)
// Exact drop-position tracking: which card the pointer is over and whether
// it's the top or bottom half, so a drop places the card precisely.
const dragOverCardId = ref<string | null>(null)
const dragOverHalf = ref<'top' | 'bottom'>('top')

/** Distinct projects present on the board, for the filter dropdown. */
const projectOptions = computed<{ id: string; name: string }[]>(() => {
  const map = new Map<string, string>()
  for (const col of board.value?.columns ?? []) {
    for (const t of col.tasks) {
      if (t.project_id && t.project_name) map.set(t.project_id, t.project_name)
    }
  }
  return [...map.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name))
})

/** Columns with cards filtered by project and sorted per the selected view. */
const columns = computed<KanbanTaskColumn[]>(() =>
  (board.value?.columns ?? []).map((col) => {
    let tasks = col.tasks
    if (projectFilter.value !== 'all') {
      tasks = tasks.filter((t) => t.project_id === projectFilter.value)
    }
    const key = columnSort.value[col.status] ?? 'manual'
    return { ...col, tasks: sortTasks(tasks, key) }
  }),
)

const hasActiveProjectFilter = computed(() => projectFilter.value !== 'all')

function clearProjectFilter() {
  projectFilter.value = 'all'
}

function columnSortKey(col: KanbanTaskColumn): TaskSortKey {
  return columnSort.value[col.status] ?? 'manual'
}

function setColumnSort(status: string, key: TaskSortKey) {
  columnSort.value = { ...columnSort.value, [status]: key }
}

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

function openTask(task: KanbanTaskCard, event?: MouseEvent) {
  if (event) {
    const consumed = handleClick(task.id, {
      ctrl: event.ctrlKey,
      meta: event.metaKey,
      shift: event.shiftKey,
    }, orderedCardIds.value)
    if (consumed) return
  }
  if (!task.project_id) {
    toast.error('Task unavailable', 'This task is missing its project link.')
    return
  }
  emit('open-task', { id: task.id, project_id: task.project_id })
}

function navigateToProject(task: KanbanTaskCard, event: MouseEvent) {
  event.stopPropagation()
  router.push(`/projects/${task.project_number || task.project_id}`)
}

// --- Bulk actions on the selected group ---

function selectedTaskIds(): string[] {
  return [...selected.value]
}

async function moveSelectedTo(status: string) {
  const ids = selectedTaskIds()
  if (ids.length === 0) return
  try {
    await bulkUpdateTasks(ids, { status })
    board.value = await getTaskBoard(props.assignee)
    setColumnSort(status, 'manual')
    toast.success('Moved', `${ids.length} task${ids.length > 1 ? 's' : ''} → ${status}`)
    // Keep the group selected in its new column.
  } catch (e) {
    toast.error('Move failed', e instanceof Error ? e.message : undefined)
  }
}

async function completeSelected() {
  const ids = selectedTaskIds()
  if (ids.length === 0) return
  try {
    await bulkUpdateTasks(ids, { status: 'done' })
    board.value = await getTaskBoard(props.assignee)
    toast.success('Completed', `${ids.length} task${ids.length > 1 ? 's' : ''} marked done`)
  } catch (e) {
    toast.error('Update failed', e instanceof Error ? e.message : undefined)
  }
}

async function deleteSelected() {
  const ids = selectedTaskIds()
  if (ids.length === 0) return
  if (!window.confirm(`Delete ${ids.length} task${ids.length > 1 ? 's' : ''}?`)) return
  try {
    await bulkDeleteTasks(ids)
    board.value = await getTaskBoard(props.assignee)
    toast.success('Deleted', `${ids.length} task${ids.length > 1 ? 's' : ''}`)
  } catch (e) {
    toast.error('Delete failed', e instanceof Error ? e.message : undefined)
  }
  clear()
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
  dragOverCardId.value = null
}

function onDragEnter(status: string) {
  dragOverStatus.value = status
  dragOverCardId.value = null
}

/** Record which card the pointer is over and whether it's the top/bottom half. */
function onCardDragOver(status: string, card: KanbanTaskCard, event: DragEvent) {
  dragOverStatus.value = status
  const el = event.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  dragOverCardId.value = card.id
  dragOverHalf.value = event.clientY < rect.top + rect.height / 2 ? 'top' : 'bottom'
}

/**
 * Compute the sort_order that places the dragged card at the current drop
 * point (index among the column's other tasks). In manual order the displayed
 * order == sort_order, so this is exact; for another sort it anchors to the
 * sort_order of the card at the drop point.
 */
function computeTargetSortOrder(col: KanbanTaskColumn, dragged: KanbanTaskCard): number {
  const hoveredId = dragOverCardId.value
  const hoveredHalf = dragOverHalf.value
  const others = col.tasks.filter((t) => t.id !== dragged.id)
  let insertIndex = others.length
  if (hoveredId) {
    const hi = others.findIndex((t) => t.id === hoveredId)
    if (hi >= 0) insertIndex = hoveredHalf === 'top' ? hi : hi + 1
  }
  const anchor = others[insertIndex]
  if (anchor) return anchor.sort_order
  return others.length
}

async function onDrop(status: string) {
  const task = dragging.value
  if (!task) return

  // Dragging a card that's part of a multi-selection moves the whole group.
  const group = isSelected(task.id) && selected.value.size > 1
  const ids = group ? [...selected.value] : [task.id]

  const targetCol = columns.value.find((c) => c.status === status)
  // Capture the drop position BEFORE clearing the hover state.
  const targetSortOrder = targetCol ? computeTargetSortOrder(targetCol, task) : 0

  dragOverStatus.value = null
  dragOverCardId.value = null

  try {
    for (const id of ids) {
      await moveTaskCard({ task_id: id, status, sort_order: targetSortOrder })
    }
    board.value = await getTaskBoard(props.assignee)
    setColumnSort(status, 'manual')
    toast.success('Moved', `${ids.length} task${ids.length > 1 ? 's' : ''} → ${status}`)
    if (group) clear()
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

  <div v-else class="kanban-board-wrap">
    <!-- Project filter toolbar (multi-project board) -->
    <div class="kanban-toolbar">
      <div class="toolbar-filters">
        <select v-model="projectFilter" class="toolbar-select" title="Filter by project">
          <option value="all">All projects</option>
          <option v-for="p in projectOptions" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <button v-if="hasActiveProjectFilter" class="toolbar-clear" @click="clearProjectFilter">
          Clear
        </button>
      </div>
    </div>

    <!-- Selection action toolbar (shown when a multi-select is active) -->
    <div v-if="multiSelecting" class="selection-toolbar">
      <span class="selection-count">{{ selected.size }} selected</span>
      <div class="selection-actions">
        <select
          class="toolbar-select"
          title="Move selected to..."
          @change="moveSelectedTo(($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''"
        >
          <option value="" disabled>Move to…</option>
          <option v-for="opt in STATUS_OPTIONS" :key="opt.status" :value="opt.status">
            {{ opt.label }}
          </option>
        </select>
        <button class="selection-btn" @click="completeSelected">
          <i class="pi pi-check" /> Mark done
        </button>
        <button class="selection-btn danger" @click="deleteSelected">
          <i class="pi pi-trash" /> Delete
        </button>
        <button class="selection-btn" @click="clear">
          <i class="pi pi-times" /> Clear
        </button>
      </div>
    </div>

    <div class="kanban-board">
    <div
      v-for="col in columns"
      :key="col.status"
      class="kanban-column"
      :class="{
        'drag-over': dragOverStatus === col.status,
        collapsed: isCollapsed(col.status, col.tasks.length),
      }"
      :title="isCollapsed(col.status, col.tasks.length) ? `Expand ${col.label}` : undefined"
      @dragover.prevent
      @dragenter.prevent="onDragEnter(col.status)"
      @drop.prevent="onDrop(col.status)"
      @click="toggleColumn(col.status)"
    >
      <div class="kanban-column-header">
        <span class="kanban-dot" :class="col.status"></span>
        <span class="kanban-column-label">{{ col.label }}</span>
        <span class="kanban-count">{{ taskCount(col) }}</span>
        <div v-if="!isCollapsed(col.status, col.tasks.length)" class="kanban-sort">
          <select
            class="kanban-sort-select"
            :value="columnSortKey(col)"
            title="Sort this column"
            @click.stop
            @change="setColumnSort(col.status, ($event.target as HTMLSelectElement).value as TaskSortKey)"
          >
            <option
              v-for="opt in TASK_SORT_OPTIONS"
              :key="opt.key"
              :value="opt.key"
            >{{ opt.label }}</option>
          </select>
        </div>
      </div>

      <div v-if="!isCollapsed(col.status, col.tasks.length)" class="kanban-column-body">
        <div
          v-for="task in col.tasks"
          :key="task.id"
          class="kanban-card"
          :class="{
            dragging: dragging?.id === task.id,
            selected: isSelected(task.id),
            'drop-top': dragOverStatus === col.status && dragOverCardId === task.id && dragOverHalf === 'top',
            'drop-bottom': dragOverStatus === col.status && dragOverCardId === task.id && dragOverHalf === 'bottom',
          }"
          draggable="true"
          @dragstart="onDragStart(task)"
          @dragend="onDragEnd"
          @dragover.prevent="onCardDragOver(col.status, task, $event)"
          @click="openTask(task, $event)"
        >
          <div class="card-title-row">
            <span class="card-title">{{ task.title }}</span>
          </div>

          <div class="card-meta">
            <button class="card-project" title="Open project" @click="navigateToProject(task, $event)">
              <i class="pi pi-briefcase" />
              {{ task.project_name }}
              <span v-if="task.job_code" class="card-job">({{ task.job_code }})</span>
            </button>
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
  </div>
</template>

<style scoped>
.kanban-loading {
  padding: 3rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

/* --- Project filter toolbar --- */
.kanban-toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.toolbar-filters {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.toolbar-select {
  padding: 0.4375rem 0.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
  max-width: 240px;
}
.toolbar-clear {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.375rem 0.625rem;
  font-size: 0.75rem;
  color: var(--p-primary-color);
  cursor: pointer;
  white-space: nowrap;
}
.toolbar-clear:hover {
  background: var(--p-content-hover-background);
}

/* --- Selection toolbar --- */
.selection-toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-primary-color);
  border-radius: 0.5rem;
  background: var(--p-primary-color-subtle, var(--p-surface-100));
}
.selection-count {
  font-weight: 600;
  font-size: 0.8125rem;
  color: var(--p-text-color);
}
.selection-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.selection-btn {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.375rem 0.625rem;
  font-size: 0.75rem;
  color: var(--p-text-color);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}
.selection-btn:hover {
  background: var(--p-content-hover-background);
}
.selection-btn.danger {
  color: var(--p-red-600);
  border-color: var(--p-red-200, var(--p-content-border-color));
}
.selection-btn.danger:hover {
  background: var(--p-red-50, #fef2f2);
}

.kanban-board {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  overflow-x: auto;
  padding-bottom: 1rem;
}

.kanban-column {
  /* Stretch columns to fill the available width — no narrow cap. */
  flex: 1 1 0;
  min-width: 240px;
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

/* Collapsed empty column → thin vertical strip (Hermes-style) */
.kanban-column.collapsed {
  flex: 0 0 44px;
  min-width: 44px;
  cursor: pointer;
  justify-content: center;
  align-items: center;
  transition: flex-basis 0.15s ease, min-width 0.15s ease;
}
.kanban-column.collapsed .kanban-column-header {
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 0.25rem;
}
.kanban-column.collapsed .kanban-column-label {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.kanban-column.collapsed .kanban-count {
  margin-left: 0;
}
.kanban-column.collapsed:hover {
  background: var(--p-surface-200);
}
.app-dark .kanban-column.collapsed:hover {
  background: var(--p-surface-800);
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
.kanban-dot.triage { background: var(--p-purple-500); }
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
.kanban-sort {
  margin-left: 0.375rem;
  display: flex;
  align-items: center;
}
.kanban-sort-select {
  border: 1px solid transparent;
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
  padding: 0.125rem 0.25rem;
  border-radius: 0.375rem;
  cursor: pointer;
  max-width: 150px;
}
.kanban-sort-select:hover,
.kanban-sort-select:focus {
  border-color: var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  outline: none;
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
.kanban-card.selected {
  border-color: var(--p-primary-color);
  box-shadow: 0 0 0 2px var(--p-primary-color);
  background: var(--p-primary-color-subtle, var(--p-content-background));
}

/* Drop-position indicator — high-contrast amber, animated so it's unmistakable. */
.kanban-card.drop-top,
.kanban-card.drop-bottom {
  border-color: #f59e0b;
  animation: drop-pulse 0.9s ease-in-out infinite;
}
.kanban-card.drop-top {
  box-shadow: 0 -4px 0 0 #f59e0b, 0 0 0 2px rgba(245, 158, 11, 0.45);
}
.kanban-card.drop-bottom {
  box-shadow: 0 4px 0 0 #f59e0b, 0 0 0 2px rgba(245, 158, 11, 0.45);
}
@keyframes drop-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.45); }
  50% { box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.85); }
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
  appearance: none;
  width: fit-content;
  padding: 0;
  border: 0;
  background: none;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
  text-align: left;
}
.card-project:hover {
  color: var(--p-primary-color);
  text-decoration: underline;
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
