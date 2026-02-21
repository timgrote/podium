<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { ProjectSummary, ProjectNote, Task } from '../../types'
import { getProjectNotes, addProjectNote, deleteProjectNote } from '../../api/projects'
import { getProjectTasks } from '../../api/tasks'
import { useToast } from '../../composables/useToast'

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

watch(activeTab, async (tab) => {
  if (tab === 'notes' && notes.value.length === 0) await loadNotes()
  if (tab === 'tasks' && tasks.value.length === 0) await loadTasks()
})

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
    await addProjectNote(props.project.id, { content: newNote.value })
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
        Tasks
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'notes' }"
        @click="activeTab = 'notes'"
      >
        Notes
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
      <div v-if="tasksLoading" class="empty">Loading tasks...</div>
      <div v-else-if="tasks.length === 0" class="empty">No tasks</div>
      <div v-else class="tasks-list">
        <div v-for="task in tasks" :key="task.id" class="task-item">
          <i class="pi" :class="taskStatusIcon[task.status] || 'pi-circle'" />
          <span class="task-title">{{ task.title }}</span>
          <span class="task-status-label">{{ task.status.replace('_', ' ') }}</span>
          <span v-if="task.due_date" class="task-due">{{ formatDate(task.due_date) }}</span>
        </div>
      </div>
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

.task-item .pi {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.task-title {
  flex: 1;
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
