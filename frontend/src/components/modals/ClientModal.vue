<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import type { Contact } from '../../types'
import { getClient, createClient, updateClient } from '../../api/clients'
import { getContacts, createContact, updateContact, deleteContact } from '../../api/contacts'
import { useToast } from '../../composables/useToast'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  clientId: string | null
}>()

const emit = defineEmits<{
  saved: []
  error: [msg: string]
}>()

const toast = useToast()
const loading = ref(false)
const saving = ref(false)
const contacts = ref<Contact[]>([])
const editingContactId = ref<string | null>(null)

const form = ref({
  name: '',
  company: '',
  accounting_email: '',
  phone: '',
  address: '',
  notes: '',
})

const contactForm = ref({
  name: '',
  email: '',
  phone: '',
  role: '',
})

const showAddContact = ref(false)
const addingContact = ref(false)
const newContact = ref({ name: '', email: '', phone: '', role: '' })

watch(visible, async (val) => {
  if (!val) return
  editingContactId.value = null
  showAddContact.value = false
  if (!props.clientId) {
    form.value = { name: '', company: '', accounting_email: '', phone: '', address: '', notes: '' }
    contacts.value = []
    return
  }
  loading.value = true
  try {
    const [client, clientContacts] = await Promise.all([
      getClient(props.clientId),
      getContacts(props.clientId),
    ])
    form.value = {
      name: client.name || '',
      company: client.company || '',
      accounting_email: client.accounting_email || '',
      phone: client.phone || '',
      address: client.address || '',
      notes: client.notes || '',
    }
    contacts.value = clientContacts
  } catch (e) {
    emit('error', String(e))
    visible.value = false
  } finally {
    loading.value = false
  }
})

async function saveClient() {
  if (!form.value.name.trim()) {
    toast.error('Client name is required')
    return
  }
  saving.value = true
  try {
    if (props.clientId) {
      await updateClient(props.clientId, {
        name: form.value.name || undefined,
        company: form.value.company || undefined,
        accounting_email: form.value.accounting_email || undefined,
        phone: form.value.phone || undefined,
        address: form.value.address || undefined,
        notes: form.value.notes || undefined,
      })
      toast.success('Client updated')
    } else {
      await createClient({
        name: form.value.name,
        email: form.value.accounting_email || undefined,
        company: form.value.company || undefined,
        phone: form.value.phone || undefined,
        address: form.value.address || undefined,
        notes: form.value.notes || undefined,
      })
      toast.success('Client created')
    }
    emit('saved')
    visible.value = false
  } catch (e) {
    emit('error', String(e))
  } finally {
    saving.value = false
  }
}

function startEditContact(ct: Contact) {
  editingContactId.value = ct.id
  contactForm.value = {
    name: ct.name || '',
    email: ct.email || '',
    phone: ct.phone || '',
    role: ct.role || '',
  }
}

function cancelEditContact() {
  editingContactId.value = null
}

async function saveContact(ct: Contact) {
  try {
    const updated = await updateContact(ct.id, {
      name: contactForm.value.name || undefined,
      email: contactForm.value.email || undefined,
      phone: contactForm.value.phone || undefined,
      role: contactForm.value.role || undefined,
    })
    const idx = contacts.value.findIndex(c => c.id === ct.id)
    if (idx >= 0) contacts.value[idx] = updated
    editingContactId.value = null
    toast.success('Contact updated')
  } catch (e) {
    toast.error('Failed to update contact')
  }
}

async function removeContact(ct: Contact) {
  try {
    await deleteContact(ct.id)
    contacts.value = contacts.value.filter(c => c.id !== ct.id)
    toast.success('Contact removed')
  } catch (e) {
    toast.error('Failed to remove contact')
  }
}

async function addContact() {
  if (!newContact.value.name.trim() || !props.clientId) return
  addingContact.value = true
  try {
    const created = await createContact({
      name: newContact.value.name.trim(),
      email: newContact.value.email.trim() || undefined,
      phone: newContact.value.phone.trim() || undefined,
      role: newContact.value.role.trim() || undefined,
      client_id: props.clientId,
    })
    contacts.value.push(created)
    newContact.value = { name: '', email: '', phone: '', role: '' }
    showAddContact.value = false
    toast.success('Contact added')
  } catch (e) {
    toast.error('Failed to add contact')
  } finally {
    addingContact.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :header="clientId ? 'Edit Client' : 'New Client'"
    :modal="true"
    :style="{ width: '600px' }"
  >
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="modal-body">
      <!-- Client Details -->
      <div class="form">
        <div class="field-row">
          <div class="field">
            <label>Name</label>
            <input v-model="form.name" type="text" />
          </div>
          <div class="field">
            <label>Company</label>
            <input v-model="form.company" type="text" />
          </div>
        </div>
        <div class="field-row">
          <div class="field">
            <label>Accounting Email</label>
            <input v-model="form.accounting_email" type="email" />
          </div>
          <div class="field">
            <label>Phone</label>
            <input v-model="form.phone" type="text" />
          </div>
        </div>
        <div class="field">
          <label>Address</label>
          <textarea v-model="form.address" rows="2" />
        </div>
        <div class="field">
          <label>Notes</label>
          <textarea v-model="form.notes" rows="3" placeholder="Internal notes about this client" />
        </div>
      </div>

      <!-- Contacts Section (edit mode only) -->
      <fieldset v-if="clientId" class="contacts-fieldset">
        <legend>
          Contacts
          <button type="button" class="btn-icon" title="Add contact" @click="showAddContact = !showAddContact">
            <i :class="showAddContact ? 'pi pi-times' : 'pi pi-plus'" />
          </button>
        </legend>

        <!-- Add Contact Form -->
        <div v-if="showAddContact" class="add-contact-form">
          <div class="field-row field-row-4">
            <input v-model="newContact.name" type="text" placeholder="Name *" />
            <input v-model="newContact.email" type="email" placeholder="Email" />
            <input v-model="newContact.phone" type="text" placeholder="Phone" />
            <input v-model="newContact.role" type="text" placeholder="Role" />
          </div>
          <button
            class="btn btn-sm btn-primary"
            :disabled="!newContact.name.trim() || addingContact"
            @click="addContact"
          >
            Add
          </button>
        </div>

        <div v-if="contacts.length === 0 && !showAddContact" class="empty-contacts">
          No contacts yet
        </div>

        <div v-for="ct in contacts" :key="ct.id" class="contact-item">
          <template v-if="editingContactId === ct.id">
            <div class="contact-edit">
              <div class="field-row field-row-4">
                <input v-model="contactForm.name" type="text" placeholder="Name" />
                <input v-model="contactForm.email" type="email" placeholder="Email" />
                <input v-model="contactForm.phone" type="text" placeholder="Phone" />
                <input v-model="contactForm.role" type="text" placeholder="Role" />
              </div>
              <div class="contact-edit-actions">
                <button class="btn btn-sm btn-primary" @click="saveContact(ct)">Save</button>
                <button class="btn btn-sm" @click="cancelEditContact">Cancel</button>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="contact-info">
              <span class="contact-name">{{ ct.name }}</span>
              <span v-if="ct.role" class="contact-role">{{ ct.role }}</span>
              <span v-if="ct.email" class="contact-detail">{{ ct.email }}</span>
              <span v-if="ct.phone" class="contact-detail">{{ ct.phone }}</span>
            </div>
            <div class="contact-actions">
              <button class="btn-icon" title="Edit" @click="startEditContact(ct)">
                <i class="pi pi-pencil" />
              </button>
              <button class="btn-icon btn-icon-danger" title="Remove" @click="removeContact(ct)">
                <i class="pi pi-trash" />
              </button>
            </div>
          </template>
        </div>
      </fieldset>
    </div>

    <template #footer>
      <button class="btn" @click="visible = false">Cancel</button>
      <button class="btn btn-primary" :disabled="saving" @click="saveClient">
        {{ saving ? 'Saving...' : 'Save' }}
      </button>
    </template>
  </Dialog>
</template>

<style scoped>
.loading { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.modal-body { display: flex; flex-direction: column; gap: 1rem; }
.form { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.field label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; }
.field input, .field textarea { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.field-row-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 0.5rem; }
.field-row-4 input { padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.8125rem; background: var(--p-form-field-background); color: var(--p-text-color); }

.contacts-fieldset { border: 1px solid var(--p-content-border-color); border-radius: 0.5rem; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem; margin: 0; }
.contacts-fieldset legend { font-size: 0.8rem; font-weight: 600; color: var(--p-text-muted-color); padding: 0 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 0.5rem; }

.add-contact-form { display: flex; flex-direction: column; gap: 0.5rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--p-content-border-color); }
.empty-contacts { font-size: 0.8125rem; color: var(--p-text-muted-color); padding: 0.5rem 0; }

.contact-item { display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--p-content-border-color); }
.contact-item:last-child { border-bottom: none; }
.contact-info { display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; }
.contact-name { font-size: 0.875rem; font-weight: 500; }
.contact-role { font-size: 0.75rem; color: var(--p-text-muted-color); background: var(--p-content-hover-background); padding: 0.125rem 0.375rem; border-radius: 0.25rem; }
.contact-detail { font-size: 0.75rem; color: var(--p-text-muted-color); }
.contact-actions { display: flex; gap: 0.25rem; }

.contact-edit { display: flex; flex-direction: column; gap: 0.5rem; width: 100%; }
.contact-edit-actions { display: flex; gap: 0.5rem; }

.btn-icon { background: none; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; cursor: pointer; padding: 0.25rem 0.5rem; color: var(--p-text-muted-color); font-size: 0.75rem; }
.btn-icon:hover { background: var(--p-content-hover-background); }
.btn-icon-danger:hover { color: var(--p-red-600); border-color: var(--p-red-300); }

.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-sm { padding: 0.375rem 0.625rem; font-size: 0.8125rem; margin-left: 0; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
