<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { promoteToContract } from '../../api/proposals'

const visible = defineModel<boolean>('visible', { required: true })

defineProps<{
  proposalId: string
}>()

const emit = defineEmits<{
  saved: []
  error: [msg: string]
}>()

const toast = useToast()
const saving = ref(false)
const signedAt = ref('')

async function promote(proposalId: string) {
  saving.value = true
  try {
    await promoteToContract(proposalId, {
      signed_at: signedAt.value || undefined,
    })
    toast.success('Proposal promoted to contract')
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
    header="Promote to Contract"
    :modal="true"
    :style="{ width: '400px' }"
  >
    <div class="form">
      <p>This will create a contract from this proposal's tasks and mark the proposal as accepted.</p>
      <div class="field">
        <label>Signed Date</label>
        <input v-model="signedAt" type="date" />
      </div>
    </div>
    <template #footer>
      <button class="btn" @click="visible = false">Cancel</button>
      <button class="btn btn-primary" :disabled="saving" @click="promote(proposalId)">
        {{ saving ? 'Promoting...' : 'Promote' }}
      </button>
    </template>
  </Dialog>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.75rem; }
.form p { margin: 0; font-size: 0.875rem; color: var(--p-surface-600); }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.field label { font-size: 0.75rem; font-weight: 600; color: var(--p-surface-600); text-transform: uppercase; }
.field input { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
