<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import type { Employee } from '../types'
import type { TimeEntry } from '../api/timeEntries'
import { getTimeEntries, deleteTimeEntry } from '../api/timeEntries'
import { getEmployees } from '../api/employees'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { todayStr } from '../utils/dates'
import LogTimeModal from '../components/modals/LogTimeModal.vue'

const { user } = useAuth()
const toast = useToast()
const entries = ref<TimeEntry[]>([])
const employees = ref<Employee[]>([])
const loading = ref(true)
const showLogModal = ref(false)
const selectedEmployeeId = ref('')
const editingEntry = ref<TimeEntry | null>(null)

// Week navigation
const weekOffset = ref(0)

function getMonday(date: Date): Date {
  const d = new Date(date)
  const day = d.getDay()
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  d.setDate(diff)
  d.setHours(0, 0, 0, 0)
  return d
}

function formatYMD(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const weekStart = computed(() => {
  const today = new Date()
  const monday = getMonday(today)
  monday.setDate(monday.getDate() + weekOffset.value * 7)
  return monday
})

const weekDays = computed(() => {
  const days: { date: Date; label: string; dateStr: string; isToday: boolean }[] = []
  const today = todayStr()
  for (let i = 0; i < 6; i++) {
    const d = new Date(weekStart.value)
    d.setDate(d.getDate() + i)
    const dateStr = formatYMD(d)
    days.push({
      date: d,
      label: d.toLocaleDateString('en-US', { weekday: 'short' }),
      dateStr,
      isToday: dateStr === today,
    })
  }
  return days
})

const weekDateRange = computed(() => {
  const start = weekDays.value[0]!
  const end = weekDays.value[weekDays.value.length - 1]!
  return { from: start.dateStr, to: end.dateStr }
})

const dailyTotals = computed(() => {
  const totals: Record<string, number> = {}
  for (const day of weekDays.value) {
    totals[day.dateStr] = 0
  }
  for (const entry of entries.value) {
    if (entry.date in totals) {
      totals[entry.date] = (totals[entry.date] ?? 0) + Number(entry.hours)
    }
  }
  return totals
})

const weekTotal = computed(() => {
  return Object.values(dailyTotals.value).reduce((sum, h) => sum + h, 0)
})

interface ProjectGroup {
  projectId: string
  projectName: string
  totalHours: number
  entries: TimeEntry[]
}

const projectGroups = computed<ProjectGroup[]>(() => {
  const map = new Map<string, ProjectGroup>()
  for (const entry of entries.value) {
    let group = map.get(entry.project_id)
    if (!group) {
      group = {
        projectId: entry.project_id,
        projectName: entry.project_name || entry.project_id,
        totalHours: 0,
        entries: [],
      }
      map.set(entry.project_id, group)
    }
    group.totalHours += Number(entry.hours)
    group.entries.push(entry)
  }
  // Sort entries within each group by date
  for (const group of map.values()) {
    group.entries.sort((a, b) => a.date.localeCompare(b.date))
  }
  // Sort groups by total hours descending
  return [...map.values()].sort((a, b) => b.totalHours - a.totalHours)
})

function dayLabel(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

const effectiveEmployeeId = computed(() => {
  return selectedEmployeeId.value || user.value?.id || ''
})

async function loadEntries() {
  if (!effectiveEmployeeId.value) return
  loading.value = true
  try {
    entries.value = await getTimeEntries({
      employee_id: effectiveEmployeeId.value,
      date_from: weekDateRange.value.from,
      date_to: weekDateRange.value.to,
    })
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

async function loadEmployees() {
  try {
    employees.value = await getEmployees()
  } catch (e) {
    toast.error(String(e))
  }
}

async function handleDelete(id: string) {
  try {
    await deleteTimeEntry(id)
    toast.success('Entry deleted')
    await loadEntries()
  } catch (e) {
    toast.error(String(e))
  }
}

function openEdit(entry: TimeEntry) {
  editingEntry.value = entry
  showLogModal.value = true
}

function openCreate() {
  editingEntry.value = null
  showLogModal.value = true
}

watch([effectiveEmployeeId, weekOffset], loadEntries)

onMounted(async () => {
  await loadEmployees()
  await loadEntries()
})
</script>

<template>
  <div class="timesheet">
    <div class="page-header">
      <h1>Timesheet</h1>
      <div class="header-actions">
        <select v-model="selectedEmployeeId" class="employee-select">
          <option value="">{{ user ? `${user.first_name} ${user.last_name}` : 'Me' }}</option>
          <option
            v-for="emp in employees.filter(e => e.id !== user?.id)"
            :key="emp.id"
            :value="emp.id"
          >
            {{ emp.first_name }} {{ emp.last_name }}
          </option>
        </select>
        <button class="btn-log-time" @click="openCreate">
          <i class="pi pi-plus" /> Log Time
        </button>
      </div>
    </div>

    <!-- Week total summary -->
    <div class="week-summary">
      <span class="week-summary-hours">{{ weekTotal.toFixed(1) }}h</span>
      <span class="week-summary-label">logged this week</span>
    </div>

    <!-- Week navigation bar -->
    <div class="week-bar">
      <button class="week-nav" @click="weekOffset--">
        <i class="pi pi-chevron-left" />
      </button>
      <div class="week-days">
        <div
          v-for="day in weekDays"
          :key="day.dateStr"
          class="day-cell"
          :class="{ today: day.isToday, 'has-hours': (dailyTotals[day.dateStr] || 0) > 0 }"
        >
          <span class="day-label">{{ day.label }}</span>
          <span class="day-date">{{ day.date.getDate() }}</span>
          <span class="day-hours">{{ (dailyTotals[day.dateStr] || 0).toFixed(1) }}h</span>
        </div>
      </div>
      <button class="week-nav" @click="weekOffset++">
        <i class="pi pi-chevron-right" />
      </button>
    </div>

    <!-- Weekly entries by project -->
    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="projectGroups.length === 0" class="empty-state">
      <p>No time logged this week</p>
    </div>

    <div v-else class="project-list">
      <div v-for="group in projectGroups" :key="group.projectId" class="project-group">
        <div class="project-header">
          <span class="project-name">{{ group.projectName }}</span>
          <span class="project-total">{{ group.totalHours.toFixed(1) }}h</span>
        </div>
        <div class="project-entries">
          <div v-for="entry in group.entries" :key="entry.id" class="entry-row" @click="openEdit(entry)">
            <span class="entry-day">{{ dayLabel(entry.date) }}</span>
            <span v-if="entry.contract_task_name" class="entry-task">{{ entry.contract_task_name }}</span>
            <span v-if="entry.description" class="entry-desc">{{ entry.description }}</span>
            <div class="entry-right">
              <span class="entry-hours">{{ Number(entry.hours).toFixed(1) }}h</span>
              <button class="btn-icon btn-delete" @click.stop="handleDelete(entry.id)">
                <i class="pi pi-trash" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <LogTimeModal
      v-model:visible="showLogModal"
      :entry="editingEntry"
      @saved="loadEntries"
    />
  </div>
</template>

<style scoped>
.timesheet {
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.employee-select {
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
}

.btn-log-time {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: none;
  border-radius: 0.375rem;
  background: var(--p-primary-color);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-log-time:hover { filter: brightness(1.1); }
.btn-log-time .pi { font-size: 0.625rem; }

/* Week summary */
.week-summary {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.week-summary-hours {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.week-summary-label {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

/* Week bar */
.week-bar {
  display: flex;
  align-items: stretch;
  gap: 0.25rem;
  margin-bottom: 1.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  overflow: hidden;
  background: var(--p-content-background);
}

.week-nav {
  display: flex;
  align-items: center;
  padding: 0 0.625rem;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--p-text-muted-color);
}

.week-nav:hover { color: var(--p-text-color); background: var(--p-content-hover-background); }
.week-nav .pi { font-size: 0.75rem; }

.week-days {
  display: flex;
  flex: 1;
}

.day-cell {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.125rem;
  padding: 0.5rem 0.25rem;
  background: none;
  border: none;
  border-left: 1px solid var(--p-content-border-color);
}

.day-cell:first-child { border-left: none; }
.day-cell.today .day-date { color: var(--p-primary-color); font-weight: 700; }

.day-label {
  font-size: 0.625rem;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
  font-weight: 600;
}

.day-date {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.day-hours {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.day-cell.has-hours .day-hours {
  color: var(--p-primary-color);
  font-weight: 600;
}

/* Entries */
.loading {
  text-align: center;
  padding: 3rem;
  color: var(--p-text-muted-color);
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.project-group {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  overflow: hidden;
  background: var(--p-content-background);
}

.project-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem 1rem;
  background: var(--p-content-hover-background);
  border-bottom: 1px solid var(--p-content-border-color);
}

.project-name {
  font-weight: 600;
  font-size: 0.875rem;
}

.project-total {
  font-weight: 700;
  font-size: 0.9375rem;
  color: var(--p-primary-color);
}

.project-entries {
  display: flex;
  flex-direction: column;
}

.entry-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid var(--p-content-border-color);
  cursor: pointer;
}

.entry-row:hover { background: var(--p-content-hover-background); }

.entry-row:last-child { border-bottom: none; }

.entry-day {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  min-width: 6rem;
  flex-shrink: 0;
}

.entry-task {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  padding: 0.0625rem 0.375rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.25rem;
  flex-shrink: 0;
}

.entry-desc {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-right {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: auto;
  flex-shrink: 0;
}

.entry-hours {
  font-weight: 700;
  font-size: 0.875rem;
  color: var(--p-primary-color);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
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
