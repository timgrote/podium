<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import type { Task, Employee } from '../../types'
import { getTask, createTask, updateTask, deleteTask, addTaskNote, updateTaskNote, deleteTaskNote, uploadImage } from '../../api/tasks'
import { getEmployees } from '../../api/employees'
import { useToast } from '../../composables/useToast'
import { useAuth } from '../../composables/useAuth'
import RichText from '../RichText.vue'
import { formatDateTime } from '../../utils/dates'

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
const saving = ref(false)
const task = ref<Task | null>(null)
const employees = ref<Employee[]>([])
const newNote = ref('')
const noteSaving = ref(false)
const imageUploading = ref(false)
const showDeleteConfirm = ref(false)

// Local form state (buffered until Save)
const form = ref({
  title: '',
  description: null as string | null,
  status: 'todo',
  priority: null as number | null,
  start_date: null as string | null,
  due_date: null as string | null,
  assignee_ids: [] as string[],
})
function populateForm(t: Task) {
  form.value = {
    title: t.title,
    description: t.description || null,
    status: t.status,
    priority: t.priority ?? null,
    start_date: t.start_date?.split('T')[0] ?? null,
    due_date: t.due_date?.split('T')[0] ?? null,
    assignee_ids: t.assignees?.map(a => a.id) ?? [],
  }
}

function onPriorityChange(event: Event) {
  const val = (event.target as HTMLSelectElement).value
  form.value.priority = val ? Number(val) : null
}

// Note editing
const editingNoteId = ref<string | null>(null)
const editNoteContent = ref('')

const statusOptions = [
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'done', label: 'Done' },
  { value: 'canceled', label: 'Canceled' },
]

const priorityOptions = [
  { value: '', label: 'None' },
  { value: '1', label: 'Low' },
  { value: '2', label: 'Medium' },
  { value: '3', label: 'High' },
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
  editingNoteId.value = null
  loading.value = true
  try {
    const [t, emps] = await Promise.all([
      getTask(props.taskId),
      getEmployees(),
    ])
    task.value = t
    employees.value = emps
    populateForm(t)
  } catch (e) {
    toast.error(String(e))
    visible.value = false
  } finally {
    loading.value = false
  }
})

async function saveAll() {
  if (!task.value) return
  if (!form.value.title.trim()) {
    toast.error('Task title is required')
    return
  }
  saving.value = true
  try {
    task.value = await updateTask(task.value.id, {
      title: form.value.title.trim(),
      description: form.value.description?.trim() || null,
      status: form.value.status,
      priority: form.value.priority,
      start_date: form.value.start_date || null,
      due_date: form.value.due_date || null,
      assignee_ids: form.value.assignee_ids,
    })
    populateForm(task.value)
    emit('saved')
    visible.value = false
  } catch (e) {
    toast.error(String(e))
  } finally {
    saving.value = false
  }
}

function cancelChanges() {
  if (task.value) populateForm(task.value)
  visible.value = false
}

// Note editing
function startEditNote(note: { id: string; content: string }) {
  editingNoteId.value = note.id
  editNoteContent.value = note.content
}

async function saveEditNote(noteId: string) {
  if (!editNoteContent.value.trim() || !task.value) return
  try {
    await updateTaskNote(noteId, { content: editNoteContent.value })
    task.value = await getTask(task.value.id)
    editingNoteId.value = null
  } catch (e) {
    toast.error(String(e))
  }
}

function cancelEditNote() {
  editingNoteId.value = null
  editNoteContent.value = ''
}

function isAssigned(empId: string): boolean {
  return form.value.assignee_ids.includes(empId)
}

function toggleAssignee(empId: string) {
  if (isAssigned(empId)) {
    form.value.assignee_ids = form.value.assignee_ids.filter(id => id !== empId)
  } else {
    form.value.assignee_ids = [...form.value.assignee_ids, empId]
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
      assignee_ids: user.value ? [user.value.id] : undefined,
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
    populateForm(task.value)
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
    populateForm(task.value)
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

async function handleNotePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.files
  if (!items?.length) return
  const imageFile = Array.from(items).find(f => f.type.startsWith('image/'))
  if (!imageFile) return

  event.preventDefault()
  imageUploading.value = true
  try {
    const { url } = await uploadImage(imageFile)
    const textarea = event.target as HTMLTextAreaElement
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const before = newNote.value.slice(0, start)
    const after = newNote.value.slice(end)
    const markdown = `![image](${url})`
    newNote.value = before + markdown + after
  } catch (e) {
    toast.error('Image upload failed: ' + String(e))
  } finally {
    imageUploading.value = false
  }
}


</script>

<template>
  <Dialog
    v-model:visible="visible"
    :modal="true"
    :style="{ width: '640px' }"
  >
    <template #header>
      <div class="title-display">
        <input
          v-model="form.title"
          type="text"
          class="title-edit-input"
        />
      </div>
    </template>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="task" class="task-detail">
      <!-- Back to parent -->
      <button v-if="parentTaskId" class="btn btn-sm" @click="goBackToParent">
        <i class="pi pi-arrow-left" /> Back to parent task
      </button>

      <!-- Status & Priority -->
      <div class="field-group">
        <div class="field">
          <label>Status</label>
          <select v-model="form.status">
            <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <div class="field">
          <label>Priority</label>
          <select :value="form.priority ?? ''" @change="onPriorityChange($event)">
            <option v-for="opt in priorityOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
      </div>

      <!-- Dates -->
      <div class="field-group">
        <div class="field">
          <label>Start Date</label>
          <input
            type="date"
            v-model="form.start_date"
          />
        </div>
        <div class="field">
          <label>Due Date</label>
          <input
            type="date"
            v-model="form.due_date"
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
      <div class="field">
        <label>Description</label>
        <textarea
          v-model="form.description"
          rows="3"
          class="note-edit-textarea"
          placeholder="Add a description..."
        />
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
          <textarea v-model="newNote" rows="2" placeholder="Add a note..." class="note-input" @paste="handleNotePaste" />
          <small v-if="imageUploading" class="upload-indicator">Uploading image...</small>
          <button class="btn btn-sm btn-primary" :disabled="noteSaving" @click="submitNote">
            {{ noteSaving ? 'Adding...' : 'Add' }}
          </button>
        </div>
        <div v-if="sortedNotes.length" class="notes-list">
          <div v-for="note in sortedNotes" :key="note.id" class="note-card">
            <div class="note-header">
              <span class="note-author">{{ note.author_name || 'Unknown' }}</span>
              <span class="note-date">{{ formatDateTime(note.created_at) }}</span>
              <button v-if="editingNoteId !== note.id" class="btn-edit-inline" title="Edit note" @click="startEditNote(note)"><i class="pi pi-pencil" /></button>
              <button class="btn-remove" @click="removeNote(note.id)">&times;</button>
            </div>
            <div v-if="editingNoteId === note.id" class="note-edit">
              <textarea v-model="editNoteContent" rows="3" class="note-edit-textarea" @keyup.escape="cancelEditNote" />
              <div class="note-edit-actions">
                <button class="btn btn-sm btn-primary" @click="saveEditNote(note.id)">Save</button>
                <button class="btn btn-sm" @click="cancelEditNote">Cancel</button>
              </div>
            </div>
            <RichText v-else :content="note.content" class="note-body" />
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

    <template #footer>
      <div class="modal-footer">
        <button class="btn" @click="cancelChanges">Cancel</button>
        <button class="btn btn-primary" :disabled="saving" @click="saveAll">
          {{ saving ? 'Saving...' : 'Save' }}
        </button>
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.task-detail { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.field label, .section > label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 0.25rem; }
.field input, .field select { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.field-group { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }

.title-display { display: flex; align-items: center; gap: 0.5rem; flex: 1; min-width: 0; }
.title-edit-input { padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 1rem; font-weight: 600; background: var(--p-form-field-background); color: var(--p-text-color); width: 100%; }

.btn-edit-inline { background: none; border: none; color: var(--p-text-muted-color); cursor: pointer; font-size: 0.75rem; padding: 0.125rem 0.25rem; }
.btn-edit-inline:hover { color: var(--p-primary-color); }
.btn-edit-inline .pi { font-size: 0.6875rem; }

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

.note-edit { display: flex; flex-direction: column; gap: 0.5rem; }
.note-edit-textarea { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; resize: vertical; background: var(--p-form-field-background); color: var(--p-text-color); font-family: inherit; }
.note-edit-actions { display: flex; gap: 0.375rem; }

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
.upload-indicator { color: var(--p-primary-color); font-size: 0.75rem; font-style: italic; }

.modal-footer { display: flex; justify-content: flex-end; gap: 0.5rem; }
</style>
