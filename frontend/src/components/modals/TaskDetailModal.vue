<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import type { Task, TaskNote, Employee } from '../../types'
import { getTask, createTask, updateTask, deleteTask, addTaskNote, deleteTaskNote } from '../../api/tasks'
import { getEmployees } from '../../api/employees'
import { useToast } from '../../composables/useToast'
import { useAuth } from '../../composables/useAuth'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  taskId: string | null
  projectId: string
}>()

const emit = defineEmits<{
  saved: []
  deleted: []
}>()

const toast = useToast()
const { user } = useAuth()
const loading = ref(false)
const task = ref<Task | null>(null)
const employees = ref<Employee[]>([])
const newNote = ref('')
const noteSaving = ref(false)
const showDeleteConfirm = ref(false)

const statusOptions = [
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'done', label: 'Done' },
  { value: 'canceled', label: 'Canceled' },
]

const parentTaskId = ref<string | null>(null)
const newSubtaskTitle = ref('')
const showSubtaskForm = ref(false)
const subtaskSaving = ref(false)

const sortedNotes = computed(() => {
  if (!task.value?.notes) return []
  return [...task.value.notes].sort((a, b) => {
    const da = a.created_at ? new Date(a.created_at).getTime() : 0
    const db = b.created_at ? new Date(b.created_at).getTime() : 0
    return db - da
  })
})

watch(visible, async (val) => {
  if (!val || !props.taskId) return
  parentTaskId.value = null
  showDeleteConfirm.value = false
  loading.value = true
  try {
    const [t, emps] = await Promise.all([
      getTask(props.taskId),
      getEmployees(),
    ])
    task.value = t
    employees.value = emps
  } catch (e) {
    toast.error(String(e))
    visible.value = false
  } finally {
    loading.value = false
  }
})

async function patchField(field: string, value: unknown) {
  if (!task.value) return
  try {
    task.value = await updateTask(task.value.id, { [field]: value })
    emit('saved')
  } catch (e) {
    toast.error(String(e))
  }
}

function isAssigned(empId: string): boolean {
  return task.value?.assignees?.some(a => a.id === empId) ?? false
}

async function toggleAssignee(empId: string) {
  if (!task.value) return
  const current = task.value.assignees?.map(a => a.id) ?? []
  const next = isAssigned(empId)
    ? current.filter(id => id !== empId)
    : [...current, empId]
  try {
    task.value = await updateTask(task.value.id, { assignee_ids: next })
    emit('saved')
  } catch (e) {
    toast.error(String(e))
  }
}

async function submitNote() {
  if (!newNote.value.trim() || !task.value) return
  noteSaving.value = true
  try {
    await addTaskNote(task.value.id, { content: newNote.value, author_id: user.value?.id })
    newNote.value = ''
    task.value = await getTask(task.value.id)
  } catch (e) {
    toast.error(String(e))
  } finally {
    noteSaving.value = false
  }
}

async function removeNote(noteId: string) {
  if (!task.value) return
  try {
    await deleteTaskNote(noteId)
    task.value = await getTask(task.value.id)
  } catch (e) {
    toast.error(String(e))
  }
}

async function confirmDelete() {
  if (!task.value) return
  try {
    await deleteTask(task.value.id)
    toast.success('Task deleted')
    emit('deleted')
    visible.value = false
  } catch (e) {
    toast.error(String(e))
  }
}

async function addSubtask() {
  if (!newSubtaskTitle.value.trim() || !task.value) return
  subtaskSaving.value = true
  try {
    await createTask(task.value.project_id, {
      title: newSubtaskTitle.value,
      parent_id: task.value.id,
    })
    newSubtaskTitle.value = ''
    showSubtaskForm.value = false
    task.value = await getTask(task.value.id)
    emit('saved')
  } catch (e) {
    toast.error(String(e))
  } finally {
    subtaskSaving.value = false
  }
}

async function removeSubtask(subId: string) {
  try {
    await deleteTask(subId)
    if (task.value) task.value = await getTask(task.value.id)
    emit('saved')
  } catch (e) {
    toast.error(String(e))
  }
}

async function openSubtask(id: string) {
  parentTaskId.value = task.value?.id ?? null
  loading.value = true
  try {
    task.value = await getTask(id)
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

async function goBackToParent() {
  if (!parentTaskId.value) return
  loading.value = true
  try {
    task.value = await getTask(parentTaskId.value)
    parentTaskId.value = null
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :header="task?.title ?? 'Task'"
    :modal="true"
    :style="{ width: '640px' }"
  >
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="task" class="task-detail">
      <!-- Back to parent -->
      <button v-if="parentTaskId" class="btn btn-sm" @click="goBackToParent">
        <i class="pi pi-arrow-left" /> Back to parent task
      </button>

      <!-- Status -->
      <div class="field">
        <label>Status</label>
        <select :value="task.status" @change="patchField('status', ($event.target as HTMLSelectElement).value)">
          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>

      <!-- Dates -->
      <div class="field-group">
        <div class="field">
          <label>Start Date</label>
          <input
            type="date"
            :value="task.start_date?.split('T')[0] ?? ''"
            @change="patchField('start_date', ($event.target as HTMLInputElement).value || null)"
          />
        </div>
        <div class="field">
          <label>Due Date</label>
          <input
            type="date"
            :value="task.due_date?.split('T')[0] ?? ''"
            @change="patchField('due_date', ($event.target as HTMLInputElement).value || null)"
          />
        </div>
      </div>

      <!-- Assignees -->
      <div class="field">
        <label>Assignees</label>
        <div class="assignee-chips">
          <button
            v-for="emp in employees"
            :key="emp.id"
            class="chip"
            :class="{ active: isAssigned(emp.id) }"
            @click="toggleAssignee(emp.id)"
          >
            {{ emp.first_name }} {{ emp.last_name }}
          </button>
        </div>
      </div>

      <!-- Description -->
      <div v-if="task.description" class="field">
        <label>Description</label>
        <div class="description">{{ task.description }}</div>
      </div>

      <!-- Subtasks -->
      <div v-if="!task.parent_id" class="section">
        <div class="section-header">
          <label>Subtasks</label>
          <button class="btn-icon" :title="showSubtaskForm ? 'Cancel' : 'Add subtask'" @click="showSubtaskForm = !showSubtaskForm">
            <i class="pi" :class="showSubtaskForm ? 'pi-times' : 'pi-plus'" />
          </button>
        </div>
        <div v-if="showSubtaskForm" class="subtask-form">
          <input v-model="newSubtaskTitle" type="text" placeholder="Subtask title" class="subtask-input" @keyup.enter="addSubtask" />
          <button class="btn btn-sm btn-primary" :disabled="subtaskSaving || !newSubtaskTitle.trim()" @click="addSubtask">
            {{ subtaskSaving ? 'Adding...' : 'Add' }}
          </button>
        </div>
        <div v-if="task.subtasks && task.subtasks.length" class="subtask-list">
          <div
            v-for="sub in task.subtasks"
            :key="sub.id"
            class="subtask-item"
          >
            <i class="pi" :class="sub.status === 'done' ? 'pi-check-circle' : 'pi-circle'" @click="openSubtask(sub.id)" />
            <span class="subtask-title" @click="openSubtask(sub.id)">{{ sub.title }}</span>
            <span class="subtask-status">{{ sub.status.replace('_', ' ') }}</span>
            <button class="btn-remove-sm" title="Delete subtask" @click="removeSubtask(sub.id)">&times;</button>
          </div>
        </div>
        <div v-else-if="!showSubtaskForm" class="empty">No subtasks</div>
      </div>

      <!-- Notes -->
      <div class="section">
        <label>Notes</label>
        <div class="add-note">
          <textarea v-model="newNote" rows="2" placeholder="Add a note..." class="note-input" />
          <button class="btn btn-sm btn-primary" :disabled="noteSaving" @click="submitNote">
            {{ noteSaving ? 'Adding...' : 'Add' }}
          </button>
        </div>
        <div v-if="sortedNotes.length" class="notes-list">
          <div v-for="note in sortedNotes" :key="note.id" class="note-card">
            <div class="note-header">
              <span class="note-author">{{ note.author_name || 'Unknown' }}</span>
              <span class="note-date">{{ formatDateTime(note.created_at) }}</span>
              <button class="btn-remove" @click="removeNote(note.id)">&times;</button>
            </div>
            <div class="note-body">{{ note.content }}</div>
          </div>
        </div>
      </div>

      <!-- Delete -->
      <div class="delete-section">
        <button v-if="!showDeleteConfirm" class="btn btn-danger btn-sm" @click="showDeleteConfirm = true">
          <i class="pi pi-trash" /> Delete Task
        </button>
        <div v-else class="delete-confirm">
          <span>Delete this task?</span>
          <button class="btn btn-danger btn-sm" @click="confirmDelete">Yes, delete</button>
          <button class="btn btn-sm" @click="showDeleteConfirm = false">Cancel</button>
        </div>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.task-detail { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.field label, .section > label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 0.25rem; }
.field input, .field select { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.field-group { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }

.assignee-chips { display: flex; flex-wrap: wrap; gap: 0.375rem; }
.chip { padding: 0.25rem 0.625rem; border: 1px solid var(--p-content-border-color); border-radius: 9999px; font-size: 0.75rem; cursor: pointer; background: var(--p-content-background); color: var(--p-text-muted-color); transition: all 0.15s; }
.chip.active { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.chip:hover { border-color: var(--p-primary-color); }

.description { font-size: 0.8125rem; color: var(--p-text-muted-color); white-space: pre-wrap; padding: 0.5rem 0.75rem; background: var(--p-content-hover-background); border-radius: 0.375rem; }

.section-header { display: flex; align-items: center; gap: 0.25rem; }
.subtask-form { display: flex; gap: 0.375rem; align-items: center; margin-bottom: 0.5rem; }
.subtask-input { flex: 1; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.8125rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.subtask-list { display: flex; flex-direction: column; gap: 0.25rem; }
.subtask-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.375rem 0.5rem; font-size: 0.8125rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; transition: background 0.15s; }
.subtask-item:hover { background: var(--p-content-hover-background); }
.subtask-item .pi { font-size: 0.75rem; color: var(--p-text-muted-color); cursor: pointer; }
.subtask-title { flex: 1; cursor: pointer; }
.subtask-status { font-size: 0.6875rem; text-transform: uppercase; color: var(--p-text-muted-color); }
.btn-remove-sm { background: none; border: none; color: var(--p-text-muted-color); cursor: pointer; font-size: 0.875rem; padding: 0 0.25rem; }
.btn-remove-sm:hover { color: var(--p-red-600); }
.btn-icon { background: none; border: none; cursor: pointer; padding: 0.25rem; color: var(--p-text-muted-color); border-radius: 0.25rem; font-size: 0.875rem; }
.btn-icon:hover { background: var(--p-content-hover-background); color: var(--p-text-color); }
.empty { font-size: 0.8125rem; color: var(--p-text-muted-color); font-style: italic; }

.add-note { display: flex; flex-direction: column; gap: 0.375rem; margin-bottom: 0.5rem; }
.note-input { padding: 0.5rem 0.75rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; font-size: 0.8125rem; resize: vertical; background: var(--p-content-background); color: var(--p-text-color); font-family: inherit; }
.notes-list { display: flex; flex-direction: column; gap: 0.5rem; }
.note-card { border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; padding: 0.625rem; }
.note-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
.note-author { font-weight: 600; font-size: 0.75rem; }
.note-date { font-size: 0.6875rem; color: var(--p-text-muted-color); }
.note-body { font-size: 0.8125rem; color: var(--p-text-muted-color); white-space: pre-wrap; }
.btn-remove { background: none; border: none; color: var(--p-red-600); cursor: pointer; font-size: 1rem; margin-left: auto; padding: 0 0.25rem; }

.delete-section { margin-top: 0.5rem; padding-top: 0.75rem; border-top: 1px solid var(--p-content-border-color); }
.delete-confirm { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; }

.loading { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.btn { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.375rem 0.75rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.75rem; font-weight: 500; color: var(--p-text-color); }
.btn:hover { background: var(--p-content-hover-background); }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger { color: var(--p-red-600); border-color: var(--p-red-300); }
.btn-danger:hover { background: var(--p-red-50); }
</style>
