<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { MyTask, Task, ProjectSummary } from '../types'
import { getMyTasks, createTask, updateTask } from '../api/tasks'
import { getProjects } from '../api/projects'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import TaskDetailModal from '../components/modals/TaskDetailModal.vue'

const { user } = useAuth()
const toast = useToast()
const tasks = ref<MyTask[]>([])
const loading = ref(true)
const taskModalVisible = ref(false)
const selectedTaskId = ref<string | null>(null)
const selectedProjectId = ref<string>('')
const collapsedProjects = ref<Set<string>>(new Set())
const expandedTasks = ref<Set<string>>(new Set())
const showCompleted = ref(false)

const showQuickAdd = ref(false)
const quickAddTitle = ref('')
const quickAddProjectId = ref('')
const todayStr = () => new Date().toISOString().split('T')[0]
const quickAddDueDate = ref(todayStr())
const quickAddSubmitting = ref(false)
const projects = ref<ProjectSummary[]>([])

const activeTasks = computed(() => tasks.value.filter(t => t.status !== 'done' && t.status !== 'canceled'))

const displayTasks = computed(() => showCompleted.value ? tasks.value : activeTasks.value)

const groupedByProject = computed(() => {
  const groups = new Map<string, { projectName: string; jobCode: string | null; tasks: MyTask[] }>()
  for (const task of displayTasks.value) {
    const key = task.project_id
    if (!groups.has(key)) {
      groups.set(key, {
        projectName: task.project_name || 'Unknown Project',
        jobCode: task.job_code,
        tasks: [],
      })
    }
    groups.get(key)!.tasks.push(task)
  }
  return groups
})

async function loadTasks() {
  if (!user.value) return
  try {
    tasks.value = await getMyTasks(user.value.id)
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

function toggleProject(projectId: string) {
  if (collapsedProjects.value.has(projectId)) {
    collapsedProjects.value.delete(projectId)
  } else {
    collapsedProjects.value.add(projectId)
  }
}

function toggleExpand(taskId: string, event: Event) {
  event.stopPropagation()
  if (expandedTasks.value.has(taskId)) {
    expandedTasks.value.delete(taskId)
  } else {
    expandedTasks.value.add(taskId)
  }
}

async function toggleDone(task: MyTask | Task, event: Event) {
  event.stopPropagation()
  const newStatus = task.status === 'done' ? 'todo' : 'done'
  try {
    await updateTask(task.id, { status: newStatus })
    await loadTasks()
  } catch (e) {
    toast.error(String(e))
  }
}

function openTask(task: MyTask | Task, projectId?: string) {
  selectedTaskId.value = task.id
  selectedProjectId.value = projectId || (task as MyTask).project_id
  taskModalVisible.value = true
}

function isOverdue(task: MyTask | Task): boolean {
  if (!task.due_date || task.status === 'done' || task.status === 'canceled') return false
  return new Date(task.due_date) < new Date(new Date().toDateString())
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function statusLabel(status: string): string {
  return status.replace('_', ' ')
}

async function loadProjects() {
  try {
    projects.value = await getProjects()
  } catch (e) {
    toast.error(String(e))
  }
}

function openQuickAdd() {
  showQuickAdd.value = true
  if (!projects.value.length) loadProjects()
}

async function submitQuickAdd() {
  if (!quickAddTitle.value.trim() || !quickAddProjectId.value) return
  quickAddSubmitting.value = true
  try {
    await createTask(quickAddProjectId.value, {
      title: quickAddTitle.value.trim(),
      due_date: quickAddDueDate.value || undefined,
      assignee_ids: user.value ? [user.value.id] : undefined,
    })
    quickAddTitle.value = ''
    quickAddDueDate.value = todayStr()
    showQuickAdd.value = false
    await loadTasks()
    toast.success('Task created')
  } catch (e) {
    toast.error(String(e))
  } finally {
    quickAddSubmitting.value = false
  }
}

onMounted(loadTasks)
</script>

<template>
  <div class="my-tasks">
    <div class="page-header">
      <h1>My Tasks</h1>
      <div class="header-actions">
        <span class="task-count">{{ activeTasks.length }} active</span>
        <button
          class="toggle-completed"
          :class="{ active: showCompleted }"
          @click="showCompleted = !showCompleted"
        >
          <i class="pi" :class="showCompleted ? 'pi-eye-slash' : 'pi-eye'" />
          {{ showCompleted ? 'Hide Completed' : 'Show Completed' }}
        </button>
        <button class="btn-add-task" @click="openQuickAdd">
          <i class="pi pi-plus" />
          Add Task
        </button>
      </div>
    </div>

    <!-- Quick Add Form -->
    <div v-if="showQuickAdd" class="quick-add-form">
      <div class="quick-add-row">
        <select v-model="quickAddProjectId" class="quick-add-select">
          <option value="" disabled>Select project...</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">
            {{ p.project_name }}{{ p.job_code ? ` (${p.job_code})` : '' }}
          </option>
        </select>
        <input
          v-model="quickAddTitle"
          class="quick-add-input"
          type="text"
          placeholder="Task title..."
          @keydown.enter="submitQuickAdd"
        />
        <input
          v-model="quickAddDueDate"
          class="quick-add-date"
          type="date"
        />
        <button
          class="quick-add-submit"
          :disabled="!quickAddTitle.trim() || !quickAddProjectId || quickAddSubmitting"
          @click="submitQuickAdd"
        >
          <i class="pi pi-check" />
        </button>
        <button class="quick-add-cancel" @click="showQuickAdd = false">
          <i class="pi pi-times" />
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading tasks...</div>

    <div v-else-if="displayTasks.length === 0" class="empty-state">
      <i class="pi pi-check-circle empty-icon" />
      <p>No tasks assigned to you</p>
    </div>

    <div v-else class="project-groups">
      <div
        v-for="[projectId, group] in groupedByProject"
        :key="projectId"
        class="project-group"
      >
        <button class="group-header" @click="toggleProject(projectId)">
          <i class="pi" :class="collapsedProjects.has(projectId) ? 'pi-chevron-right' : 'pi-chevron-down'" />
          <span class="project-name">{{ group.projectName }}</span>
          <span v-if="group.jobCode" class="job-code">{{ group.jobCode }}</span>
          <span class="group-count">{{ group.tasks.length }}</span>
        </button>

        <div v-if="!collapsedProjects.has(projectId)" class="task-list">
          <div v-for="task in group.tasks" :key="task.id" class="task-block">
            <div class="task-row" @click="openTask(task)">
              <button
                class="checkbox"
                :class="{ checked: task.status === 'done' }"
                title="Toggle complete"
                @click="toggleDone(task, $event)"
              >
                <i class="pi" :class="task.status === 'done' ? 'pi-check' : ''" />
              </button>
              <span class="task-title" :class="{ completed: task.status === 'done' }">{{ task.title }}</span>
              <button
                v-if="task.subtasks && task.subtasks.length"
                class="expand-btn"
                :title="expandedTasks.has(task.id) ? 'Collapse subtasks' : 'Expand subtasks'"
                @click="toggleExpand(task.id, $event)"
              >
                <i class="pi" :class="expandedTasks.has(task.id) ? 'pi-chevron-up' : 'pi-chevron-down'" />
                <span class="subtask-count">{{ task.subtasks.length }}</span>
              </button>
              <span class="spacer" />
              <span
                class="status-badge"
                :class="task.status"
              >
                {{ statusLabel(task.status) }}
              </span>
              <span
                v-if="task.due_date"
                class="due-date"
                :class="{ overdue: isOverdue(task) }"
              >
                {{ formatDate(task.due_date) }}
              </span>
            </div>

            <!-- Subtasks -->
            <div v-if="task.subtasks && task.subtasks.length && expandedTasks.has(task.id)" class="subtask-list">
              <div
                v-for="sub in task.subtasks"
                :key="sub.id"
                class="subtask-row"
                @click="openTask(sub, task.project_id)"
              >
                <button
                  class="checkbox checkbox-sm"
                  :class="{ checked: sub.status === 'done' }"
                  title="Toggle complete"
                  @click="toggleDone(sub, $event)"
                >
                  <i class="pi" :class="sub.status === 'done' ? 'pi-check' : ''" />
                </button>
                <span class="task-title subtask-title" :class="{ completed: sub.status === 'done' }">{{ sub.title }}</span>
                <span
                  v-if="sub.due_date"
                  class="due-date"
                  :class="{ overdue: isOverdue(sub) }"
                >
                  {{ formatDate(sub.due_date) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <TaskDetailModal
      v-model:visible="taskModalVisible"
      :task-id="selectedTaskId"
      :project-id="selectedProjectId"
      @saved="loadTasks"
      @deleted="loadTasks"
    />
  </div>
</template>

<style scoped>
.my-tasks {
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.task-count {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.toggle-completed {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  cursor: pointer;
}

.toggle-completed:hover {
  background: var(--p-content-hover-background);
}

.toggle-completed.active {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--p-text-muted-color);
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--p-text-muted-color);
}

.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
  display: block;
}

.empty-state p {
  font-size: 0.9375rem;
  margin: 0;
}

.project-groups {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.project-group {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  overflow: hidden;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--p-content-hover-background);
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--p-text-color);
  text-align: left;
}

.group-header:hover {
  background: var(--p-surface-200);
}

:root.p-dark .group-header:hover {
  background: var(--p-surface-700);
}

.group-header .pi {
  font-size: 0.625rem;
  color: var(--p-text-muted-color);
}

.project-name {
  font-weight: 600;
}

.job-code {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  font-family: monospace;
}

.group-count {
  margin-left: auto;
  font-size: 0.6875rem;
  background: var(--p-surface-300);
  color: var(--p-text-muted-color);
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
}

:root.p-dark .group-count {
  background: var(--p-surface-600);
}

.task-list {
  border-top: 1px solid var(--p-content-border-color);
}

.task-block {
  border-bottom: 1px solid var(--p-content-border-color);
}

.task-block:last-child {
  border-bottom: none;
}

.task-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  cursor: pointer;
  transition: background 0.1s;
}

.task-row:hover {
  background: var(--p-content-hover-background);
}

/* Checkbox */
.checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid var(--p-content-border-color);
  border-radius: 4px;
  background: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
  padding: 0;
}

.checkbox .pi {
  font-size: 0.625rem;
  color: #fff;
}

.checkbox:hover {
  border-color: var(--p-primary-color);
}

.checkbox.checked {
  background: var(--p-primary-color);
  border-color: var(--p-primary-color);
}

.checkbox-sm {
  width: 16px;
  height: 16px;
}

.checkbox-sm .pi {
  font-size: 0.5rem;
}

.task-title {
  font-size: 0.875rem;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spacer {
  flex: 1;
}

.task-title.completed {
  text-decoration: line-through;
  color: var(--p-text-muted-color);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: capitalize;
  white-space: nowrap;
}

.status-badge.todo {
  background: var(--p-surface-200);
  color: var(--p-text-muted-color);
}

:root.p-dark .status-badge.todo {
  background: var(--p-surface-600);
  color: var(--p-surface-100);
}

.status-badge.in_progress {
  background: #dbeafe;
  color: #1d4ed8;
}

:root.p-dark .status-badge.in_progress {
  background: #1e3a5f;
  color: #93c5fd;
}

.status-badge.blocked {
  background: #fef3c7;
  color: #92400e;
}

:root.p-dark .status-badge.blocked {
  background: #451a03;
  color: #fcd34d;
}

.status-badge.done {
  background: #dcfce7;
  color: #166534;
}

:root.p-dark .status-badge.done {
  background: #14532d;
  color: #86efac;
}

.status-badge.canceled {
  background: var(--p-surface-200);
  color: var(--p-text-muted-color);
  text-decoration: line-through;
}

.due-date {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

.due-date.overdue {
  color: #dc2626;
  font-weight: 600;
}

/* Expand button for subtasks */
.expand-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  background: none;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.25rem;
  padding: 0.125rem 0.375rem;
  cursor: pointer;
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
  transition: all 0.15s;
}

.expand-btn:hover {
  background: var(--p-content-hover-background);
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
}

.expand-btn .pi {
  font-size: 0.5rem;
}

.subtask-count {
  font-weight: 600;
}

/* Subtask rows */
.subtask-list {
  background: var(--p-content-hover-background);
  border-top: 1px solid var(--p-content-border-color);
}

.subtask-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 1rem 0.5rem 2.75rem;
  cursor: pointer;
  transition: background 0.1s;
  border-bottom: 1px solid var(--p-content-border-color);
}

.subtask-row:last-child {
  border-bottom: none;
}

.subtask-row:hover {
  background: var(--p-surface-200);
}

:root.p-dark .subtask-row:hover {
  background: var(--p-surface-700);
}

.subtask-title {
  font-size: 0.8125rem;
}

/* Add Task button */
.btn-add-task {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: none;
  border-radius: 0.375rem;
  background: var(--p-primary-color);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-add-task:hover {
  filter: brightness(1.1);
}

.btn-add-task .pi {
  font-size: 0.625rem;
}

/* Quick Add Form */
.quick-add-form {
  margin-bottom: 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 0.75rem;
  background: var(--p-content-background);
}

.quick-add-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.quick-add-select {
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
  min-width: 160px;
  max-width: 200px;
}

.quick-add-input {
  flex: 1;
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
}

.quick-add-input:focus,
.quick-add-select:focus,
.quick-add-date:focus {
  outline: none;
  border-color: var(--p-primary-color);
}

.quick-add-date {
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
  width: 140px;
}

.quick-add-submit,
.quick-add-cancel {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  cursor: pointer;
  flex-shrink: 0;
}

.quick-add-submit:hover:not(:disabled) {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.quick-add-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.quick-add-cancel:hover {
  background: var(--p-content-hover-background);
}

.quick-add-submit .pi,
.quick-add-cancel .pi {
  font-size: 0.75rem;
}
</style>
