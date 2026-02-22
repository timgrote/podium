<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { ProjectSummary, ProjectNote, Task } from '../../types'
import { getProjectNotes, addProjectNote, deleteProjectNote } from '../../api/projects'
import { getProjectTasks, createTask, updateTask } from '../../api/tasks'
import { getEmployees } from '../../api/employees'
import TaskDetailModal from '../modals/TaskDetailModal.vue'
import type { Employee } from '../../types'
import { useToast } from '../../composables/useToast'
import { useAuth } from '../../composables/useAuth'

const props = defineProps<{
  project: ProjectSummary
}>()

const emit = defineEmits<{
  editProject: []
  deleteProject: []
  createContract: [projectId: string]
  editContract: [contractId: string]
  deleteContract: [contractId: string]
  createInvoice: [contractId: string]
  editInvoice: [invoiceId: string]
  deleteInvoice: [invoiceId: string]
  invoiceActions: [invoiceId: string]
  createProposal: [projectId: string]
  editProposal: [proposalId: string]
  deleteProposal: [proposalId: string]
  promoteProposal: [proposalId: string]
}>()

const toast = useToast()
const { user } = useAuth()
const activeTab = ref<'financial' | 'tasks' | 'notes'>('financial')

// Notes state
const notes = ref<ProjectNote[]>([])
const notesLoading = ref(false)
const newNote = ref('')
const noteSaving = ref(false)
const noteSearch = ref('')

const filteredNotes = computed(() => {
  const sorted = [...notes.value].sort((a, b) => {
    const da = a.created_at ? new Date(a.created_at).getTime() : 0
    const db = b.created_at ? new Date(b.created_at).getTime() : 0
    return db - da
  })
  if (!noteSearch.value.trim()) return sorted
  const q = noteSearch.value.toLowerCase()
  return sorted.filter(n => n.content.toLowerCase().includes(q))
})

// Tasks state
const tasks = ref<Task[]>([])
const tasksLoading = ref(false)
const showNewTaskForm = ref(false)
const newTaskTitle = ref('')
const newTaskDueDate = ref('')
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

// Load counts eagerly so tabs show badges before clicking
watch(() => props.project.id, async () => {
  await Promise.all([loadNotes(), loadTasks(), loadEmployees()])
}, { immediate: true })

async function loadEmployees() {
  try {
    employees.value = await getEmployees()
  } catch (e) {
    console.error('Failed to load employees:', e)
  }
}

function toggleNewTaskAssignee(empId: string) {
  const idx = newTaskAssigneeIds.value.indexOf(empId)
  if (idx >= 0) {
    newTaskAssigneeIds.value.splice(idx, 1)
  } else {
    newTaskAssigneeIds.value.push(empId)
  }
}

async function loadNotes() {
  notesLoading.value = true
  try {
    notes.value = await getProjectNotes(props.project.id)
  } catch (e) {
    console.error('Failed to load notes:', e)
  } finally {
    notesLoading.value = false
  }
}

async function submitNote() {
  if (!newNote.value.trim()) return
  noteSaving.value = true
  try {
    await addProjectNote(props.project.id, { content: newNote.value, author_id: user.value?.id })
    newNote.value = ''
    toast.success('Note added')
    await loadNotes()
  } catch (e) {
    toast.error(String(e))
  } finally {
    noteSaving.value = false
  }
}

async function removeNote(noteId: string) {
  try {
    await deleteProjectNote(noteId)
    toast.success('Note deleted')
    await loadNotes()
  } catch (e) {
    toast.error(String(e))
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
    newTaskDueDate.value = ''
    newTaskDescription.value = ''
    newTaskAssigneeIds.value = []
    showNewTaskForm.value = false
    toast.success('Task created')
    await loadTasks()
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
}

function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false
  return new Date(dateStr) < new Date()
}

function getInitials(assignees: Task['assignees']): string[] {
  if (!assignees) return []
  return assignees.map(a => {
    const f = a.first_name?.[0] ?? ''
    const l = a.last_name?.[0] ?? ''
    return `${f}${l}`.toUpperCase() || '?'
  })
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString()
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

const taskStatusIcon: Record<string, string> = {
  todo: 'pi-circle',
  in_progress: 'pi-spin pi-spinner',
  blocked: 'pi-ban',
  done: 'pi-check-circle',
  canceled: 'pi-times-circle',
}
</script>

<template>
  <div class="project-detail">
    <div class="detail-header">
      <div class="detail-meta">
        <span v-if="project.location" class="meta-item">
          <i class="pi pi-map-marker" /> {{ project.location }}
        </span>
        <span v-if="project.pm_name" class="meta-item">
          <i class="pi pi-user" /> {{ project.pm_name }}
        </span>
      </div>
      <div class="detail-actions">
      </div>
    </div>

    <div class="tabs">
      <button
        class="tab"
        :class="{ active: activeTab === 'financial' }"
        @click="activeTab = 'financial'"
      >
        Financial
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'tasks' }"
        @click="activeTab = 'tasks'"
      >
        Tasks <span v-if="totalTaskCount" class="tab-count">({{ totalTaskCount }})</span>
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'notes' }"
        @click="activeTab = 'notes'"
      >
        Notes <span v-if="notes.length" class="tab-count">({{ notes.length }})</span>
      </button>
    </div>

    <div v-if="activeTab === 'financial'" class="tab-content">
      <!-- Contracts -->
      <div class="section">
        <div class="section-header">
          <h4>Contracts</h4>
          <button class="btn btn-sm btn-primary" @click="emit('createContract', project.id)">
            <i class="pi pi-plus" /> Add
          </button>
        </div>
        <div v-if="project.contracts.length === 0" class="empty">No contracts</div>
        <div v-for="contract in project.contracts" :key="contract.id" class="sub-card">
          <div class="sub-card-header">
            <span class="sub-card-title">{{ formatCurrency(contract.total_amount) }}</span>
            <span v-if="contract.signed_at" class="sub-card-date">
              Signed {{ formatDate(contract.signed_at) }}
            </span>
            <div class="sub-card-actions">
              <button class="btn-icon" title="Create Invoice" @click="emit('createInvoice', contract.id)">
                <i class="pi pi-file" />
              </button>
              <button class="btn-icon" title="Edit" @click="emit('editContract', contract.id)">
                <i class="pi pi-pencil" />
              </button>
              <button class="btn-icon" title="Delete" @click="emit('deleteContract', contract.id)">
                <i class="pi pi-trash" />
              </button>
            </div>
          </div>
          <div v-if="contract.tasks.length" class="task-table">
            <div class="task-row task-header-row">
              <span class="task-name">Task</span>
              <span class="task-amount">Fee</span>
              <span class="task-billed">Billed</span>
              <span class="task-pct">%</span>
            </div>
            <div v-for="task in contract.tasks" :key="task.id" class="task-row">
              <span class="task-name">{{ task.name }}</span>
              <span class="task-amount">{{ formatCurrency(task.amount) }}</span>
              <span class="task-billed">{{ formatCurrency(task.billed_amount) }}</span>
              <span class="task-pct">{{ formatPercent(task.billed_percent) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Invoices -->
      <div class="section">
        <div class="section-header">
          <h4>Invoices</h4>
        </div>
        <div v-if="project.invoices.length === 0" class="empty">No invoices</div>
        <div v-for="invoice in project.invoices" :key="invoice.id" class="sub-card">
          <div class="sub-card-header">
            <span class="sub-card-title">{{ invoice.invoice_number }}</span>
            <span class="sub-card-amount">{{ formatCurrency(invoice.total_due) }}</span>
            <span
              class="status-pill"
              :class="{
                sent: invoice.sent_status === 'sent',
                paid: invoice.paid_status === 'paid',
              }"
            >
              {{ invoice.paid_status === 'paid' ? 'Paid' : invoice.sent_status === 'sent' ? 'Sent' : 'Draft' }}
            </span>
            <div class="sub-card-actions">
              <button class="btn-icon" title="Actions" @click="emit('invoiceActions', invoice.id)">
                <i class="pi pi-ellipsis-h" />
              </button>
              <button class="btn-icon" title="Edit" @click="emit('editInvoice', invoice.id)">
                <i class="pi pi-pencil" />
              </button>
              <button class="btn-icon" title="Delete" @click="emit('deleteInvoice', invoice.id)">
                <i class="pi pi-trash" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Proposals -->
      <div class="section">
        <div class="section-header">
          <h4>Proposals</h4>
          <button class="btn btn-sm btn-primary" @click="emit('createProposal', project.id)">
            <i class="pi pi-plus" /> Add
          </button>
        </div>
        <div v-if="project.proposals.length === 0" class="empty">No proposals</div>
        <div v-for="proposal in project.proposals" :key="proposal.id" class="sub-card">
          <div class="sub-card-header">
            <span class="sub-card-title">{{ formatCurrency(proposal.total_fee) }}</span>
            <span
              class="status-pill"
              :class="{ sent: proposal.status === 'sent', accepted: proposal.status === 'accepted' }"
            >
              {{ proposal.status }}
            </span>
            <div class="sub-card-actions">
              <button
                v-if="proposal.status !== 'accepted'"
                class="btn-icon"
                title="Promote to Contract"
                @click="emit('promoteProposal', proposal.id)"
              >
                <i class="pi pi-arrow-up" />
              </button>
              <button class="btn-icon" title="Edit" @click="emit('editProposal', proposal.id)">
                <i class="pi pi-pencil" />
              </button>
              <button class="btn-icon" title="Delete" @click="emit('deleteProposal', proposal.id)">
                <i class="pi pi-trash" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'tasks'" class="tab-content">
      <div class="section">
        <div class="section-header tasks-header">
          <h4>Tasks</h4>
          <button class="btn-icon" :title="showNewTaskForm ? 'Cancel' : 'Add task'" @click="showNewTaskForm = !showNewTaskForm">
            <i class="pi" :class="showNewTaskForm ? 'pi-times' : 'pi-plus'" />
          </button>
        </div>

        <!-- Inline new task form -->
        <div v-if="showNewTaskForm" class="new-task-form">
          <input v-model="newTaskTitle" type="text" placeholder="Task title" class="new-task-input" />
          <div class="new-task-row">
            <input v-model="newTaskDueDate" type="date" class="new-task-date" />
            <button class="btn btn-sm btn-primary" :disabled="newTaskSaving || !newTaskTitle.trim()" @click="submitNewTask">
              {{ newTaskSaving ? 'Creating...' : 'Create' }}
            </button>
          </div>
          <textarea v-model="newTaskDescription" rows="2" placeholder="Description (optional)" class="new-task-desc" />
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
        </div>

        <div v-if="tasksLoading" class="empty">Loading tasks...</div>
        <div v-else-if="tasks.length === 0 && !showNewTaskForm" class="empty">No tasks</div>
        <template v-else>
          <!-- Active tasks -->
          <div v-if="activeTasks.length" class="tasks-list">
            <template v-for="task in activeTasks" :key="task.id">
              <div class="task-item clickable" @click="openTaskDetail(task.id)">
                <span class="task-checkbox" :class="{ checked: task.status === 'done' }" @click.stop="toggleTaskDone(task.id, task.status)">
                  <i v-if="task.status === 'done'" class="pi pi-check" />
                </span>
                <span class="task-title">{{ task.title }}</span>
                <span v-if="task.assignees?.length" class="task-assignees">
                  <span v-for="initials in getInitials(task.assignees)" :key="initials" class="initials-badge">{{ initials }}</span>
                </span>
                <span class="task-status-label">{{ task.status.replace('_', ' ') }}</span>
                <span v-if="task.due_date" class="task-due" :class="{ overdue: isOverdue(task.due_date) && task.status !== 'done' }">
                  {{ formatDate(task.due_date) }}
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
                  <span v-if="sub.due_date" class="task-due" :class="{ overdue: isOverdue(sub.due_date) && sub.status !== 'done' }">
                    {{ formatDate(sub.due_date) }}
                  </span>
                </div>
              </div>
            </template>
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
        @saved="loadTasks"
        @deleted="loadTasks"
      />
    </div>

    <div v-if="activeTab === 'notes'" class="tab-content">
      <div class="add-note">
        <textarea v-model="newNote" rows="2" placeholder="Add a note..." class="note-input" />
        <button class="btn btn-sm btn-primary" :disabled="noteSaving" @click="submitNote">
          {{ noteSaving ? 'Adding...' : 'Add Note' }}
        </button>
      </div>

      <div v-if="notes.length > 1" class="note-search">
        <i class="pi pi-search" />
        <input
          v-model="noteSearch"
          type="text"
          placeholder="Search notes..."
        />
        <button v-if="noteSearch" class="search-clear" @click="noteSearch = ''">
          <i class="pi pi-times" />
        </button>
      </div>

      <div v-if="notesLoading" class="empty">Loading notes...</div>
      <div v-else-if="filteredNotes.length === 0 && notes.length > 0" class="empty">No matching notes</div>
      <div v-else-if="notes.length === 0 && !notesLoading" class="empty">No notes yet</div>
      <div v-else class="notes-list">
        <div v-for="note in filteredNotes" :key="note.id" class="note-card">
          <div class="note-header">
            <img v-if="note.author_avatar_url" :src="note.author_avatar_url" class="note-avatar" />
            <span class="note-author">{{ note.author_name || 'Unknown' }}</span>
            <span class="note-date">{{ formatDateTime(note.created_at) }}</span>
            <button class="btn-remove" @click="removeNote(note.id)">&times;</button>
          </div>
          <div class="note-body">{{ note.content }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.project-detail {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-meta {
  display: flex;
  gap: 1rem;
}

.meta-item {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.detail-actions {
  display: flex;
  gap: 0.5rem;
}

.tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--p-content-border-color);
}

.tab {
  padding: 0.5rem 1rem;
  background: none;
  border: none;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
}

.tab.active {
  color: var(--p-text-color);
  border-bottom-color: var(--p-primary-color);
}

.tab-count {
  color: var(--p-text-muted-color);
  font-weight: 400;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.sub-card {
  background: var(--p-content-hover-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
}

.sub-card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.sub-card-title {
  font-weight: 600;
  font-size: 0.875rem;
}

.sub-card-amount {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.sub-card-date {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.sub-card-actions {
  margin-left: auto;
  display: flex;
  gap: 0.25rem;
}

.status-pill {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  background: var(--p-content-hover-background);
  color: var(--p-text-muted-color);
  font-weight: 600;
}

.status-pill.sent {
  background: var(--p-blue-100);
  color: var(--p-blue-700);
}

.status-pill.paid,
.status-pill.accepted {
  background: var(--p-green-100);
  color: var(--p-green-700);
}

.task-table {
  margin-top: 0.5rem;
}

.task-row {
  display: grid;
  grid-template-columns: 1fr 6rem 6rem 4rem;
  gap: 0.5rem;
  padding: 0.25rem 0;
  font-size: 0.8125rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.task-header-row {
  font-weight: 600;
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--p-content-border-color);
}

.task-amount,
.task-billed,
.task-pct {
  text-align: right;
}

.empty {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

/* Tasks */
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

.task-due {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.task-due.overdue {
  color: var(--p-red-600);
  font-weight: 600;
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

.new-task-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
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

/* Notes */
.add-note {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.note-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  resize: vertical;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-family: inherit;
}

.note-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.375rem 0.75rem;
}

.note-search i {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.note-search input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 0.8125rem;
  background: transparent;
  color: var(--p-text-color);
}

.search-clear {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.125rem;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  display: flex;
  align-items: center;
}

.search-clear:hover {
  color: var(--p-text-color);
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.note-card {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.625rem;
}

.note-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.note-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  object-fit: cover;
}

.note-author {
  font-weight: 600;
  font-size: 0.75rem;
}

.note-date {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.note-body {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  white-space: pre-wrap;
}

.btn-remove {
  background: none;
  border: none;
  color: var(--p-red-600);
  cursor: pointer;
  font-size: 1rem;
  margin-left: auto;
  padding: 0 0.25rem;
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

.btn-danger {
  color: var(--p-red-600);
  border-color: var(--p-red-300);
}

.btn-danger:hover {
  background: var(--p-red-50);
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
</style>
