<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import type { ProjectSummary, Contact, Employee } from '../../types'
import { useClients } from '../../composables/useClients'
import { useToast } from '../../composables/useToast'
import { createProject, updateProject } from '../../api/projects'
import { getEmployees } from '../../api/employees'
import { getContacts, createContact } from '../../api/contacts'

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
const contacts = ref<Contact[]>([])
const showNewContact = ref(false)
const newContactName = ref('')
const newContactEmail = ref('')
const creatingContact = ref(false)

const form = ref({
  project_name: '',
  project_number: '',
  job_code: '',
  client_id: '',
  client_name: '',
  client_email: '',
  client_pm_id: '',
  location: '',
  status: 'proposal',
  pm_id: '',
  client_project_number: '',
  data_path: '',
  notes: '',
})

const saving = ref(false)

function normalizeDataPath(raw: string): string {
  let p = raw.trim()
  if (p.startsWith('"') && p.endsWith('"')) p = p.slice(1, -1)
  p = p.replace(/\\/g, '/')
  p = p.replace(/^[A-Z]:\/Dropbox\/TIE\//i, '')
  p = p.replace(/^\/+|\/+$/g, '')
  return p
}

async function loadContacts(clientId: string) {
  if (!clientId) {
    contacts.value = []
    return
  }
  contacts.value = await getContacts(clientId)
}

// Watch client_id changes to load contacts and auto-select first
watch(() => form.value.client_id, async (newClientId, oldClientId) => {
  if (newClientId !== oldClientId) {
    showNewContact.value = false
    newContactName.value = ''
    newContactEmail.value = ''
    await loadContacts(newClientId || '')
    if (contacts.value.length > 0 && contacts.value[0]) {
      form.value.client_pm_id = contacts.value[0].id
    } else {
      form.value.client_pm_id = ''
    }
  }
})

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
      client_pm_id: props.project.client_pm_id || '',
      location: props.project.location || '',
      status: props.project.status,
      pm_id: props.project.pm_id || '',
      client_project_number: props.project.client_project_number || '',
      data_path: props.project.data_path || '',
      notes: '',
    }
    // Load contacts for the existing client without overwriting client_pm_id
    if (props.project.client_id) {
      await loadContacts(props.project.client_id)
    }
  } else {
    form.value = {
      project_name: '',
      project_number: '',
      job_code: '',
      client_id: '',
      client_name: '',
      client_email: '',
      client_pm_id: '',
      location: '',
      status: 'proposal',
      pm_id: '',
      client_project_number: '',
      data_path: '',
      notes: '',
    }
    contacts.value = []
  }
  showNewContact.value = false
  newContactName.value = ''
  newContactEmail.value = ''
})

async function addContact() {
  if (!newContactName.value.trim()) return
  creatingContact.value = true
  try {
    const contact = await createContact({
      name: newContactName.value.trim(),
      email: newContactEmail.value.trim() || undefined,
      client_id: form.value.client_id,
    })
    contacts.value.push(contact)
    form.value.client_pm_id = contact.id
    showNewContact.value = false
    newContactName.value = ''
    newContactEmail.value = ''
  } catch (e) {
    toast.error('Failed to create contact')
  } finally {
    creatingContact.value = false
  }
}

async function save() {
  if (!form.value.project_name.trim()) {
    toast.error('Project name is required')
    return
  }
  saving.value = true
  try {
    if (props.project) {
      await updateProject(props.project.id, {
        name: form.value.project_name,
        project_number: form.value.project_number || undefined,
        job_code: form.value.job_code || undefined,
        client_id: form.value.client_id || undefined,
        client_pm_id: form.value.client_pm_id || null,
        location: form.value.location || undefined,
        status: form.value.status,
        pm_id: form.value.pm_id || null,
        client_project_number: form.value.client_project_number || undefined,
        data_path: normalizeDataPath(form.value.data_path) || undefined,
      })
      toast.success('Project updated')
    } else {
      await createProject({
        project_name: form.value.project_name,
        job_code: form.value.job_code || undefined,
        client_id: form.value.client_id || undefined,
        client_pm_id: form.value.client_pm_id || undefined,
        client_name: form.value.client_name || undefined,
        client_email: form.value.client_email || undefined,
        location: form.value.location || undefined,
        status: form.value.status,
        pm_id: form.value.pm_id || undefined,
        data_path: normalizeDataPath(form.value.data_path) || undefined,
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
            <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.company || c.name }}</option>
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

        <!-- Contact Section (visible when client is selected) -->
        <div v-if="form.client_id" class="contact-section">
          <div class="contact-header">
            <label>Contact</label>
            <button type="button" class="btn-icon" title="Add new contact" @click="showNewContact = !showNewContact">
              <i :class="showNewContact ? 'pi pi-times' : 'pi pi-plus'" />
            </button>
          </div>
          <select v-model="form.client_pm_id">
            <option value="">-- None --</option>
            <option v-for="ct in contacts" :key="ct.id" :value="ct.id">
              {{ ct.name }}{{ ct.email ? ` (${ct.email})` : '' }}
            </option>
          </select>
          <div v-if="showNewContact" class="new-contact-form">
            <div class="field-row">
              <div class="field">
                <input v-model="newContactName" type="text" placeholder="Name" />
              </div>
              <div class="field">
                <input v-model="newContactEmail" type="email" placeholder="Email" />
              </div>
              <button
                type="button"
                class="btn btn-sm"
                :disabled="!newContactName.trim() || creatingContact"
                @click="addContact"
              >
                Add
              </button>
            </div>
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
        <input v-model="form.data_path" type="text" placeholder="e.g. RVi Planning/Thompson Ridge" />
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
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; align-items: end; }
.client-fieldset { border: 1px solid var(--p-content-border-color); border-radius: 0.5rem; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.75rem; margin: 0; }
.client-fieldset legend { font-size: 0.8rem; font-weight: 600; color: var(--p-text-muted-color); padding: 0 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; }
.contact-section { display: flex; flex-direction: column; gap: 0.5rem; }
.contact-section select { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.contact-header { display: flex; align-items: center; justify-content: space-between; }
.contact-header label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; }
.btn-icon { background: none; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; cursor: pointer; padding: 0.25rem 0.5rem; color: var(--p-text-muted-color); font-size: 0.75rem; }
.btn-icon:hover { background: var(--p-content-hover-background); }
.new-contact-form .field-row { grid-template-columns: 1fr 1fr auto; }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-sm { padding: 0.5rem 0.75rem; font-size: 0.8rem; margin-left: 0; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger { color: var(--p-red-600); border-color: var(--p-red-300); }
.btn-danger:hover { background: var(--p-red-50); }
.footer-row { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.footer-right { display: flex; gap: 0.5rem; }
</style>
