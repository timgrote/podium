<script setup lang="ts">
/**
 * ProjectTasksBoard — the project-level Kanban board that lives inside the
 * conductor project view's Tasks section.
 *
 * Reads task data exclusively through the projectTasks data-access module
 * (listTasks), which returns top-level tasks sorted by status column, pinned-
 * first, then sort_order. Columns are the canonical TASK_STATUSES; each shows a
 * header with the status label + count and cards with title, assignees (if any)
 * and a due/last-updated label.
 *
 * Drag-and-drop: cards are native-HTML5 draggable. Dropping a card on a column
 * (or above/below another card) calls updateTaskStatus to persist the new
 * status/position. The UI updates optimistically and rolls back on API failure
 * with an error toast. A per-card status menu provides the same status-change
 * action for keyboard/screen-reader users who cannot drag.
 */
import { computed, ref, watch } from 'vue'
import type { ProjectSummary, Task } from '../../types'
import {
  TASK_STATUSES,
  TASK_STATUS_LABELS,
  listTasks,
  groupTasksByStatus,
  reorderTasksForBoard,
  updateTaskStatus,
  type TaskStatus,
} from '../../api/projectTasks'
import { useToast } from '../../composables/useToast'
import { useCollapsibleColumns } from '../../composables/useCollapsibleColumns'
import { formatDateShort, isOverdue } from '../../utils/dates'

const props = defineProps<{
  project: ProjectSummary
  /** Increment to force the board to reload tasks (e.g. after a modal save). */
  refreshKey?: number
}>()

const emit = defineEmits<{
  openTask: [taskId: string]
}>()

const toast = useToast()
const { isCollapsed, toggleColumn } = useCollapsibleColumns()

const tasks = ref<Task[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Drag state (native HTML5).
const dragging = ref<Task | null>(null)
/** Status column currently hovered during a drag (drives column highlight). */
const dragOverStatus = ref<TaskStatus | null>(null)
/**
 * Id of the card the pointer is currently "before" (drop insertion point).
 * `null` means append to the end of the hovered column.
 */
const dropBeforeId = ref<string | null>(null)

// Accessible status-change menu.
const activeMenuTaskId = ref<string | null>(null)

/** Group tasks into canonical status columns via the shared data-access helper. */
const columns = computed(() => groupTasksByStatus(tasks.value))

function assigneeInitials(task: Task): string[] {
  if (!task.assignees?.length) return []
  return task.assignees.map((a) => {
    const f = a.first_name?.[0] ?? ''
    const l = a.last_name?.[0] ?? ''
    return `${f}${l}`.toUpperCase() || '?'
  })
}

function assigneeName(task: Task): string {
  const a = task.assignees?.[0]
  if (!a) return ''
  return `${a.first_name} ${a.last_name}`.trim()
}

/** Due/last-updated label for a card footer. */
function cardMeta(task: Task): { label: string; severity: 'overdue' | 'soon' | 'normal' | 'none' } | null {
  if (task.due_date) {
    if (isOverdue(task.due_date) && task.status !== 'done' && task.status !== 'canceled') {
      return { label: 'Overdue', severity: 'overdue' }
    }
    return { label: formatDateShort(task.due_date), severity: task.status === 'done' ? 'none' : 'soon' }
  }
  if (task.updated_at) {
    return { label: `Updated ${formatDateShort(task.updated_at)}`, severity: 'normal' }
  }
  return null
}

async function load() {
  loading.value = true
  error.value = null
  try {
    tasks.value = await listTasks(props.project.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

watch(() => props.project.id, load, { immediate: true })
watch(() => props.refreshKey, () => load())

// --- Drag & drop ---
function onDragStart(task: Task, event: DragEvent) {
  dragging.value = task
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', task.id)
  }
}

function onDragEnd() {
  dragging.value = null
  dragOverStatus.value = null
  dropBeforeId.value = null
}

function onColumnDragEnter(status: TaskStatus) {
  dragOverStatus.value = status
}

/** Hover over a card: set the insertion point before this card (or after it). */
function onCardDragOver(status: TaskStatus, taskId: string, nextId: string | null, event: DragEvent) {
  dragOverStatus.value = status
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const topHalf = event.clientY < rect.top + rect.height / 2
  dropBeforeId.value = topHalf ? taskId : nextId
}

/** Hover over empty column space: append to the end. */
function onBodyDragOver(status: TaskStatus) {
  dragOverStatus.value = status
  dropBeforeId.value = null
}

function onDrop(status: TaskStatus) {
  const drag = dragging.value
  const beforeId = dropBeforeId.value
  dragging.value = null
  dragOverStatus.value = null
  dropBeforeId.value = null
  if (!drag) return
  void moveTask(drag.id, status, beforeId)
}

/** Resolve the drop to a target status + in-column index, then persist. */
async function moveTask(taskId: string, targetStatus: TaskStatus, beforeId: string | null) {
  const col = groupTasksByStatus(tasks.value).find((c) => c.status === targetStatus)
  const remaining = col ? col.tasks.filter((t) => t.id !== taskId) : []
  let targetIndex = remaining.length
  if (beforeId) {
    const i = remaining.findIndex((t) => t.id === beforeId)
    if (i >= 0) targetIndex = i
  }
  await applyMove(taskId, targetStatus, targetIndex)
}

/**
 * Optimistically reorder the local board, persist via updateTaskStatus, and
 * roll back to the previous order on failure with an error toast.
 */
async function applyMove(taskId: string, targetStatus: TaskStatus, targetIndex: number) {
  const task = tasks.value.find((t) => t.id === taskId)
  if (!task) return

  const reordered = reorderTasksForBoard(tasks.value, taskId, targetStatus, targetIndex)
  const orderUnchanged =
    reordered.map((t) => t.id).join('|') === tasks.value.map((t) => t.id).join('|')
  if (orderUnchanged && task.status === targetStatus) return // no-op drop

  const snapshot = tasks.value.map((t) => ({ ...t }))
  tasks.value = reordered

  try {
    await updateTaskStatus(props.project.id, taskId, targetStatus, targetIndex)
    toast.success('Moved', `${task.title} → ${TASK_STATUS_LABELS[targetStatus]}`)
  } catch (e) {
    tasks.value = snapshot
    toast.error('Move failed', e instanceof Error ? e.message : undefined)
  }
}

// --- Accessible status-change menu (keyboard / screen-reader alternative) ---
function toggleMenu(taskId: string, event: MouseEvent) {
  event.stopPropagation()
  activeMenuTaskId.value = activeMenuTaskId.value === taskId ? null : taskId
}

async function changeStatusViaMenu(taskId: string, targetStatus: TaskStatus) {
  const col = groupTasksByStatus(tasks.value).find((c) => c.status === targetStatus)
  const remaining = col ? col.tasks.filter((t) => t.id !== taskId) : []
  activeMenuTaskId.value = null
  await applyMove(taskId, targetStatus, remaining.length)
}

defineExpose({ load })
</script>

<template>
  <!-- Loading state: spinner + skeleton columns -->
  <div v-if="loading" class="ptb-loading" data-testid="ptb-loading">
    <i class="pi pi-spin pi-spinner" /> Loading tasks…
    <div class="ptb-skeleton-row" aria-hidden="true">
      <div v-for="n in 5" :key="n" class="ptb-skeleton-col">
        <div class="ptb-skeleton-card" />
        <div class="ptb-skeleton-card" />
      </div>
    </div>
  </div>

  <!-- Error state -->
  <div v-else-if="error" class="ptb-error" role="alert">
    <i class="pi pi-exclamation-triangle" />
    <div>
      <p class="ptb-error-title">Failed to load tasks</p>
      <p class="ptb-error-detail">{{ error }}</p>
    </div>
    <button class="ptb-retry" @click="load">Retry</button>
  </div>

  <!-- Board -->
  <div v-else class="ptb-board">
    <div
      v-for="col in columns"
      :key="col.status"
      class="ptb-column"
      :class="{
        empty: col.tasks.length === 0,
        collapsed: isCollapsed(col.status, col.tasks.length),
        'drag-over': dragOverStatus === col.status,
      }"
      :title="isCollapsed(col.status, col.tasks.length) ? `Expand ${col.label}` : undefined"
      @dragenter.prevent="onColumnDragEnter(col.status)"
      @dragover.prevent
      @click="toggleColumn(col.status)"
    >
      <div class="ptb-column-header">
        <span class="ptb-dot" :class="col.status"></span>
        <span class="ptb-column-label">{{ col.label }}</span>
        <span class="ptb-count">{{ col.tasks.length }}</span>
      </div>

      <div
        v-if="!isCollapsed(col.status, col.tasks.length)"
        class="ptb-column-body"
        @dragover.prevent="onBodyDragOver(col.status)"
        @drop.prevent="onDrop(col.status)"
      >
        <div
          v-for="(task, i) in col.tasks"
          :key="task.id"
          class="ptb-card"
          :class="{
            pinned: task.is_pinned,
            dragging: dragging?.id === task.id,
            'drop-before': dragging && dropBeforeId === task.id,
          }"
          draggable="true"
          @dragstart="onDragStart(task, $event)"
          @dragend="onDragEnd"
          @dragover.stop.prevent="onCardDragOver(col.status, task.id, col.tasks[i + 1]?.id ?? null, $event)"
          @click="emit('openTask', task.id)"
        >
          <div class="ptb-card-title-row">
            <span class="ptb-card-title">{{ task.title }}</span>
            <span class="ptb-card-actions">
              <span v-if="task.is_pinned" class="ptb-pin" title="Pinned"><i class="pi pi-bookmark" /></span>
              <span class="ptb-menu-wrap">
                <button
                  class="ptb-menu-btn"
                  type="button"
                  aria-label="Change status"
                  aria-haspopup="menu"
                  :aria-expanded="activeMenuTaskId === task.id"
                  @click.stop="toggleMenu(task.id, $event)"
                >
                  <i class="pi pi-ellipsis-v" />
                </button>
                <div v-if="activeMenuTaskId === task.id" class="ptb-menu" role="menu" @click.stop>
                  <button
                    v-for="s in TASK_STATUSES"
                    :key="s"
                    type="button"
                    class="ptb-menu-item"
                    :class="{ current: task.status === s }"
                    role="menuitem"
                    @click="changeStatusViaMenu(task.id, s)"
                  >
                    {{ TASK_STATUS_LABELS[s] }}
                  </button>
                </div>
              </span>
            </span>
          </div>

          <div class="ptb-card-footer">
            <span
              v-if="cardMeta(task)"
              class="ptb-meta"
              :class="cardMeta(task)!.severity"
            >
              {{ cardMeta(task)!.label }}
            </span>
            <div v-if="assigneeInitials(task).length" class="ptb-assignees">
              <span
                v-for="(initials, ai) in assigneeInitials(task)"
                :key="initials + ai"
                class="ptb-avatar"
                :title="task.assignees?.[ai] ? `${task.assignees[ai].first_name} ${task.assignees[ai].last_name}` : assigneeName(task)"
              >{{ initials }}</span>
            </div>
          </div>
        </div>

        <!-- Empty column: drop-target placeholder -->
        <div v-if="col.tasks.length === 0" class="ptb-empty">
          <span class="ptb-empty-label">Drop here</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ptb-loading {
  padding: 2rem;
  text-align: center;
  color: var(--p-text-muted-color);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
  font-size: 0.875rem;
}
.ptb-skeleton-row {
  display: flex;
  gap: 1rem;
  width: 100%;
}
.ptb-skeleton-col {
  flex: 1 1 0;
  min-width: 200px;
  background: var(--p-surface-100);
  border-radius: 0.625rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}
.app-dark .ptb-skeleton-col {
  background: var(--p-surface-900);
}
.ptb-skeleton-card {
  height: 72px;
  border-radius: 0.5rem;
  background: var(--p-content-border-color);
  opacity: 0.5;
  animation: ptb-pulse 1.2s ease-in-out infinite;
}
@keyframes ptb-pulse {
  0%, 100% { opacity: 0.35; }
  50% { opacity: 0.6; }
}

.ptb-error {
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--p-red-600, #dc2626);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  background: var(--p-content-background);
}
.ptb-error .pi {
  font-size: 1.25rem;
}
.ptb-error-title {
  margin: 0;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-color);
}
.ptb-error-detail {
  margin: 0.125rem 0 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.ptb-retry {
  margin-left: auto;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--p-text-color);
  cursor: pointer;
  flex-shrink: 0;
}
.ptb-retry:hover {
  background: var(--p-content-hover-background);
}

.ptb-board {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  overflow-x: auto;
  padding-bottom: 1rem;
}
.ptb-column {
  flex: 1 1 0;
  min-width: 240px;
  background: var(--p-surface-100);
  border-radius: 0.625rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 220px);
  transition: background 0.15s, outline 0.15s;
}
.ptb-column.drag-over {
  outline: 2px solid var(--p-primary-color);
  background: var(--p-primary-color-subtle, var(--p-surface-100));
}

/* Collapsed empty column → thin vertical strip (Hermes-style) */
.ptb-column.collapsed {
  flex: 0 0 44px;
  min-width: 44px;
  cursor: pointer;
  justify-content: center;
  align-items: center;
  transition: flex-basis 0.15s ease, min-width 0.15s ease;
}
.ptb-column.collapsed .ptb-column-header {
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 0.25rem;
}
.ptb-column.collapsed .ptb-column-label {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.ptb-column.collapsed .ptb-count {
  margin-left: 0;
}
.ptb-column.collapsed:hover {
  background: var(--p-surface-200);
}
.app-dark .ptb-column.collapsed:hover {
  background: var(--p-surface-800);
}
.app-dark .ptb-column {
  background: var(--p-surface-900);
}
.ptb-column-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.25rem 0.75rem;
}
.ptb-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--p-surface-400);
}
.ptb-dot.todo { background: var(--p-surface-400); }
.ptb-dot.triage { background: var(--p-purple-500); }
.ptb-dot.in_progress { background: var(--p-blue-500); }
.ptb-dot.blocked { background: var(--p-red-500); }
.ptb-dot.done { background: var(--p-green-600); }
.ptb-dot.canceled { background: var(--p-surface-500); }
.ptb-column-label {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-color);
}
.ptb-count {
  margin-left: auto;
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 1rem;
  padding: 0.125rem 0.5rem;
}
.ptb-column-body {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  overflow-y: auto;
  min-height: 60px;
}
.ptb-card {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 0.75rem;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.15s, transform 0.15s;
}
.ptb-card:hover {
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
}
.ptb-card.pinned {
  border-left: 3px solid var(--p-primary-color);
}
.ptb-card.dragging {
  opacity: 0.4;
}
/* Drop-position indicator — high-contrast amber, animated so it's unmistakable. */
.ptb-card.drop-before {
  border-color: #f59e0b;
  box-shadow: 0 -4px 0 0 #f59e0b, 0 0 0 2px rgba(245, 158, 11, 0.45);
  animation: ptb-drop-pulse 0.9s ease-in-out infinite;
}
@keyframes ptb-drop-pulse {
  0%, 100% { box-shadow: 0 -4px 0 0 #f59e0b, 0 0 0 2px rgba(245, 158, 11, 0.45); }
  50% { box-shadow: 0 -4px 0 0 #f59e0b, 0 0 0 4px rgba(245, 158, 11, 0.85); }
}
.ptb-card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}
.ptb-card-title {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-color);
  line-height: 1.3;
  word-break: break-word;
}
.ptb-card-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
}
.ptb-pin {
  color: var(--p-primary-color);
  font-size: 0.75rem;
  flex-shrink: 0;
}
.ptb-menu-wrap {
  position: relative;
  display: inline-flex;
}
.ptb-menu-btn {
  background: none;
  border: none;
  color: var(--p-text-muted-color);
  cursor: pointer;
  padding: 0.125rem 0.25rem;
  font-size: 0.8125rem;
  border-radius: 0.25rem;
  line-height: 1;
}
.ptb-menu-btn:hover,
.ptb-menu-btn:focus-visible {
  color: var(--p-text-color);
  background: var(--p-content-hover-background);
  outline: none;
}
.ptb-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 30;
  min-width: 9rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
  padding: 0.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}
.ptb-menu-item {
  text-align: left;
  background: none;
  border: none;
  padding: 0.375rem 0.625rem;
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  color: var(--p-text-color);
  cursor: pointer;
  white-space: nowrap;
}
.ptb-menu-item:hover,
.ptb-menu-item:focus-visible {
  background: var(--p-content-hover-background);
  outline: none;
}
.ptb-menu-item.current {
  color: var(--p-primary-color);
  font-weight: 600;
}
.ptb-card-footer {
  margin-top: 0.625rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.ptb-meta {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.ptb-meta.overdue {
  background: var(--p-red-50, #fef2f2);
  color: var(--p-red-600, #dc2626);
}
.ptb-meta.soon {
  background: var(--p-amber-50, #fffbeb);
  color: var(--p-amber-600, #d97706);
}
.ptb-meta.normal {
  color: var(--p-text-muted-color);
  padding: 0.125rem 0;
}
.ptb-assignees {
  display: flex;
  gap: 0.125rem;
  margin-left: auto;
  flex-shrink: 0;
}
.ptb-avatar {
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
.ptb-empty {
  padding: 1rem;
  text-align: center;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  border: 1.5px dashed var(--p-content-border-color);
  border-radius: 0.5rem;
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ptb-empty-label {
  opacity: 0.6;
}
</style>
