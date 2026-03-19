<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { sendInvoice, createNextInvoice, deleteInvoice, generateSheet, updateInvoice, getInvoice } from '../../api/invoices'
import { todayStr } from '../../utils/dates'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  invoiceId: string
}>()

const emit = defineEmits<{
  saved: []
  error: [msg: string]
}>()

const toast = useToast()
const acting = ref(false)
const confirmDelete = ref(false)
const showMarkPaid = ref(false)
const paidDate = ref(todayStr())
const isSent = ref(false)

watch(visible, async (val) => {
  if (!val || !props.invoiceId) return
  try {
    const inv = await getInvoice(props.invoiceId)
    isSent.value = inv.sent_status === 'sent'
  } catch { /* ignore */ }
})

async function doAction(action: string) {
  acting.value = true
  try {
    switch (action) {
      case 'send':
        await sendInvoice(props.invoiceId)
        toast.success('Invoice sent')
        break
      case 'next':
        await createNextInvoice(props.invoiceId)
        toast.success('Next invoice created')
        break
      case 'recreate-sheet':
        await generateSheet(props.invoiceId, { force: true })
        toast.success('Google Sheet recreated')
        break
      case 'mark-sent':
        await updateInvoice(props.invoiceId, { sent_status: 'sent' })
        toast.success('Invoice marked as sent')
        break
      case 'mark-unsent':
        await updateInvoice(props.invoiceId, { sent_status: 'draft' })
        toast.success('Invoice marked as unsent')
        break
      case 'mark-paid':
        await updateInvoice(props.invoiceId, {
          sent_status: 'sent',
          paid_status: 'paid',
          paid_at: paidDate.value,
        })
        toast.success('Invoice marked as paid')
        break
      case 'delete':
        await deleteInvoice(props.invoiceId)
        toast.success('Invoice deleted')
        break
      default:
        throw new Error(`Unknown invoice action: ${action}`)
    }
    emit('saved')
    visible.value = false
  } catch (e) {
    emit('error', String(e))
  } finally {
    acting.value = false
    confirmDelete.value = false
    showMarkPaid.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    header="Invoice Actions"
    :modal="true"
    :style="{ width: '400px' }"
  >
    <div class="actions">
      <button class="action-btn" :disabled="acting" @click="doAction('send')">
        <i class="pi pi-envelope" />
        <span>Send Invoice</span>
      </button>
      <button v-if="!isSent" class="action-btn" :disabled="acting" @click="doAction('mark-sent')">
        <i class="pi pi-check" />
        <span>Mark as Sent</span>
      </button>
      <button v-else class="action-btn" :disabled="acting" @click="doAction('mark-unsent')">
        <i class="pi pi-undo" />
        <span>Mark as Unsent</span>
      </button>
      <button class="action-btn" :disabled="acting" @click="doAction('next')">
        <i class="pi pi-arrow-right" />
        <span>Create Next Invoice</span>
      </button>
      <button class="action-btn" :disabled="acting" @click="doAction('recreate-sheet')">
        <i class="pi pi-refresh" />
        <span>Recreate Google Sheet</span>
      </button>
      <div class="mark-paid-section">
        <button v-if="!showMarkPaid" class="action-btn success" :disabled="acting" @click="showMarkPaid = true">
          <i class="pi pi-dollar" />
          <span>Mark Paid</span>
        </button>
        <div v-else class="mark-paid-form">
          <label class="date-label">Paid Date</label>
          <div class="mark-paid-row">
            <input v-model="paidDate" type="date" class="date-input" />
            <button class="btn btn-sm btn-success" :disabled="acting" @click="doAction('mark-paid')">
              {{ acting ? 'Saving...' : 'Confirm' }}
            </button>
            <button class="btn btn-sm" :disabled="acting" @click="showMarkPaid = false">Cancel</button>
          </div>
        </div>
      </div>
      <div class="delete-section">
        <button v-if="!confirmDelete" class="action-btn danger" :disabled="acting" @click="confirmDelete = true">
          <i class="pi pi-trash" />
          <span>Delete Invoice</span>
        </button>
        <div v-else class="confirm-row">
          <span class="confirm-text">Delete this invoice?</span>
          <button class="btn btn-sm btn-danger" :disabled="acting" @click="doAction('delete')">
            {{ acting ? 'Deleting...' : 'Yes, Delete' }}
          </button>
          <button class="btn btn-sm" :disabled="acting" @click="confirmDelete = false">Cancel</button>
        </div>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.actions { display: flex; flex-direction: column; gap: 0.5rem; }
.action-btn {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.75rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem;
  background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; text-align: left;
  transition: all 0.15s; width: 100%; color: var(--p-text-color);
}
.action-btn:hover { background: var(--p-content-hover-background); border-color: var(--p-primary-color); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.action-btn i { font-size: 1.125rem; color: var(--p-primary-color); width: 1.5rem; }
.action-btn.success i { color: var(--p-green-600); }
.action-btn.success:hover { border-color: var(--p-green-400); }
.action-btn.danger i { color: var(--p-red-600); }
.action-btn.danger:hover { border-color: var(--p-red-400); }
.mark-paid-section { margin-top: 0.25rem; }
.mark-paid-form { padding: 0.75rem; border: 1px solid var(--p-green-200); border-radius: 0.375rem; background: color-mix(in srgb, var(--p-green-50) 50%, transparent); }
.date-label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; margin-bottom: 0.25rem; display: block; }
.mark-paid-row { display: flex; align-items: center; gap: 0.5rem; }
.date-input { padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; background: var(--p-form-field-background); color: var(--p-text-color); flex: 1; }
.btn-success { color: #fff; background: var(--p-green-600); border-color: var(--p-green-600); }
.btn-success:hover { background: var(--p-green-700); }
.btn-success:disabled { opacity: 0.5; cursor: not-allowed; }
.delete-section { margin-top: 0.5rem; border-top: 1px solid var(--p-content-border-color); padding-top: 0.75rem; }
.confirm-row { display: flex; align-items: center; gap: 0.5rem; }
.confirm-text { font-size: 0.875rem; color: var(--p-red-600); font-weight: 500; }
.btn { display: inline-flex; align-items: center; padding: 0.25rem 0.5rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.75rem; color: var(--p-text-color); }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn-danger { color: #fff; background: var(--p-red-600); border-color: var(--p-red-600); }
.btn-danger:hover { background: var(--p-red-700); }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
:root.p-dark .mark-paid-form { background: color-mix(in srgb, var(--p-green-500) 10%, transparent); border-color: color-mix(in srgb, var(--p-green-400) 30%, transparent); }
</style>
