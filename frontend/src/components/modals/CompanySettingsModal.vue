<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { getCompanySettings, updateCompanySettings, uploadLogo } from '../../api/company'

const visible = defineModel<boolean>('visible', { required: true })

const emit = defineEmits<{
  saved: []
  error: [msg: string]
}>()

const toast = useToast()
const saving = ref(false)
const loading = ref(false)

const form = ref<Record<string, string>>({
  company_name: '',
  company_email: '',
  company_phone: '',
  company_address: '',
  logo_url: '',
  invoice_template_id: '',
  invoice_drive_folder_id: '',
})

watch(visible, async (val) => {
  if (!val) return
  loading.value = true
  try {
    const settings = await getCompanySettings()
    form.value = {
      company_name: settings.company_name || '',
      company_email: settings.company_email || '',
      company_phone: settings.company_phone || '',
      company_address: settings.company_address || '',
      logo_url: settings.logo_url || '',
      invoice_template_id: settings.invoice_template_id || '',
      invoice_drive_folder_id: settings.invoice_drive_folder_id || '',
    }
  } catch (e) {
    emit('error', String(e))
    visible.value = false
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  try {
    await updateCompanySettings(form.value)
    toast.success('Settings saved')
    emit('saved')
    visible.value = false
  } catch (e) {
    emit('error', String(e))
  } finally {
    saving.value = false
  }
}

async function handleLogoUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const result = await uploadLogo(file)
    form.value.logo_url = result.logo_url
    toast.success('Logo uploaded')
  } catch (e) {
    emit('error', String(e))
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    header="Company Settings"
    :modal="true"
    :style="{ width: '500px' }"
  >
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="form">
      <div class="field">
        <label>Company Name</label>
        <input v-model="form.company_name" type="text" />
      </div>
      <div class="field">
        <label>Email</label>
        <input v-model="form.company_email" type="email" />
      </div>
      <div class="field">
        <label>Phone</label>
        <input v-model="form.company_phone" type="text" />
      </div>
      <div class="field">
        <label>Address</label>
        <textarea v-model="form.company_address" rows="2" />
      </div>
      <div class="field">
        <label>Logo</label>
        <div class="logo-row">
          <img v-if="form.logo_url" :src="form.logo_url" alt="Logo" class="logo-preview" />
          <input type="file" accept="image/*" @change="handleLogoUpload" />
        </div>
      </div>
      <div class="field">
        <label>Invoice Template ID</label>
        <input v-model="form.invoice_template_id" type="text" placeholder="Google Sheets template ID" />
      </div>
      <div class="field">
        <label>Invoice Drive Folder ID</label>
        <input v-model="form.invoice_drive_folder_id" type="text" placeholder="Google Drive folder ID" />
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
.logo-row { display: flex; align-items: center; gap: 1rem; }
.logo-preview { height: 40px; border-radius: 0.25rem; }
.loading { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
