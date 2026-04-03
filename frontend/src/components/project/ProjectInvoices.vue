<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ProjectDetail } from '../../types'
import { generateSheet, exportPdf as exportInvoicePdfApi } from '../../api/invoices'
import { useToast } from '../../composables/useToast'
import { formatDate } from '../../utils/dates'

const props = defineProps<{
  project: ProjectDetail
}>()

const emit = defineEmits<{
  editInvoice: [invoiceId: string]
  deleteInvoice: [invoiceId: string]
  invoiceActions: [invoiceId: string]
  createInvoice: [contractId: string]
  refreshProject: []
}>()

const latestContractId = computed(() => {
  const contracts = props.project.contracts
  if (contracts.length === 0) return null
  return contracts[contracts.length - 1]!.id
})

const toast = useToast()
const invoiceBusy = ref<Record<string, string>>({})

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', minimumFractionDigits: 2,
  }).format(value)
}

async function genInvoiceSheet(invoiceId: string) {
  invoiceBusy.value[invoiceId] = 'gen'
  try {
    const result = await generateSheet(invoiceId)
    const inv = props.project.invoices.find(i => i.id === invoiceId)
    if (inv) {
      inv.data_path = result.data_path
      inv.pdf_path = null
    }
    toast.success('Google Sheet generated')
    if (result.data_path) window.open(result.data_path, '_blank')
  } catch (e) {
    toast.error(String(e))
  } finally {
    delete invoiceBusy.value[invoiceId]
  }
}

async function exportInvoicePdf(invoiceId: string) {
  invoiceBusy.value[invoiceId] = 'pdf'
  try {
    const result = await exportInvoicePdfApi(invoiceId)
    const inv = props.project.invoices.find(i => i.id === invoiceId)
    if (inv) inv.pdf_path = result.pdf_path
    toast.success('PDF exported')
    if (result.pdf_path) window.open(result.pdf_path, '_blank')
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  } finally {
    delete invoiceBusy.value[invoiceId]
  }
}
</script>

<template>
  <div class="section">
    <div class="section-header">
      <h4>Invoices</h4>
      <button
        v-if="latestContractId"
        class="btn btn-sm btn-primary"
        @click="emit('createInvoice', latestContractId!)"
      >
        <i class="pi pi-plus" /> Add Invoice
      </button>
    </div>
    <div v-if="project.invoices.length === 0" class="empty">No invoices</div>
    <div v-for="invoice in project.invoices" :key="invoice.id" class="sub-card" @click="emit('editInvoice', invoice.id)">
      <div class="sub-card-header">
        <span class="sub-card-title">{{ invoice.invoice_number }}</span>
        <span class="sub-card-amount">{{ formatCurrency(invoice.total_due) }}</span>
        <span
          class="status-pill"
          :class="{
            sent: invoice.sent_status === 'sent',
            paid: invoice.paid_status === 'paid',
          }"
        >
          {{ invoice.paid_status === 'paid' ? 'Paid' : invoice.sent_status === 'sent' ? 'Sent' : 'Draft' }}
        </span>
        <span v-if="invoice.invoice_date" class="sub-card-date">
          {{ formatDate(invoice.invoice_date) }}
        </span>
        <div class="sub-card-actions" @click.stop>
          <a
            v-if="invoice.data_path && invoice.data_path.includes('google.com')"
            class="btn-icon"
            title="Open Google Sheet"
            :href="invoice.data_path"
            target="_blank"
          >
            <i class="pi pi-file-excel" style="color: var(--p-green-600)" />
          </a>
          <button
            v-else
            class="btn-icon"
            title="Generate Google Sheet"
            :disabled="!!invoiceBusy[invoice.id]"
            @click="genInvoiceSheet(invoice.id)"
          >
            <i class="pi" :class="invoiceBusy[invoice.id] === 'gen' ? 'pi-spin pi-spinner' : 'pi-file-excel'" :style="invoiceBusy[invoice.id] === 'gen' ? '' : 'color: var(--p-green-600)'" />
          </button>
          <button
            v-if="invoice.data_path && invoice.data_path.includes('google.com') && !invoice.pdf_path"
            class="btn-icon"
            title="Export PDF"
            :disabled="!!invoiceBusy[invoice.id]"
            @click="exportInvoicePdf(invoice.id)"
          >
            <i class="pi" :class="invoiceBusy[invoice.id] === 'pdf' ? 'pi-spin pi-spinner' : 'pi-file-pdf'" :style="invoiceBusy[invoice.id] === 'pdf' ? '' : 'color: var(--p-red-600)'" />
          </button>
          <a
            v-if="invoice.pdf_path"
            class="btn-icon"
            title="View PDF"
            :href="invoice.pdf_path"
            target="_blank"
          >
            <i class="pi pi-file-pdf" style="color: var(--p-red-600)" />
          </a>
          <button class="btn-icon" title="Actions" @click="emit('invoiceActions', invoice.id)">
            <i class="pi pi-ellipsis-h" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
.section-header h4 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
}
.sub-card {
  background: var(--p-content-hover-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
}
.sub-card:hover { border-color: var(--p-primary-color); }
.sub-card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.sub-card-title { font-weight: 600; font-size: 0.875rem; }
.sub-card-amount { font-weight: 500; font-size: 0.875rem; color: var(--p-text-muted-color); }
.sub-card-date { font-size: 0.75rem; color: var(--p-text-muted-color); }
.sub-card-actions { margin-left: auto; display: flex; gap: 0.25rem; }
.status-pill {
  font-size: 0.625rem; text-transform: uppercase; letter-spacing: 0.05em;
  padding: 0.125rem 0.5rem; border-radius: 9999px;
  background: var(--p-content-hover-background); color: var(--p-text-muted-color); font-weight: 600;
}
.status-pill.sent { background: var(--p-blue-100); color: var(--p-blue-700); }
.status-pill.paid, .status-pill.accepted { background: var(--p-green-100); color: var(--p-green-700); }
.btn-icon {
  background: none; border: none; cursor: pointer; padding: 0.25rem;
  color: var(--p-text-muted-color); border-radius: 0.25rem; font-size: 0.875rem;
}
.btn-icon-green { color: var(--p-green-600); }
.btn-icon-green:hover { color: var(--p-green-700); }
.btn-icon:hover { background: var(--p-content-hover-background); color: var(--p-text-color); }
.btn { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.375rem 0.75rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.75rem; font-weight: 500; color: var(--p-text-color); }
.btn:hover { background: var(--p-content-hover-background); }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.empty { font-size: 0.8125rem; color: var(--p-text-muted-color); font-style: italic; }
</style>
