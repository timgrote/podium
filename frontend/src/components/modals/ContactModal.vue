<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import type { Contact, Client } from '../../types'
import { getContacts, updateContact } from '../../api/contacts'
import { useClients } from '../../composables/useClients'
import { useToast } from '../../composables/useToast'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  contactId: string | null
}>()

const emit = defineEmits<{
  saved: []
  error: [msg: string]
}>()

const { clients, load: loadClients } = useClients()
const toast = useToast()
const loading = ref(false)
const saving = ref(false)

const form = ref({
  name: '',
  email: '',
  phone: '',
  role: '',
  notes: '',
  client_id: '',
})

watch(visible, async (val) => {
  if (!val || !props.contactId) return
  loading.value = true
  try {
    const [all] = await Promise.all([getContacts(), loadClients()])
    const ct = all.find(c => c.id === props.contactId)
    if (!ct) {
      emit('error', 'Contact not found')
      visible.value = false
      return
    }
    form.value = {
      name: ct.name || '',
      email: ct.email || '',
      phone: ct.phone || '',
      role: ct.role || '',
      notes: ct.notes || '',
      client_id: ct.client_id || '',
    }
  } catch (e) {
    emit('error', String(e))
    visible.value = false
  } finally {
    loading.value = false
  }
})

async function save() {
  if (!form.value.name.trim()) {
    toast.error('Contact name is required')
    return
  }
  if (!props.contactId) return
  saving.value = true
  try {
    await updateContact(props.contactId, {
      name: form.value.name,
      email: form.value.email || null,
      phone: form.value.phone || null,
      role: form.value.role || null,
      notes: form.value.notes || null,
      client_id: form.value.client_id || null,
    })
    toast.success('Contact updated')
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
    header="Edit Contact"
    :modal="true"
    :style="{ width: '480px' }"
  >
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="form">
      <div class="field">
        <label>Name *</label>
        <input v-model="form.name" type="text" />
      </div>
      <div class="field-row">
        <div class="field">
          <label>Email</label>
          <input v-model="form.email" type="email" />
        </div>
        <div class="field">
          <label>Phone</label>
          <input v-model="form.phone" type="text" />
        </div>
      </div>
      <div class="field">
        <label>Role</label>
        <input v-model="form.role" type="text" placeholder="e.g., Project Manager" />
      </div>
      <div class="field">
        <label>Notes</label>
        <textarea v-model="form.notes" rows="3" placeholder="Notes about this contact" />
      </div>
      <div class="field">
        <label>Client</label>
        <select v-model="form.client_id">
          <option value="">-- None --</option>
          <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.company || c.name }}</option>
        </select>
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
.loading { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.form { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.field label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; }
.field input, .field select, .field textarea { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
