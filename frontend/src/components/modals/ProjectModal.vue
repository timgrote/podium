<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import type { ProjectSummary } from '../../types'
import { useClients } from '../../composables/useClients'
import { useToast } from '../../composables/useToast'
import { createProject, updateProject } from '../../api/projects'
import { getEmployees } from '../../api/employees'
import type { Employee } from '../../types'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  project: ProjectSummary | null
}>()

const emit = defineEmits<{
  saved: []
  error: [msg: string]
  delete: []
}>()

const { clients } = useClients()
const toast = useToast()
const employees = ref<Employee[]>([])

const form = ref({
  project_name: '',
  project_number: '',
  job_code: '',
  client_id: '',
  client_name: '',
  client_email: '',
  location: '',
  status: 'proposal',
  pm_id: '',
  client_project_number: '',
  data_path: '',
  notes: '',
})

const saving = ref(false)

watch(visible, async (val) => {
  if (!val) return
  employees.value = await getEmployees()
  if (props.project) {
    form.value = {
      project_name: props.project.project_name || '',
      project_number: props.project.project_number || '',
      job_code: props.project.job_code || '',
      client_id: props.project.client_id || '',
      client_name: props.project.client_name || '',
      client_email: props.project.client_email || '',
      location: props.project.location || '',
      status: props.project.status,
      pm_id: props.project.pm_id || '',
      client_project_number: props.project.client_project_number || '',
      data_path: props.project.data_path || '',
      notes: '',
    }
  } else {
    form.value = {
      project_name: '',
      project_number: '',
      job_code: '',
      client_id: '',
      client_name: '',
      client_email: '',
      location: '',
      status: 'proposal',
      pm_id: '',
      client_project_number: '',
      data_path: '',
      notes: '',
    }
  }
})

async function save() {
  if (!form.value.project_name.trim()) return
  saving.value = true
  try {
    if (props.project) {
      await updateProject(props.project.id, {
        name: form.value.project_name,
        project_number: form.value.project_number || undefined,
        job_code: form.value.job_code || undefined,
        client_id: form.value.client_id || undefined,
        location: form.value.location || undefined,
        status: form.value.status,
        pm_id: form.value.pm_id || null,
        client_project_number: form.value.client_project_number || undefined,
        data_path: form.value.data_path || undefined,
      })
      toast.success('Project updated')
    } else {
      await createProject({
        project_name: form.value.project_name,
        job_code: form.value.job_code || undefined,
        client_id: form.value.client_id || undefined,
        client_name: form.value.client_name || undefined,
        client_email: form.value.client_email || undefined,
        location: form.value.location || undefined,
        status: form.value.status,
        pm_id: form.value.pm_id || undefined,
        data_path: form.value.data_path || undefined,
      })
      toast.success('Project created')
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
    :header="project ? 'Edit Project' : 'New Project'"
    :modal="true"
    :style="{ width: '560px' }"
  >
    <div class="form">
      <!-- Project Basics -->
      <div class="field-row" style="grid-template-columns: 2fr 1fr">
        <div class="field">
          <label>Project Name *</label>
          <input v-model="form.project_name" type="text" />
        </div>
        <div class="field">
          <label>Project #</label>
          <input v-model="form.project_number" type="text" :disabled="!project" :placeholder="project ? '' : 'Auto'" />
        </div>
      </div>
      <div class="field-row">
        <div class="field">
          <label>Job Code</label>
          <input v-model="form.job_code" type="text" placeholder="e.g., rvi-absal" />
        </div>
        <div class="field">
          <label>Location</label>
          <input v-model="form.location" type="text" placeholder="Austin, TX" />
        </div>
      </div>

      <!-- Client Fieldset -->
      <fieldset class="client-fieldset">
        <legend>Client</legend>
        <div class="field">
          <label>Client</label>
          <select v-model="form.client_id">
            <option value="">-- Select or create new --</option>
            <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div v-if="!form.client_id && !project" class="field-row">
          <div class="field">
            <label>New Client Name</label>
            <input v-model="form.client_name" type="text" />
          </div>
          <div class="field">
            <label>New Client Email</label>
            <input v-model="form.client_email" type="email" />
          </div>
        </div>
        <div class="field">
          <label>Client Project #</label>
          <input v-model="form.client_project_number" type="text" />
        </div>
      </fieldset>

      <!-- Assignment + Status -->
      <div class="field-row">
        <div class="field">
          <label>Project Manager</label>
          <select v-model="form.pm_id">
            <option value="">-- None --</option>
            <option v-for="e in employees" :key="e.id" :value="e.id">{{ e.first_name }} {{ e.last_name }}</option>
          </select>
        </div>
        <div class="field">
          <label>Status</label>
          <select v-model="form.status">
            <option value="proposal">Proposal</option>
            <option value="contract">Contract</option>
            <option value="in_process">In Process</option>
            <option value="invoiced">Invoiced</option>
            <option value="paid">Paid</option>
            <option value="complete">Complete</option>
          </select>
        </div>
      </div>

      <!-- Folder Path -->
      <div class="field">
        <label>Folder Path</label>
        <input v-model="form.data_path" type="text" placeholder="/path/to/project/folder" />
      </div>
    </div>
    <template #footer>
      <div class="footer-row">
        <button v-if="project" class="btn btn-danger" @click="emit('delete'); visible = false">
          <i class="pi pi-trash" /> Delete
        </button>
        <div class="footer-right">
          <button class="btn" @click="visible = false">Cancel</button>
          <button class="btn btn-primary" :disabled="saving" @click="save">
            {{ saving ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.field label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; }
.field input, .field select, .field textarea { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.field input:disabled { opacity: 0.5; cursor: not-allowed; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.client-fieldset { border: 1px solid var(--p-content-border-color); border-radius: 0.5rem; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.75rem; margin: 0; }
.client-fieldset legend { font-size: 0.8rem; font-weight: 600; color: var(--p-text-muted-color); padding: 0 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger { color: var(--p-red-600); border-color: var(--p-red-300); }
.btn-danger:hover { background: var(--p-red-50); }
.footer-row { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.footer-right { display: flex; gap: 0.5rem; }
</style>
