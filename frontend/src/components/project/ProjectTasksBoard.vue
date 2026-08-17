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
 * Drag-and-drop is intentionally NOT implemented in this task. The
 * `onMoveTask` callback prop is the documented seam the follow-up drag-and-drop
 * task will call to persist moves — it is currently a no-op.
 */
import { computed, ref, watch } from 'vue'
import type { ProjectSummary, Task } from '../../types'
import {
  listTasks,
  groupTasksByStatus,
  type TaskStatus,
} from '../../api/projectTasks'
import { formatDateShort, isOverdue } from '../../utils/dates'

/**
 * Signature for persisting a task move. Exposed so the follow-up drag-and-drop
 * task can wire real persistence without changing the board's data contract.
 * Defaults to a no-op.
 */
type MoveTaskHandler = (
  taskId: string,
  targetStatus: TaskStatus,
  targetPosition: number,
) => void

const props = withDefaults(
  defineProps<{
    project: ProjectSummary
    /** Increment to force the board to reload tasks (e.g. after a modal save). */
    refreshKey?: number
    /**
     * Placeholder persistence hook for drag-and-drop (currently a no-op).
     * Called with the moved task id, the target status, and the target position
     * within that column.
     */
    onMoveTask?: MoveTaskHandler
  }>(),
  {
    refreshKey: 0,
    onMoveTask: () => {},
  },
)

const emit = defineEmits<{
  openTask: [taskId: string]
}>()

const tasks = ref<Task[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

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
      :class="{ empty: col.tasks.length === 0 }"
      data-drop-target
    >
      <div class="ptb-column-header">
        <span class="ptb-dot" :class="col.status"></span>
        <span class="ptb-column-label">{{ col.label }}</span>
        <span class="ptb-count">{{ col.tasks.length }}</span>
      </div>

      <div class="ptb-column-body">
        <div
          v-for="task in col.tasks"
          :key="task.id"
          class="ptb-card"
          :class="{ pinned: task.is_pinned }"
          @click="emit('openTask', task.id)"
        >
          <div class="ptb-card-title-row">
            <span class="ptb-card-title">{{ task.title }}</span>
            <span v-if="task.is_pinned" class="ptb-pin" title="Pinned"><i class="pi pi-bookmark" /></span>
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
                v-for="(initials, i) in assigneeInitials(task)"
                :key="initials + i"
                class="ptb-avatar"
                :title="task.assignees?.[i] ? `${task.assignees[i].first_name} ${task.assignees[i].last_name}` : assigneeName(task)"
              >{{ initials }}</span>
            </div>
          </div>
        </div>

        <!-- Empty column: drop-target placeholder (drag wiring is a later task) -->
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
.ptb-pin {
  color: var(--p-primary-color);
  font-size: 0.75rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
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
