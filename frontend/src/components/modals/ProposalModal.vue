<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { getProposal, createProposal, updateProposal } from '../../api/proposals'

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

const form = ref({
  client_company: '',
  client_contact_email: '',
  engineer_key: '',
  engineer_name: '',
  contact_method: '',
  proposal_date: '',
})

const tasks = ref<{ name: string; description: string; amount: number }[]>([])

watch(visible, async (val) => {
  if (!val) return
  if (props.proposalId) {
    loading.value = true
    try {
      const p = await getProposal(props.proposalId)
      form.value = {
        client_company: p.client_company || '',
        client_contact_email: p.client_contact_email || '',
        engineer_key: p.engineer_key || '',
        engineer_name: p.engineer_name || '',
        contact_method: p.contact_method || '',
        proposal_date: p.proposal_date || '',
      }
      tasks.value = p.tasks.map((t) => ({
        name: t.name,
        description: t.description || '',
        amount: t.amount,
      }))
    } finally {
      loading.value = false
    }
  } else {
    form.value = { client_company: '', client_contact_email: '', engineer_key: '', engineer_name: '', contact_method: '', proposal_date: '' }
    tasks.value = [{ name: '', description: '', amount: 0 }]
  }
})

function addTask() {
  tasks.value.push({ name: '', description: '', amount: 0 })
}

function removeTask(i: number) {
  tasks.value.splice(i, 1)
}

async function save() {
  saving.value = true
  try {
    const validTasks = tasks.value.filter((t) => t.name.trim())
    if (props.proposalId) {
      await updateProposal(props.proposalId, {
        client_company: form.value.client_company || undefined,
        client_contact_email: form.value.client_contact_email || undefined,
        engineer_key: form.value.engineer_key || undefined,
        engineer_name: form.value.engineer_name || undefined,
        contact_method: form.value.contact_method || undefined,
        proposal_date: form.value.proposal_date || undefined,
      })
      toast.success('Proposal updated')
    } else {
      await createProposal({
        project_id: props.projectId,
        client_company: form.value.client_company || undefined,
        client_contact_email: form.value.client_contact_email || undefined,
        engineer_key: form.value.engineer_key || undefined,
        engineer_name: form.value.engineer_name || undefined,
        contact_method: form.value.contact_method || undefined,
        proposal_date: form.value.proposal_date || undefined,
        tasks: validTasks,
      })
      toast.success('Proposal created')
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
    :style="{ width: '600px' }"
  >
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="form">
      <div class="field-group">
        <div class="field">
          <label>Client Company</label>
          <input v-model="form.client_company" type="text" />
        </div>
        <div class="field">
          <label>Client Email</label>
          <input v-model="form.client_contact_email" type="email" />
        </div>
      </div>
      <div class="field-group">
        <div class="field">
          <label>Engineer</label>
          <input v-model="form.engineer_name" type="text" />
        </div>
        <div class="field">
          <label>Contact Method</label>
          <input v-model="form.contact_method" type="text" placeholder="site meeting" />
        </div>
      </div>
      <div class="field">
        <label>Proposal Date</label>
        <input v-model="form.proposal_date" type="text" placeholder="February 20, 2026" />
      </div>

      <div class="tasks-section">
        <div class="tasks-header">
          <h4>Tasks</h4>
          <button class="btn btn-sm" @click="addTask">+ Add Task</button>
        </div>
        <div v-for="(task, i) in tasks" :key="i" class="task-row">
          <input v-model="task.name" placeholder="Task name" class="task-name" />
          <input v-model.number="task.amount" type="number" step="0.01" placeholder="Amount" class="task-amount" />
          <button class="btn-remove" @click="removeTask(i)">&times;</button>
        </div>
        <div class="task-total">
          Total: ${{ tasks.reduce((s, t) => s + (t.amount || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
      </div>
    </div>
    <template #footer>
      <button class="btn" @click="visible = false">Cancel</button>
      <button class="btn btn-primary" :disabled="saving" @click="save">
        {{ saving ? 'Saving...' : 'Save' }}
      </button>
    </template>
  </Dialog>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.field label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; }
.field input, .field textarea { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.field-group { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.tasks-section { margin-top: 0.5rem; }
.tasks-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.tasks-header h4 { margin: 0; font-size: 0.875rem; }
.task-row { display: flex; gap: 0.5rem; margin-bottom: 0.375rem; align-items: center; }
.task-name { flex: 1; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.task-amount { width: 100px; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; text-align: right; background: var(--p-form-field-background); color: var(--p-text-color); }
.btn-remove { background: none; border: none; color: var(--p-red-600); cursor: pointer; font-size: 1.25rem; padding: 0 0.25rem; }
.task-total { text-align: right; font-weight: 600; font-size: 0.875rem; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--p-content-border-color); }
.loading { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
