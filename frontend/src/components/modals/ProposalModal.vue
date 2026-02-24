<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { getProposal, createProposal, updateProposal, getProposalDefaults, generateDoc } from '../../api/proposals'

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
const saving = ref(false)
const loading = ref(false)
const generateGoogleDoc = ref(true)
const dataPath = ref<string | null>(null)

const form = ref({
  engineer_key: '',
  engineer_name: '',
  contact_method: '',
  proposal_date: '',
  status: 'draft',
})

const tasks = ref<{ name: string; description: string; amount: number }[]>([])
const engineers = ref<Record<string, { name: string; title: string }>>({})
const expandedTask = ref<number | null>(null)

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
      const p = await getProposal(props.proposalId)
      dataPath.value = p.data_path || null
      form.value = {
        engineer_key: p.engineer_key || '',
        engineer_name: p.engineer_name || '',
        contact_method: p.contact_method || '',
        proposal_date: p.proposal_date || '',
        status: p.status || 'draft',
      }
      tasks.value = p.tasks.map((t) => ({
        name: t.name,
        description: t.description || '',
        amount: t.amount,
      }))
    } else {
      // Create mode — pre-populate from defaults
      generateGoogleDoc.value = true
      dataPath.value = null
      expandedTask.value = null
      form.value = {
        engineer_key: Object.keys(engineers.value)[0] || '',
        engineer_name: '',
        contact_method: '',
        proposal_date: '',
        status: 'draft',
      }
      // Pre-populate with default tasks
      const defaultTasks = [...(defaults.tasks || [])];
      if (defaults.changes_task) {
        defaultTasks.push(defaults.changes_task)
      }
      tasks.value = defaultTasks.map((t) => ({
        name: t.name,
        description: t.description || '',
        amount: t.amount || 0,
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
  tasks.value.push({ name: '', description: '', amount: 0 })
}

function removeTask(i: number) {
  tasks.value.splice(i, 1)
  if (expandedTask.value === i) expandedTask.value = null
  else if (expandedTask.value !== null && expandedTask.value > i) expandedTask.value--
}

function toggleDescription(i: number) {
  expandedTask.value = expandedTask.value === i ? null : i
}

const totalFee = computed(() =>
  tasks.value.reduce((s, t) => s + (t.amount || 0), 0)
)

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
        try {
          toast.success('Generating Google Doc...')
          await generateDoc(created.id)
          toast.success('Google Doc generated')
        } catch (e) {
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
          <input v-model="form.proposal_date" type="text" placeholder="February 20, 2026" />
        </div>
        <div class="field">
          <label>Status</label>
          <select v-model="form.status">
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      <div class="tasks-section">
        <div class="tasks-header">
          <h4>Tasks</h4>
          <button class="btn btn-sm" @click="addTask">+ Add Task</button>
        </div>
        <div v-for="(task, i) in tasks" :key="i" class="task-entry">
          <div class="task-row">
            <button
              class="btn-expand"
              :title="expandedTask === i ? 'Hide description' : 'Show description'"
              @click="toggleDescription(i)"
            >
              <i class="pi" :class="expandedTask === i ? 'pi-chevron-down' : 'pi-chevron-right'" />
            </button>
            <input v-model="task.name" placeholder="Task name" class="task-name" />
            <input v-model.number="task.amount" type="number" step="0.01" placeholder="Amount" class="task-amount" />
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
    </div>
    <template #footer>
      <button class="btn" @click="visible = false">Cancel</button>
      <button class="btn btn-primary" :disabled="saving" @click="save">
        {{ saving ? 'Saving...' : (generateGoogleDoc && !proposalId ? 'Save & Generate Doc' : 'Save') }}
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
.task-entry { margin-bottom: 0.375rem; }
.task-row { display: flex; gap: 0.5rem; align-items: center; }
.task-name { flex: 1; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.task-amount { width: 100px; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; text-align: right; background: var(--p-form-field-background); color: var(--p-text-color); }
.task-description { padding-left: 1.75rem; margin-top: 0.25rem; }
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
