<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { useAuth } from '../../composables/useAuth'
import { getProposal, createProposal, updateProposal, getProposalDefaults, generateDoc } from '../../api/proposals'
import { todayStr } from '../../utils/dates'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  projectId: string
  proposalId: string | null
}>()

const emit = defineEmits<{
  saved: []
  error: [msg: string]
}>()

const toast = useToast()
const { user } = useAuth()
const saving = ref(false)
const loading = ref(false)
const generateGoogleDoc = ref(true)
const regenerateDoc = ref(true)
const dataPath = ref<string | null>(null)

const hasExistingDoc = computed(
  () => !!dataPath.value && dataPath.value.includes('google.com')
)

function parseProposalDate(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  // Already ISO format
  if (/^\d{4}-\d{2}-\d{2}/.test(dateStr)) return dateStr.slice(0, 10)
  // Try parsing human-readable like "March 03, 2026"
  const parsed = new Date(dateStr)
  if (!isNaN(parsed.getTime())) return parsed.toISOString().slice(0, 10)
  return ''
}

function defaultEngineerKey(): string {
  const keys = Object.keys(engineers.value)
  const firstName = user.value?.first_name?.toLowerCase()
  if (firstName) {
    const match = keys.find(k => k === firstName)
    if (match) return match
  }
  return keys[0] || ''
}

const form = ref({
  engineer_key: '',
  engineer_name: '',
  contact_method: '',
  proposal_date: '',
  status: 'draft',
})

const tasks = ref<{ name: string; description: string; amount: number; billing_type: 'fixed' | 'time_expense' }[]>([])
const engineers = ref<Record<string, { name: string; title: string }>>({})
const expandedTask = ref<number | null>(null)
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

watch(visible, async (val) => {
  if (!val) return
  loading.value = true
  try {
    // Always load defaults for the engineer dropdown
    const defaults = await getProposalDefaults()
    engineers.value = defaults.engineers || {}

    if (props.proposalId) {
      // Edit mode
      generateGoogleDoc.value = false
      regenerateDoc.value = true
      const p = await getProposal(props.proposalId)
      dataPath.value = p.data_path || null
      form.value = {
        engineer_key: p.engineer_key || '',
        engineer_name: p.engineer_name || '',
        contact_method: p.contact_method || '',
        proposal_date: parseProposalDate(p.proposal_date),
        status: p.status || 'draft',
      }
      tasks.value = p.tasks.map((t) => ({
        name: t.name,
        description: t.description || '',
        amount: t.amount,
        billing_type: t.billing_type || 'fixed',
      }))
    } else {
      // Create mode — pre-populate from defaults
      generateGoogleDoc.value = true
      dataPath.value = null
      expandedTask.value = null
      form.value = {
        engineer_key: defaultEngineerKey(),
        engineer_name: '',
        contact_method: '',
        proposal_date: todayStr(),
        status: 'draft',
      }
      onEngineerChange()
      // Pre-populate with default tasks
      const defaultTasks = [...(defaults.tasks || [])];
      if (defaults.changes_task) {
        defaultTasks.push(defaults.changes_task)
      }
      tasks.value = defaultTasks.map((t) => ({
        name: t.name,
        description: t.description || '',
        amount: t.amount || 0,
        billing_type: 'fixed',
      }))
    }
  } catch (e) {
    emit('error', String(e))
    visible.value = false
  } finally {
    loading.value = false
  }
})

// Sync engineer_name when engineer_key changes
function onEngineerChange() {
  const eng = engineers.value[form.value.engineer_key]
  if (eng) {
    form.value.engineer_name = eng.name
  }
}

function addTask() {
  tasks.value.push({ name: '', description: '', amount: 0, billing_type: 'fixed' })
  // Expand the new task's description so it's ready to fill in
  expandedTask.value = tasks.value.length - 1
}

function removeTask(i: number) {
  tasks.value.splice(i, 1)
  if (expandedTask.value === i) expandedTask.value = null
  else if (expandedTask.value !== null && expandedTask.value > i) expandedTask.value--
}

function toggleDescription(i: number) {
  expandedTask.value = expandedTask.value === i ? null : i
}

function onDragStart(i: number) {
  dragIndex.value = i
  // Collapse any open description so index tracking stays simple during reorder
  expandedTask.value = null
}

function onDragOver(i: number) {
  dragOverIndex.value = i
}

function onDrop(target: number) {
  const from = dragIndex.value
  if (from === null || from === target) {
    dragIndex.value = null
    dragOverIndex.value = null
    return
  }
  const [moved] = tasks.value.splice(from, 1)
  if (!moved) return
  tasks.value.splice(target, 0, moved)
  dragIndex.value = null
  dragOverIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}

const totalFee = computed(() =>
  tasks.value.reduce((s, t) => s + (t.amount || 0), 0)
)

const saveLabel = computed(() => {
  if (!props.proposalId) {
    return generateGoogleDoc.value ? 'Save & Generate Doc' : 'Save'
  }
  return regenerateDoc.value && hasExistingDoc.value ? 'Save & Regenerate Doc' : 'Save'
})

async function save() {
  saving.value = true
  try {
    const validTasks = tasks.value.filter((t) => t.name.trim())
    if (validTasks.length === 0) {
      toast.error('Add at least one task')
      saving.value = false
      return
    }

    // Sync engineer name from dropdown if key is set
    const engineerName = form.value.engineer_name || engineers.value[form.value.engineer_key]?.name || ''

    if (props.proposalId) {
      await updateProposal(props.proposalId, {
        engineer_key: form.value.engineer_key || undefined,
        engineer_name: engineerName || undefined,
        contact_method: form.value.contact_method || undefined,
        proposal_date: form.value.proposal_date || undefined,
        status: form.value.status,
        tasks: validTasks,
      })
      toast.success('Proposal updated')

      if (regenerateDoc.value && hasExistingDoc.value) {
        // Open window immediately to avoid popup blocker (doc generation takes ~12s)
        const docWindow = window.open('about:blank', '_blank')
        try {
          toast.success('Regenerating Google Doc...')
          const result = await generateDoc(props.proposalId)
          toast.success('Google Doc regenerated')
          if (result.data_path && docWindow) {
            docWindow.location.href = result.data_path
          } else if (result.data_path) {
            window.open(result.data_path, '_blank')
          }
        } catch (e) {
          if (docWindow) docWindow.close()
          toast.error('Proposal saved but Google Doc regeneration failed: ' + String(e))
        }
      }
    } else {
      const created = await createProposal({
        project_id: props.projectId,
        engineer_key: form.value.engineer_key || undefined,
        engineer_name: engineerName || undefined,
        contact_method: form.value.contact_method || undefined,
        proposal_date: form.value.proposal_date || undefined,
        status: form.value.status,
        tasks: validTasks,
      })
      toast.success('Proposal created')

      if (generateGoogleDoc.value && created.id) {
        // Open window immediately to avoid popup blocker (doc generation takes ~12s)
        const docWindow = window.open('about:blank', '_blank')
        try {
          toast.success('Generating Google Doc...')
          const result = await generateDoc(created.id)
          toast.success('Google Doc generated')
          if (result.data_path && docWindow) {
            docWindow.location.href = result.data_path
          } else if (result.data_path) {
            window.open(result.data_path, '_blank')
          }
        } catch (e) {
          if (docWindow) docWindow.close()
          toast.error('Proposal saved but Google Doc generation failed: ' + String(e))
        }
      }
    }
    emit('saved')
    visible.value = false
  } catch (e) {
    emit('error', String(e))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :header="proposalId ? 'Edit Proposal' : 'New Proposal'"
    :modal="true"
    :style="{ width: '640px' }"
    :pt="{ root: { style: 'resize: both; overflow: auto; min-width: 400px; max-width: 95vw; max-height: 95vh;' } }"
  >
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="form">
      <a
        v-if="dataPath && dataPath.includes('google.com')"
        class="doc-banner"
        :href="dataPath"
        target="_blank"
      >
        <i class="pi pi-file-edit" /> Open Google Doc
      </a>
      <div class="field-group">
        <div class="field">
          <label>Engineer</label>
          <select v-model="form.engineer_key" @change="onEngineerChange">
            <option v-for="(eng, key) in engineers" :key="key" :value="key">
              {{ eng.name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>Contact Method</label>
          <input v-model="form.contact_method" type="text" placeholder="e.g., site meeting" />
        </div>
      </div>
      <div class="field-group">
        <div class="field">
          <label>Proposal Date</label>
          <input v-model="form.proposal_date" type="date" />
        </div>
        <div class="field">
          <label>Status</label>
          <select v-model="form.status">
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      <div class="tasks-section">
        <div class="tasks-header">
          <h4>Tasks</h4>
          <button class="btn btn-sm" @click="addTask">+ Add Task</button>
        </div>
        <div
          v-for="(task, i) in tasks"
          :key="i"
          class="task-entry"
          :class="{ 'drag-over': dragOverIndex === i && dragIndex !== i, dragging: dragIndex === i }"
          @dragover.prevent="onDragOver(i)"
          @drop="onDrop(i)"
        >
          <div class="task-row">
            <span
              class="drag-handle"
              title="Drag to reorder"
              draggable="true"
              @dragstart="onDragStart(i)"
              @dragend="onDragEnd"
            >
              <i class="pi pi-bars" />
            </span>
            <button
              class="btn-expand"
              :title="expandedTask === i ? 'Hide description' : 'Show description'"
              @click="toggleDescription(i)"
            >
              <i class="pi" :class="expandedTask === i ? 'pi-chevron-down' : 'pi-chevron-right'" />
            </button>
            <input v-model="task.name" placeholder="Task name" class="task-name" />
            <input v-model.number="task.amount" type="number" step="0.01" placeholder="Amount" class="task-amount" />
            <select v-model="task.billing_type" class="task-type" title="Billing type">
              <option value="fixed">Fixed</option>
              <option value="time_expense">T&amp;E</option>
            </select>
            <button class="btn-remove" @click="removeTask(i)">&times;</button>
          </div>
          <div v-if="expandedTask === i" class="task-description">
            <textarea v-model="task.description" rows="3" placeholder="Task description (optional)" />
          </div>
        </div>
        <div class="task-total">
          Total: ${{ totalFee.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
      </div>

      <label v-if="!proposalId" class="checkbox-row">
        <input v-model="generateGoogleDoc" type="checkbox" />
        Generate Google Doc
      </label>
      <label v-if="proposalId && hasExistingDoc" class="checkbox-row">
        <input v-model="regenerateDoc" type="checkbox" />
        Regenerate Google Doc (creates a new one)
      </label>
    </div>
    <template #footer>
      <button class="btn" @click="visible = false">Cancel</button>
      <button class="btn btn-primary" :disabled="saving" @click="save">
        {{ saving ? 'Saving...' : saveLabel }}
      </button>
    </template>
  </Dialog>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.field label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; }
.field input, .field textarea, .field select { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.field-group { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.tasks-section { margin-top: 0.5rem; }
.tasks-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.tasks-header h4 { margin: 0; font-size: 0.875rem; }
.task-entry { margin-bottom: 0.375rem; border-radius: 0.25rem; border-top: 2px solid transparent; }
.task-entry.dragging { opacity: 0.5; }
.task-entry.drag-over { border-top-color: var(--p-primary-color); }
.task-row { display: flex; gap: 0.5rem; align-items: center; }
.drag-handle { display: flex; align-items: center; color: var(--p-text-muted-color); cursor: grab; padding: 0.25rem; font-size: 0.75rem; }
.drag-handle:active { cursor: grabbing; }
.task-name { flex: 1; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.task-amount { width: 100px; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; text-align: right; background: var(--p-form-field-background); color: var(--p-text-color); }
.task-type { width: 72px; padding: 0.375rem 0.25rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.75rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.task-description { padding-left: 3.25rem; margin-top: 0.25rem; }
.task-description textarea { width: 100%; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; background: var(--p-form-field-background); color: var(--p-text-color); resize: vertical; font-family: inherit; }
.btn-expand { background: none; border: none; color: var(--p-text-muted-color); cursor: pointer; padding: 0.25rem; font-size: 0.75rem; }
.btn-remove { background: none; border: none; color: var(--p-red-600); cursor: pointer; font-size: 1.25rem; padding: 0 0.25rem; }
.task-total { text-align: right; font-weight: 600; font-size: 0.875rem; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--p-content-border-color); }
.checkbox-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: var(--p-text-color); cursor: pointer; margin-top: 0.25rem; }
.checkbox-row input[type="checkbox"] { accent-color: var(--p-primary-color); }
.doc-banner {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  background: var(--p-blue-50);
  border: 1px solid var(--p-blue-200);
  border-radius: 0.375rem;
  color: var(--p-blue-700);
  text-decoration: none;
  font-size: 0.8125rem;
  font-weight: 500;
}
.doc-banner:hover {
  background: var(--p-blue-100);
}
:root.p-dark .doc-banner {
  background: color-mix(in srgb, var(--p-blue-500) 15%, transparent);
  border-color: color-mix(in srgb, var(--p-blue-400) 30%, transparent);
  color: var(--p-blue-300);
}
:root.p-dark .doc-banner:hover {
  background: color-mix(in srgb, var(--p-blue-500) 25%, transparent);
}
.loading { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
