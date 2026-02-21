<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { generateSheet, exportPdf, sendInvoice, createNextInvoice } from '../../api/invoices'

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

async function doAction(action: string) {
  acting.value = true
  try {
    switch (action) {
      case 'generate':
        await generateSheet(props.invoiceId)
        toast.success('Google Sheet generated')
        break
      case 'pdf':
        await exportPdf(props.invoiceId)
        toast.success('PDF exported')
        break
      case 'send':
        await sendInvoice(props.invoiceId)
        toast.success('Invoice sent')
        break
      case 'next':
        await createNextInvoice(props.invoiceId)
        toast.success('Next invoice created')
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
      <button class="action-btn" :disabled="acting" @click="doAction('generate')">
        <i class="pi pi-file-excel" />
        <span>Generate Google Sheet</span>
      </button>
      <button class="action-btn" :disabled="acting" @click="doAction('pdf')">
        <i class="pi pi-file-pdf" />
        <span>Export PDF</span>
      </button>
      <button class="action-btn" :disabled="acting" @click="doAction('send')">
        <i class="pi pi-envelope" />
        <span>Send Invoice</span>
      </button>
      <button class="action-btn" :disabled="acting" @click="doAction('next')">
        <i class="pi pi-arrow-right" />
        <span>Create Next Invoice</span>
      </button>
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
</style>
