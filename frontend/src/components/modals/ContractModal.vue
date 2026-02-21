<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { getContract, createContract, updateContract } from '../../api/contracts'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  projectId: string
  contractId: string | null
}>()

const emit = defineEmits<{
  saved: []
  error: [msg: string]
}>()

const toast = useToast()
const saving = ref(false)
const loading = ref(false)

const form = ref({
  signed_at: '',
  file_path: '',
  notes: '',
})

const tasks = ref<{ name: string; description: string; amount: number }[]>([])

watch(visible, async (val) => {
  if (!val) return
  if (props.contractId) {
    loading.value = true
    try {
      const c = await getContract(props.contractId)
      form.value = {
        signed_at: c.signed_at ? c.signed_at.split('T')[0]! : '',
        file_path: c.file_path ?? '',
        notes: c.notes ?? '',
      }
      tasks.value = c.tasks.map((t) => ({
        name: t.name,
        description: t.description || '',
        amount: t.amount,
      }))
    } finally {
      loading.value = false
    }
  } else {
    form.value = { signed_at: '', file_path: '', notes: '' }
    tasks.value = [{ name: '', description: '', amount: 0 }]
  }
})

function addTask() {
  tasks.value.push({ name: '', description: '', amount: 0 })
}

function removeTask(index: number) {
  tasks.value.splice(index, 1)
}

async function save() {
  saving.value = true
  try {
    const validTasks = tasks.value.filter((t) => t.name.trim())
    if (props.contractId) {
      await updateContract(props.contractId, {
        signed_at: form.value.signed_at || undefined,
        file_path: form.value.file_path || undefined,
        notes: form.value.notes || undefined,
        tasks: validTasks,
      })
      toast.success('Contract updated')
    } else {
      await createContract({
        project_id: props.projectId,
        signed_at: form.value.signed_at || undefined,
        file_path: form.value.file_path || undefined,
        notes: form.value.notes || undefined,
        tasks: validTasks,
      })
      toast.success('Contract created')
    }
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
    :header="contractId ? 'Edit Contract' : 'New Contract'"
    :modal="true"
    :style="{ width: '600px' }"
  >
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="form">
      <div class="field-group">
        <div class="field">
          <label>Signed Date</label>
          <input v-model="form.signed_at" type="date" />
        </div>
        <div class="field">
          <label>File Path</label>
          <input v-model="form.file_path" type="text" />
        </div>
      </div>
      <div class="field">
        <label>Notes</label>
        <textarea v-model="form.notes" rows="2" />
      </div>

      <div class="tasks-section">
        <div class="tasks-header">
          <h4>Tasks</h4>
          <button class="btn btn-sm" @click="addTask">+ Add Task</button>
        </div>
        <div v-for="(task, i) in tasks" :key="i" class="task-row">
          <input v-model="task.name" placeholder="Task name" class="task-name" />
          <input
            v-model.number="task.amount"
            type="number"
            step="0.01"
            placeholder="Amount"
            class="task-amount"
          />
          <button class="btn-remove" @click="removeTask(i)">&times;</button>
        </div>
        <div class="task-total">
          Total: ${{ tasks.reduce((s, t) => s + (t.amount || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
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
.field label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; }
.field input, .field select, .field textarea { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.field-group { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.tasks-section { margin-top: 0.5rem; }
.tasks-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.tasks-header h4 { margin: 0; font-size: 0.875rem; }
.task-row { display: flex; gap: 0.5rem; margin-bottom: 0.375rem; align-items: center; }
.task-name { flex: 1; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.task-amount { width: 100px; padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem; font-size: 0.8125rem; text-align: right; background: var(--p-form-field-background); color: var(--p-text-color); }
.btn-remove { background: none; border: none; color: var(--p-red-600); cursor: pointer; font-size: 1.25rem; padding: 0 0.25rem; }
.task-total { text-align: right; font-weight: 600; font-size: 0.875rem; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--p-content-border-color); }
.loading { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
