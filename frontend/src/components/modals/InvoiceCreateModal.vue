<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { getContract, createInvoiceFromContract } from '../../api/contracts'
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
const tasks = ref<(ContractTask & { percentThisInvoice: number })[]>([])

watch(visible, async (val) => {
  if (!val || !props.contractId) return
  loading.value = true
  try {
    const contract = await getContract(props.contractId)
    tasks.value = contract.tasks.map((t) => ({
      ...t,
      percentThisInvoice: 0,
    }))
  } finally {
    loading.value = false
  }
})

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

async function save() {
  const selected = tasks.value
    .filter((t) => t.percentThisInvoice > 0)
    .map((t) => ({
      task_id: t.id,
      percent_this_invoice: t.percentThisInvoice,
    }))
  if (selected.length === 0) return

  saving.value = true
  try {
    await createInvoiceFromContract(props.contractId, { tasks: selected })
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
    :style="{ width: '600px' }"
  >
    <div v-if="loading" class="loading">Loading contract tasks...</div>
    <div v-else class="form">
      <p class="hint">Set the percent to bill for each task on this invoice.</p>
      <div class="task-grid">
        <div class="task-header">
          <span>Task</span>
          <span>Fee</span>
          <span>Billed</span>
          <span>% This Invoice</span>
        </div>
        <div v-for="task in tasks" :key="task.id" class="task-row">
          <span class="task-name">{{ task.name }}</span>
          <span class="task-fee">{{ formatCurrency(task.amount) }}</span>
          <span class="task-billed">{{ task.billed_percent.toFixed(1) }}%</span>
          <input
            v-model.number="task.percentThisInvoice"
            type="number"
            step="1"
            min="0"
            :max="100 - task.billed_percent"
            class="pct-input"
          />
        </div>
      </div>
    </div>
    <template #footer>
      <button class="btn" @click="visible = false">Cancel</button>
      <button class="btn btn-primary" :disabled="saving" @click="save">
        {{ saving ? 'Creating...' : 'Create Invoice' }}
      </button>
    </template>
  </Dialog>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.75rem; }
.hint { font-size: 0.8125rem; color: var(--p-surface-500); margin: 0; }
.task-grid { display: flex; flex-direction: column; gap: 0.25rem; }
.task-header, .task-row { display: grid; grid-template-columns: 1fr 6rem 5rem 6rem; gap: 0.5rem; align-items: center; padding: 0.375rem 0; }
.task-header { font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--p-surface-500); font-weight: 600; border-bottom: 1px solid var(--p-surface-200); }
.task-name { font-size: 0.8125rem; }
.task-fee, .task-billed { font-size: 0.8125rem; text-align: right; }
.pct-input { width: 100%; padding: 0.25rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; text-align: right; background: var(--p-form-field-background); color: var(--p-text-color); }
.loading { text-align: center; padding: 2rem; color: var(--p-surface-400); }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
