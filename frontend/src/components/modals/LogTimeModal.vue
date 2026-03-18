<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import type { ProjectSummary, ContractTask } from '../../types'
import { createTimeEntry } from '../../api/timeEntries'
import { getProjects } from '../../api/projects'
import { useAuth } from '../../composables/useAuth'
import { useToast } from '../../composables/useToast'
import { todayStr } from '../../utils/dates'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  projectId?: string | null
  projectName?: string | null
  contractTasks?: ContractTask[]
}>()

const emit = defineEmits<{
  saved: []
}>()

const { user } = useAuth()
const toast = useToast()
const saving = ref(false)
const showDetails = ref(false)

const selectedProjectId = ref('')
const selectedHours = ref<number | null>(null)
const customHours = ref('')
const showCustom = ref(false)
const contractTaskId = ref('')
const description = ref('')
const entryDate = ref(todayStr())

const projects = ref<ProjectSummary[]>([])
const projectsLoaded = ref(false)

const hourButtons = [0.5, 1, 2, 4, 8]

const effectiveHours = computed(() => {
  if (showCustom.value) return parseFloat(customHours.value) || 0
  return selectedHours.value || 0
})

const canSave = computed(() => {
  return effectiveHours.value > 0 && (selectedProjectId.value || props.projectId)
})

watch(visible, async (val) => {
  if (!val) return
  selectedHours.value = null
  customHours.value = ''
  showCustom.value = false
  contractTaskId.value = ''
  description.value = ''
  entryDate.value = todayStr()
  showDetails.value = false

  if (props.projectId) {
    selectedProjectId.value = props.projectId
  } else {
    selectedProjectId.value = ''
    if (!projectsLoaded.value) {
      try {
        projects.value = await getProjects()
        projectsLoaded.value = true
      } catch (e) {
        toast.error(String(e))
      }
    }
  }
})

function selectHours(h: number) {
  showCustom.value = false
  selectedHours.value = h
}

function selectCustom() {
  showCustom.value = true
  selectedHours.value = null
}

async function save() {
  if (!canSave.value || !user.value) return
  saving.value = true
  try {
    await createTimeEntry({
      employee_id: user.value.id,
      project_id: selectedProjectId.value || props.projectId!,
      contract_task_id: contractTaskId.value || undefined,
      hours: effectiveHours.value,
      date: entryDate.value,
      description: description.value || undefined,
    })
    toast.success(`Logged ${effectiveHours.value}h`)
    emit('saved')
    visible.value = false
  } catch (e) {
    toast.error(String(e))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    header="Log Time"
    :modal="true"
    :style="{ width: '420px' }"
  >
    <div class="log-time-form">
      <div v-if="!props.projectId" class="field">
        <label>Project</label>
        <select v-model="selectedProjectId">
          <option value="" disabled>Select project...</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">
            {{ p.project_name }}{{ p.job_code ? ` (${p.job_code})` : '' }}
          </option>
        </select>
      </div>
      <div v-else class="project-label">
        {{ props.projectName || props.projectId }}
      </div>

      <div class="hours-section">
        <label>Hours</label>
        <div class="hour-buttons">
          <button
            v-for="h in hourButtons"
            :key="h"
            class="hour-btn"
            :class="{ active: !showCustom && selectedHours === h }"
            @click="selectHours(h)"
          >
            {{ h }}
          </button>
          <button
            class="hour-btn"
            :class="{ active: showCustom }"
            @click="selectCustom"
          >
            Other
          </button>
        </div>
        <input
          v-if="showCustom"
          v-model="customHours"
          type="number"
          step="0.25"
          min="0.25"
          placeholder="Hours..."
          class="custom-hours-input"
          autofocus
        />
      </div>

      <button class="details-toggle" @click="showDetails = !showDetails">
        <i class="pi" :class="showDetails ? 'pi-chevron-up' : 'pi-chevron-down'" />
        Details
      </button>

      <div v-if="showDetails" class="details-section">
        <div class="field">
          <label>Date</label>
          <input v-model="entryDate" type="date" />
        </div>
        <div v-if="props.contractTasks && props.contractTasks.length" class="field">
          <label>Contract Task</label>
          <select v-model="contractTaskId">
            <option value="">-- None --</option>
            <option v-for="ct in props.contractTasks" :key="ct.id" :value="ct.id">
              {{ ct.name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>Description</label>
          <textarea v-model="description" rows="2" placeholder="What did you work on?" />
        </div>
      </div>
    </div>

    <template #footer>
      <button class="btn" @click="visible = false">Cancel</button>
      <button class="btn btn-primary" :disabled="saving || !canSave" @click="save">
        {{ saving ? 'Saving...' : `Log ${effectiveHours > 0 ? effectiveHours + 'h' : ''}` }}
      </button>
    </template>
  </Dialog>
</template>

<style scoped>
.log-time-form { display: flex; flex-direction: column; gap: 1rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.field label, .hours-section > label { font-size: 0.75rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; letter-spacing: 0.05em; }
.field input, .field select, .field textarea { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); }
.project-label { font-weight: 600; font-size: 0.9375rem; padding: 0.25rem 0; }
.hours-section { display: flex; flex-direction: column; gap: 0.5rem; }
.hour-buttons { display: flex; gap: 0.5rem; }
.hour-btn {
  flex: 1;
  padding: 0.625rem 0;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.hour-btn:hover { border-color: var(--p-primary-color); color: var(--p-primary-color); }
.hour-btn.active { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.custom-hours-input { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; background: var(--p-form-field-background); color: var(--p-text-color); width: 100%; }
.details-toggle {
  display: flex; align-items: center; gap: 0.375rem;
  background: none; border: none; cursor: pointer;
  color: var(--p-text-muted-color); font-size: 0.8125rem;
  padding: 0;
}
.details-toggle:hover { color: var(--p-text-color); }
.details-toggle .pi { font-size: 0.625rem; }
.details-section { display: flex; flex-direction: column; gap: 0.75rem; }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
