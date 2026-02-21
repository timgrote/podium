<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { getInvoice, updateInvoice } from '../../api/invoices'
import type { InvoiceLineItem } from '../../types'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  invoiceId: string
}>()

const emit = defineEmits<{
  saved: []
  error: [msg: string]
}>()

const toast = useToast()
const saving = ref(false)
const loading = ref(false)

const invoiceNumber = ref('')
const invoiceType = ref('')
const description = ref('')
const lineItems = ref<(InvoiceLineItem & { editQuantity: number })[]>([])

watch(visible, async (val) => {
  if (!val || !props.invoiceId) return
  loading.value = true
  try {
    const inv = await getInvoice(props.invoiceId)
    invoiceNumber.value = inv.invoice_number
    invoiceType.value = inv.type
    description.value = inv.description || ''
    lineItems.value = (inv.line_items || []).map((li) => ({
      ...li,
      editQuantity: li.quantity,
    }))
  } finally {
    loading.value = false
  }
})

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function cumulativePercent(item: InvoiceLineItem & { editQuantity: number }): number {
  if (!item.unit_price) return 0
  const thisAmount = (item.unit_price * item.editQuantity) / 100
  return ((item.previous_billing + thisAmount) / item.unit_price) * 100
}

function thisAmount(item: InvoiceLineItem & { editQuantity: number }): number {
  return (item.unit_price * item.editQuantity) / 100
}

const totalDue = computed(() =>
  lineItems.value.reduce((sum, li) => sum + thisAmount(li), 0),
)

async function save() {
  saving.value = true
  try {
    await updateInvoice(props.invoiceId, {
      description: description.value || undefined,
      line_items: lineItems.value.map((li) => ({
        quantity: li.editQuantity,
        unit_price: li.unit_price,
        previous_billing: li.previous_billing,
      })),
    })
    toast.success('Invoice updated')
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
    :header="`Edit Invoice ${invoiceNumber}`"
    :modal="true"
    :style="{ width: '700px' }"
  >
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="form">
      <div v-if="invoiceType === 'list'" class="field">
        <label>Description</label>
        <textarea v-model="description" rows="2" />
      </div>

      <div v-if="lineItems.length" class="task-grid">
        <div class="task-header">
          <span>Task</span>
          <span>Fee</span>
          <span>Prev Billing</span>
          <span>% This Inv</span>
          <span>Cumulative %</span>
          <span>This Amount</span>
        </div>
        <div v-for="item in lineItems" :key="item.id" class="task-row">
          <span class="task-name">{{ item.name }}</span>
          <span class="num">{{ formatCurrency(item.unit_price) }}</span>
          <span class="num">{{ formatCurrency(item.previous_billing) }}</span>
          <input
            v-model.number="item.editQuantity"
            type="number"
            step="1"
            min="0"
            class="pct-input"
          />
          <span class="num cumulative">{{ cumulativePercent(item).toFixed(1) }}%</span>
          <span class="num">{{ formatCurrency(thisAmount(item)) }}</span>
        </div>
        <div class="total-row">
          <span>Total Due</span>
          <span class="num total">{{ formatCurrency(totalDue) }}</span>
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
.field label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; }
.field textarea { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.task-grid { display: flex; flex-direction: column; gap: 0.25rem; }
.task-header, .task-row { display: grid; grid-template-columns: 1fr 5.5rem 5.5rem 4.5rem 5rem 5.5rem; gap: 0.5rem; align-items: center; padding: 0.375rem 0; }
.task-header { font-size: 0.625rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--p-text-muted-color); font-weight: 600; border-bottom: 1px solid var(--p-content-border-color); }
.task-name { font-size: 0.8125rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.num { font-size: 0.8125rem; text-align: right; }
.cumulative { font-weight: 600; color: var(--p-primary-color); }
.pct-input { width: 100%; padding: 0.25rem 0.375rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; text-align: right; background: var(--p-form-field-background); color: var(--p-text-color); }
.total-row { display: flex; justify-content: space-between; padding-top: 0.5rem; border-top: 2px solid var(--p-content-border-color); margin-top: 0.25rem; font-weight: 600; font-size: 0.875rem; }
.total { color: var(--p-text-color); }
.loading { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
