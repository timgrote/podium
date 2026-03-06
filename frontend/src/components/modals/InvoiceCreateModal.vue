<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { getContract, createInvoiceFromContract, getNextInvoiceNumber } from '../../api/contracts'
import type { ContractTask } from '../../types'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  contractId: string
}>()

const emit = defineEmits<{
  saved: []
  error: [msg: string]
}>()

const toast = useToast()
const saving = ref(false)
const loading = ref(false)
const invoiceNumber = ref('')
const invoiceDate = ref('')
const tasks = ref<(ContractTask & { cumulativePercent: number })[]>([])

function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

watch(visible, async (val) => {
  if (!val || !props.contractId) return
  loading.value = true
  invoiceDate.value = todayStr()
  try {
    const [contract, nextNum] = await Promise.all([
      getContract(props.contractId),
      getNextInvoiceNumber(props.contractId),
    ])
    invoiceNumber.value = nextNum.invoice_number
    tasks.value = contract.tasks.map((t) => ({
      ...t,
      cumulativePercent: t.billed_percent,
    }))
  } catch (e) {
    emit('error', String(e))
    visible.value = false
  } finally {
    loading.value = false
  }
})

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function thisAmount(task: ContractTask & { cumulativePercent: number }): number {
  return (task.amount * task.cumulativePercent / 100) - task.billed_amount
}

const invoiceTotal = computed(() =>
  tasks.value.reduce((sum, t) => sum + thisAmount(t), 0),
)

async function save() {
  const selected = tasks.value
    .filter((t) => t.cumulativePercent > t.billed_percent)
    .map((t) => ({
      task_id: t.id,
      percent_this_invoice: t.cumulativePercent - t.billed_percent,
    }))
  if (selected.length === 0) return

  saving.value = true
  try {
    await createInvoiceFromContract(props.contractId, {
      tasks: selected,
      invoice_number: invoiceNumber.value || undefined,
      invoice_date: invoiceDate.value || undefined,
    })
    toast.success('Invoice created')
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
    header="Create Invoice from Contract"
    :modal="true"
    :style="{ width: '720px' }"
  >
    <div v-if="loading" class="loading">Loading contract tasks...</div>
    <div v-else class="form">
      <div class="field-row">
        <div class="field">
          <label>Invoice Number</label>
          <input v-model="invoiceNumber" type="text" />
        </div>
        <div class="field">
          <label>Invoice Date</label>
          <input v-model="invoiceDate" type="date" />
        </div>
      </div>
      <div class="task-grid">
        <div class="task-header">
          <span>Task</span>
          <span>Fee</span>
          <span>Prev Billing</span>
          <span>Cumulative %</span>
          <span>This Amount</span>
        </div>
        <div v-for="task in tasks" :key="task.id" class="task-row">
          <span class="task-name">{{ task.name }}</span>
          <span class="task-fee">{{ formatCurrency(task.amount) }}</span>
          <span class="task-prev">{{ formatCurrency(task.billed_amount) }}</span>
          <input
            v-model.number="task.cumulativePercent"
            type="number"
            step="1"
            :min="task.billed_percent"
            max="100"
            class="pct-input"
          />
          <span class="task-amount">{{ formatCurrency(thisAmount(task)) }}</span>
        </div>
        <div class="total-row">
          <span>Invoice Total</span>
          <span class="total-amount">{{ formatCurrency(invoiceTotal) }}</span>
        </div>
      </div>
    </div>
    <template #footer>
      <button class="btn" @click="visible = false">Cancel</button>
      <button class="btn btn-primary" :disabled="saving || invoiceTotal <= 0" @click="save">
        {{ saving ? 'Creating...' : 'Create Invoice' }}
      </button>
    </template>
  </Dialog>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.field label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; }
.field input[type="text"], .field input[type="date"] { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); width: 100%; box-sizing: border-box; }
.field-row { display: flex; gap: 0.75rem; }
.task-grid { display: flex; flex-direction: column; gap: 0.25rem; }
.task-header, .task-row { display: grid; grid-template-columns: 1fr 6rem 6rem 5.5rem 6rem; gap: 0.5rem; align-items: center; padding: 0.375rem 0; }
.task-header { font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--p-text-muted-color); font-weight: 600; border-bottom: 1px solid var(--p-content-border-color); }
.task-header span:not(:first-child) { text-align: right; }
.task-name { font-size: 0.8125rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-fee, .task-prev, .task-amount { font-size: 0.8125rem; text-align: right; }
.total-row { display: flex; justify-content: space-between; padding-top: 0.5rem; border-top: 2px solid var(--p-content-border-color); margin-top: 0.25rem; font-weight: 600; font-size: 0.875rem; }
.total-amount { color: var(--p-text-color); }
.pct-input { width: 100%; padding: 0.25rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; text-align: right; background: var(--p-form-field-background); color: var(--p-text-color); }
.loading { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
