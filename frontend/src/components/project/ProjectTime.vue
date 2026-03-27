<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { ProjectDetail } from '../../types'
import { getTimeEntries, getTimeSummary, deleteTimeEntry, type TimeEntry, type TimeSummary } from '../../api/timeEntries'
import { useToast } from '../../composables/useToast'
import LogTimeModal from '../modals/LogTimeModal.vue'

const props = defineProps<{
  project: ProjectDetail
}>()

const toast = useToast()
const timeEntries = ref<TimeEntry[]>([])
const timeSummary = ref<TimeSummary | null>(null)
const timeLoading = ref(false)
const showLogTimeModal = ref(false)
const editingEntry = ref<TimeEntry | null>(null)

const allContractTasks = computed(() => {
  return props.project.contracts?.flatMap(c => c.tasks || []) || []
})

async function loadTime() {
  timeLoading.value = true
  try {
    const [entries, summary] = await Promise.all([
      getTimeEntries({ project_id: props.project.id }),
      getTimeSummary(props.project.id),
    ])
    timeEntries.value = entries
    timeSummary.value = summary
  } catch (e) {
    console.error('Failed to load time entries:', e)
  } finally {
    timeLoading.value = false
  }
}

function openCreate() {
  editingEntry.value = null
  showLogTimeModal.value = true
}

function openEdit(entry: TimeEntry) {
  editingEntry.value = entry
  showLogTimeModal.value = true
}

async function handleDelete(id: string) {
  try {
    await deleteTimeEntry(id)
    toast.success('Entry deleted')
    await loadTime()
  } catch (e) {
    toast.error(String(e))
  }
}

onMounted(() => {
  loadTime()
})

defineExpose({ totalHours: computed(() => timeSummary.value?.total_hours || 0) })
</script>

<template>
  <div class="project-time">
    <div class="section-header">
      <h4>Time Tracking</h4>
      <button class="btn btn-sm btn-primary" @click="openCreate">
        <i class="pi pi-plus" /> Log Time
      </button>
    </div>

    <div v-if="timeLoading" class="loading">Loading...</div>

    <template v-else>
      <!-- Summary -->
      <div v-if="timeSummary && timeSummary.total_hours > 0" class="time-summary">
        <div class="time-total">
          <span class="time-total-hours">{{ Number(timeSummary.total_hours).toFixed(2) }}</span>
          <span class="time-total-label">total hours</span>
        </div>

        <div v-if="timeSummary.by_employee.length" class="time-breakdown">
          <h5>By Employee</h5>
          <div v-for="row in timeSummary.by_employee" :key="row.employee_id" class="breakdown-row">
            <span class="breakdown-name">{{ row.employee_name }}</span>
            <span class="breakdown-hours">{{ Number(row.total_hours).toFixed(2) }}h</span>
          </div>
        </div>

        <div v-if="timeSummary.by_task.filter(t => t.task_name).length" class="time-breakdown">
          <h5>By Contract Task</h5>
          <div v-for="row in timeSummary.by_task.filter(t => t.task_name)" :key="row.contract_task_id || 'none'" class="breakdown-row">
            <span class="breakdown-name">{{ row.task_name }}</span>
            <span class="breakdown-hours">{{ Number(row.total_hours).toFixed(2) }}h</span>
          </div>
        </div>
      </div>

      <!-- Recent entries -->
      <div v-if="timeEntries.length" class="time-entries-section">
        <h5>Recent Entries</h5>
        <div class="time-entries-list">
          <div v-for="entry in timeEntries.slice(0, 20)" :key="entry.id" class="time-entry-row" @click="openEdit(entry)">
            <span class="te-date">{{ entry.date }}</span>
            <span class="te-employee">{{ entry.employee_name }}</span>
            <span v-if="entry.contract_task_name" class="te-task">{{ entry.contract_task_name }}</span>
            <span v-if="entry.description" class="te-desc">{{ entry.description }}</span>
            <span class="te-hours">{{ Number(entry.hours).toFixed(2) }}h</span>
            <button class="btn-icon btn-delete" @click.stop="handleDelete(entry.id)">
              <i class="pi pi-trash" />
            </button>
          </div>
        </div>
      </div>

      <div v-if="!timeSummary || timeSummary.total_hours === 0" class="empty">
        No time logged yet
      </div>
    </template>

    <LogTimeModal
      v-model:visible="showLogTimeModal"
      :project-id="project.id"
      :project-name="project.project_name"
      :contract-tasks="allContractTasks"
      :entry="editingEntry"
      @saved="loadTime"
    />
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

.loading {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

.empty {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all 0.15s;
  color: var(--p-text-color);
}

.btn:hover {
  background: var(--p-content-hover-background);
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.btn-primary {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.btn-primary:hover {
  background: var(--p-primary-hover-color);
}

.time-summary {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.time-total {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.time-total-hours {
  font-size: 2rem;
  font-weight: 700;
  color: var(--p-primary-color);
}

.time-total-label {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.time-breakdown {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.time-breakdown h5 {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 0.25rem 0;
}

.breakdown-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.375rem 0;
  border-bottom: 1px solid var(--p-content-border-color);
}

.breakdown-row:last-child { border-bottom: none; }

.breakdown-name {
  font-size: 0.875rem;
}

.breakdown-hours {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-primary-color);
}

.time-entries-section h5 {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 0.5rem 0;
}

.time-entries-list {
  display: flex;
  flex-direction: column;
}

.time-entry-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.375rem 0;
  border-bottom: 1px solid var(--p-content-border-color);
  font-size: 0.8125rem;
  cursor: pointer;
}

.time-entry-row:hover { background: var(--p-content-hover-background); }
.time-entry-row:last-child { border-bottom: none; }

.te-date {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  min-width: 80px;
}

.te-employee {
  font-weight: 500;
  min-width: 100px;
}

.te-task {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  padding: 0.0625rem 0.375rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.25rem;
}

.te-desc {
  flex: 1;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.te-hours {
  font-weight: 600;
  color: var(--p-primary-color);
  margin-left: auto;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--p-text-muted-color);
  padding: 0.25rem;
  font-size: 0.75rem;
}

.btn-icon:hover { color: var(--p-text-color); }
.btn-delete:hover { color: #dc2626; }
</style>
