<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { ProjectSummary, Task, Employee } from '../../types'
import { getProjectTasks, createTask, updateTask } from '../../api/tasks'
import { uploadImage } from '../../api/tasks'
import { getEmployees } from '../../api/employees'
import { useToast } from '../../composables/useToast'
import { useAuth } from '../../composables/useAuth'
import { formatDate, isOverdue, todayStr } from '../../utils/dates'
import { copyLink } from '../../utils/clipboard'
import TaskDetailModal from '../modals/TaskDetailModal.vue'
import { useProjectTasks } from '../../composables/useProjectTasks'

const props = defineProps<{
  project: ProjectSummary
  autoOpenTaskId?: string | null
}>()

const emit = defineEmits<{
  refreshProject: []
  entityClicked: [entityType: string, entityId: string]
  taskModalClosed: []
}>()

const toast = useToast()
const { user } = useAuth()

// Tasks state
const tasks = ref<Task[]>([])
const tasksLoading = ref(false)
const showNewTaskForm = ref(false)
const newTaskTitle = ref('')
const newTaskDueDate = ref(todayStr())
const newTaskDescription = ref('')
const newTaskSaving = ref(false)
const newTaskAssigneeIds = ref<string[]>([])
const employees = ref<Employee[]>([])
const showCompletedTasks = ref(false)

// Task detail modal
const taskModalVisible = ref(false)
const selectedTaskId = ref<string | null>(null)

const activeTasks = computed(() =>
  tasks.value.filter(t => t.status !== 'done' && t.status !== 'canceled')
)

const { searchQuery, sortField, sortOrder, toggleSort, filteredTasks } = useProjectTasks(activeTasks)

const completedTasks = computed(() =>
  tasks.value.filter(t => t.status === 'done' || t.status === 'canceled')
)

const totalTaskCount = computed(() => {
  let count = tasks.value.length
  for (const t of tasks.value) {
    if (t.subtasks) count += t.subtasks.length
  }
  return count
})

// Load tasks and employees when project changes
watch(() => props.project.id, async () => {
  await Promise.all([loadTasks(), loadEmployees()])
}, { immediate: true })

// Deep-link: auto-open task modal when autoOpenTaskId is set
watch(() => props.autoOpenTaskId, (taskId) => {
  if (taskId && tasks.value.length > 0) {
    openTaskDetail(taskId)
  }
})

// Wait for tasks to load before opening deep-linked task
watch(() => tasks.value.length, (len) => {
  if (len > 0 && props.autoOpenTaskId) {
    openTaskDetail(props.autoOpenTaskId)
  }
})

watch(taskModalVisible, (visible) => {
  if (!visible) {
    emit('taskModalClosed')
  }
})

async function loadEmployees() {
  try {
    employees.value = await getEmployees()
  } catch (e) {
    console.error('Failed to load employees:', e)
  }
}

async function loadTasks() {
  tasksLoading.value = true
  try {
    tasks.value = await getProjectTasks(props.project.id)
  } catch (e) {
    console.error('Failed to load tasks:', e)
  } finally {
    tasksLoading.value = false
  }
}

async function submitNewTask() {
  if (!newTaskTitle.value.trim()) return
  newTaskSaving.value = true
  try {
    await createTask(props.project.id, {
      title: newTaskTitle.value,
      due_date: newTaskDueDate.value || undefined,
      description: newTaskDescription.value || undefined,
      assignee_ids: newTaskAssigneeIds.value.length ? newTaskAssigneeIds.value : undefined,
    })
    newTaskTitle.value = ''
    newTaskDueDate.value = todayStr()
    newTaskDescription.value = ''
    newTaskAssigneeIds.value = []
    showNewTaskForm.value = false
    toast.success('Task created')
    await loadTasks()
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  } finally {
    newTaskSaving.value = false
  }
}

async function toggleTaskDone(taskId: string, currentStatus: string) {
  const newStatus = currentStatus === 'done' ? 'todo' : 'done'
  try {
    await updateTask(taskId, { status: newStatus })
    await loadTasks()
    emit('refreshProject')
    if (newStatus === 'done') {
      showCompletedTasks.value = true
    }
  } catch (e) {
    toast.error(String(e))
  }
}

function openTaskDetail(taskId: string) {
  selectedTaskId.value = taskId
  taskModalVisible.value = true
  emit('entityClicked', 'task', taskId)
}

function toggleNewTaskAssignee(empId: string) {
  const idx = newTaskAssigneeIds.value.indexOf(empId)
  if (idx >= 0) {
    newTaskAssigneeIds.value.splice(idx, 1)
  } else {
    newTaskAssigneeIds.value.push(empId)
  }
}

function openDatePicker(event: MouseEvent) {
  const el = event.currentTarget as HTMLElement
  const input = el.querySelector('input[type="date"]') as HTMLInputElement | null
  if (input) {
    try { input.showPicker() } catch { input.focus(); input.click() }
  }
}

async function inlineDateChange(taskId: string, event: Event) {
  const input = event.target as HTMLInputElement
  const newDate = input.value || null
  try {
    await updateTask(taskId, { due_date: newDate })
    await loadTasks()
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  }
}

function getInitials(assignees: Task['assignees']): string[] {
  if (!assignees) return []
  return assignees.map(a => {
    const f = a.first_name?.[0] ?? ''
    const l = a.last_name?.[0] ?? ''
    return `${f}${l}`.toUpperCase() || '?'
  })
}

async function handlePasteImage(event: ClipboardEvent, targetRef: typeof newTaskDescription) {
  const items = event.clipboardData?.files
  if (!items?.length) return
  const imageFile = Array.from(items).find(f => f.type.startsWith('image/'))
  if (!imageFile) return

  event.preventDefault()
  try {
    const { url } = await uploadImage(imageFile)
    const textarea = event.target as HTMLTextAreaElement
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const before = targetRef.value.slice(0, start)
    const after = targetRef.value.slice(end)
    targetRef.value = before + `![image](${url})` + after
  } catch (e) {
    toast.error('Image upload failed: ' + String(e))
  }
}

function onTaskDescPaste(event: ClipboardEvent) {
  handlePasteImage(event, newTaskDescription)
}

defineExpose({ totalTaskCount, loadTasks })
</script>

<template>
  <div class="section">
    <div class="section-header tasks-header">
      <h4>Tasks</h4>
      <button class="btn-icon" :title="showNewTaskForm ? 'Cancel' : 'Add task'" @click="showNewTaskForm = !showNewTaskForm; if (showNewTaskForm && user) newTaskAssigneeIds = [user.id]">
        <i class="pi" :class="showNewTaskForm ? 'pi-times' : 'pi-plus'" />
      </button>
    </div>

    <!-- Inline new task form -->
    <div v-if="showNewTaskForm" class="new-task-form">
      <input v-model="newTaskTitle" type="text" placeholder="Task title" class="new-task-input" />
      <input v-model="newTaskDueDate" type="date" class="new-task-date" />
      <textarea v-model="newTaskDescription" rows="2" placeholder="Description (optional)" class="new-task-desc" @paste="onTaskDescPaste" />
      <div v-if="employees.length" class="new-task-assignees">
        <label class="new-task-label">Assign to</label>
        <div class="assignee-chips">
          <button
            v-for="emp in employees"
            :key="emp.id"
            class="chip"
            :class="{ active: newTaskAssigneeIds.includes(emp.id) }"
            @click="toggleNewTaskAssignee(emp.id)"
          >
            {{ emp.first_name }} {{ emp.last_name }}
          </button>
        </div>
      </div>
      <button class="btn btn-sm btn-primary" :disabled="newTaskSaving || !newTaskTitle.trim()" @click="submitNewTask">
        {{ newTaskSaving ? 'Creating...' : 'Create' }}
      </button>
    </div>

    <!-- Task search -->
    <div v-if="!tasksLoading && activeTasks.length > 0" class="task-search-bar">
      <i class="pi pi-search" />
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search tasks..."
      />
      <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''">
        <i class="pi pi-times" />
      </button>
    </div>

    <!-- Column headers -->
    <div v-if="!tasksLoading && activeTasks.length > 0" class="task-column-headers">
      <div class="col-checkbox"></div>
      <div class="col-name sortable" @click="toggleSort('title')">
        Name
        <i v-if="sortField === 'title'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
      <div class="col-assignee sortable" @click="toggleSort('assignee')">
        Assignee
        <i v-if="sortField === 'assignee'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
      <div class="col-status">Status</div>
      <div class="col-link"></div>
      <div class="col-due sortable" @click="toggleSort('due_date')">
        Due
        <i v-if="sortField === 'due_date'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
    </div>

    <div v-if="tasksLoading" class="empty">Loading tasks...</div>
    <div v-else-if="tasks.length === 0 && !showNewTaskForm" class="empty">No tasks</div>
    <template v-else>
      <!-- Active tasks -->
      <div v-if="filteredTasks.length" class="tasks-list">
        <template v-for="task in filteredTasks" :key="task.id">
          <div class="task-item clickable" @click="openTaskDetail(task.id)">
            <span class="task-checkbox" :class="{ checked: task.status === 'done' }" @click.stop="toggleTaskDone(task.id, task.status)">
              <i v-if="task.status === 'done'" class="pi pi-check" />
            </span>
            <span class="task-title">{{ task.title }}</span>
            <span v-if="task.assignees?.length" class="task-assignees">
              <span v-for="initials in getInitials(task.assignees)" :key="initials" class="initials-badge">{{ initials }}</span>
            </span>
            <span class="task-status-label">{{ task.status.replace('_', ' ') }}</span>
            <button class="btn-copy-link" title="Copy link" @click.stop="copyLink(`/projects/${project.project_number}/tasks/${task.id}`)">
              <i class="pi pi-link" />
            </button>
            <span class="task-due-inline" :class="{ overdue: isOverdue(task.due_date) && task.status !== 'done' }" @click.stop="openDatePicker">
              <span v-if="task.due_date">{{ formatDate(task.due_date) }}</span>
              <span v-else class="no-date-hint"><i class="pi pi-calendar" /></span>
              <input type="date" class="inline-date-input" :value="task.due_date || ''" @change="inlineDateChange(task.id, $event)" />
            </span>
          </div>
          <!-- Subtasks -->
          <div v-if="task.subtasks?.length" class="subtask-group">
            <div
              v-for="sub in task.subtasks"
              :key="sub.id"
              class="task-item clickable subtask"
              @click="openTaskDetail(sub.id)"
            >
              <span class="task-checkbox" :class="{ checked: sub.status === 'done' }" @click.stop="toggleTaskDone(sub.id, sub.status)">
                <i v-if="sub.status === 'done'" class="pi pi-check" />
              </span>
              <span class="task-title">{{ sub.title }}</span>
              <span class="task-status-label">{{ sub.status.replace('_', ' ') }}</span>
              <span class="task-due-inline" :class="{ overdue: isOverdue(sub.due_date) && sub.status !== 'done' }" @click.stop="openDatePicker">
                <span v-if="sub.due_date">{{ formatDate(sub.due_date) }}</span>
                <span v-else class="no-date-hint"><i class="pi pi-calendar" /></span>
                <input type="date" class="inline-date-input" :value="sub.due_date || ''" @change="inlineDateChange(sub.id, $event)" />
              </span>
            </div>
          </div>
        </template>
      </div>
      <div v-if="activeTasks.length && !filteredTasks.length" class="empty">
        No tasks matching "{{ searchQuery }}"
      </div>

      <!-- Completed tasks -->
      <div v-if="completedTasks.length" class="completed-section">
        <button class="completed-toggle" @click="showCompletedTasks = !showCompletedTasks">
          <i class="pi" :class="showCompletedTasks ? 'pi-chevron-down' : 'pi-chevron-right'" />
          Completed ({{ completedTasks.length }})
        </button>
        <div v-if="showCompletedTasks" class="tasks-list">
          <template v-for="task in completedTasks" :key="task.id">
            <div class="task-item clickable done" @click="openTaskDetail(task.id)">
              <span class="task-checkbox checked" @click.stop="toggleTaskDone(task.id, task.status)">
                <i class="pi pi-check" />
              </span>
              <span class="task-title">{{ task.title }}</span>
              <span class="task-status-label">{{ task.status.replace('_', ' ') }}</span>
            </div>
            <div v-if="task.subtasks?.length" class="subtask-group">
              <div
                v-for="sub in task.subtasks"
                :key="sub.id"
                class="task-item clickable subtask done"
                @click="openTaskDetail(sub.id)"
              >
                <span class="task-checkbox checked" @click.stop="toggleTaskDone(sub.id, sub.status)">
                  <i class="pi pi-check" />
                </span>
                <span class="task-title">{{ sub.title }}</span>
                <span class="task-status-label">{{ sub.status.replace('_', ' ') }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </template>
  </div>

  <TaskDetailModal
    v-model:visible="taskModalVisible"
    :task-id="selectedTaskId"
    :project-id="project.id"
    @saved="loadTasks(); emit('refreshProject')"
    @deleted="loadTasks(); emit('refreshProject')"
  />
</template>

<style scoped>
.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0;
  font-size: 0.8125rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.task-item.clickable {
  cursor: pointer;
  padding: 0.375rem 0.25rem;
  border-radius: 0.25rem;
  border-bottom: none;
  margin-bottom: 1px;
}

.task-item.clickable:hover {
  background: var(--p-content-hover-background);
}

.task-item.done {
  opacity: 0.6;
}

.tasks-header {
  justify-content: flex-start;
  gap: 0.25rem;
}

.task-checkbox {
  width: 16px;
  height: 16px;
  border: 1.5px solid var(--p-content-border-color);
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
}

.task-checkbox:hover {
  border-color: var(--p-primary-color);
}

.task-checkbox.checked {
  background: var(--p-primary-color);
  border-color: var(--p-primary-color);
}

.task-checkbox .pi {
  font-size: 0.5625rem;
  color: #fff;
}

.task-title {
  flex: 1;
}

.task-assignees {
  display: flex;
  gap: 0.125rem;
}

.initials-badge {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--p-primary-color);
  color: #fff;
  font-size: 0.5625rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.task-status-label {
  font-size: 0.6875rem;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
  letter-spacing: 0.05em;
}

.task-due-inline {
  position: relative;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.task-due-inline:hover {
  color: var(--p-primary-color);
}

.task-due-inline.overdue {
  color: var(--p-red-600);
  font-weight: 600;
}

.task-due-inline.overdue:hover {
  color: var(--p-red-700);
}

.inline-date-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  width: 100%;
  cursor: pointer;
  font-size: 0.75rem;
}

.no-date-hint {
  color: var(--p-surface-400);
  font-size: 0.75rem;
}

.no-date-hint:hover {
  color: var(--p-primary-color);
}

.subtask-group {
  padding-left: 1.5rem;
}

.subtask {
  font-size: 0.75rem;
}

.new-task-form {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  margin-bottom: 0.75rem;
  background: var(--p-content-hover-background);
}

.new-task-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
}

.new-task-date {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
}

.new-task-desc {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  resize: vertical;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  font-family: inherit;
}

.new-task-assignees {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.new-task-label {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.assignee-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.chip {
  padding: 0.25rem 0.625rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 9999px;
  font-size: 0.75rem;
  cursor: pointer;
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  transition: all 0.15s;
}

.chip.active {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.chip:hover {
  border-color: var(--p-primary-color);
}

.completed-section {
  margin-top: 0.5rem;
}

.completed-toggle {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  background: none;
  border: none;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
  padding: 0.25rem 0;
  font-weight: 500;
}

.completed-toggle:hover {
  color: var(--p-text-color);
}

.completed-toggle .pi {
  font-size: 0.625rem;
}

.btn-copy-link {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.125rem;
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
  opacity: 0;
  transition: opacity 0.15s;
}

.task-item:hover .btn-copy-link {
  opacity: 1;
}

.btn-copy-link:hover {
  color: var(--p-primary-color);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.section-header h4 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.empty {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all 0.15s;
  color: var(--p-text-color);
}

.btn:hover {
  background: var(--p-content-hover-background);
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.btn-primary {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.btn-primary:hover {
  background: var(--p-primary-hover-color);
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--p-text-muted-color);
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.btn-icon:hover {
  background: var(--p-content-hover-background);
  color: var(--p-text-color);
}

.task-search-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.5rem;
}

.task-search-bar i {
  color: var(--p-text-muted-color);
}

.task-search-bar input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 0.8125rem;
  background: transparent;
  color: var(--p-text-color);
}

.task-search-bar .search-clear {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.125rem;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  display: flex;
  align-items: center;
}

.task-search-bar .search-clear:hover {
  color: var(--p-text-color);
}

.task-column-headers {
  display: flex;
  align-items: center;
  padding: 0.375rem 0.25rem;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.025em;
  gap: 0.5rem;
  border-bottom: 1px solid var(--p-content-border-color);
  margin-bottom: 0.25rem;
}

.task-column-headers .sortable {
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.task-column-headers .sortable:hover {
  color: var(--p-text-color);
}

.task-column-headers .sortable .pi {
  font-size: 0.5625rem;
}

.col-checkbox { width: 16px; flex-shrink: 0; }
.col-name { flex: 1; min-width: 0; }
.col-assignee { width: 4.5rem; flex-shrink: 0; }
.col-status { width: 5rem; flex-shrink: 0; }
.col-link { width: 1.25rem; flex-shrink: 0; }
.col-due { width: 5rem; flex-shrink: 0; text-align: right; justify-content: flex-end; }
</style>
