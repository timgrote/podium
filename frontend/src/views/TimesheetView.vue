<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import type { Employee } from '../types'
import type { TimeEntry } from '../api/timeEntries'
import { getTimeEntries, deleteTimeEntry, updateTimeEntry } from '../api/timeEntries'
import { getEmployees } from '../api/employees'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { todayStr, formatDateShort } from '../utils/dates'
import LogTimeModal from '../components/modals/LogTimeModal.vue'

const { user } = useAuth()
const toast = useToast()
const entries = ref<TimeEntry[]>([])
const employees = ref<Employee[]>([])
const loading = ref(true)
const showLogModal = ref(false)
const selectedEmployeeId = ref('')
const editingId = ref<string | null>(null)
const editHours = ref('')

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

const selectedDay = ref('')

// Initialize selectedDay to today
onMounted(() => {
  selectedDay.value = todayStr()
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

const dayEntries = computed(() => {
  if (!selectedDay.value) return []
  return entries.value.filter(e => e.date === selectedDay.value)
})

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

function startEdit(entry: TimeEntry) {
  editingId.value = entry.id
  editHours.value = String(entry.hours)
}

async function saveEdit(entry: TimeEntry) {
  const h = parseFloat(editHours.value)
  if (!h || h <= 0) return
  try {
    await updateTimeEntry(entry.id, { hours: h })
    editingId.value = null
    await loadEntries()
  } catch (e) {
    toast.error(String(e))
  }
}

function cancelEdit() {
  editingId.value = null
}

watch([effectiveEmployeeId, weekOffset], loadEntries)
watch(weekOffset, () => {
  // Keep selectedDay within the new week if it's out of range
  const range = weekDateRange.value
  if (selectedDay.value < range.from || selectedDay.value > range.to) {
    selectedDay.value = range.from
  }
})

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
        <button class="btn-log-time" @click="showLogModal = true">
          <i class="pi pi-plus" /> Log Time
        </button>
      </div>
    </div>

    <!-- Week summary bar -->
    <div class="week-bar">
      <button class="week-nav" @click="weekOffset--">
        <i class="pi pi-chevron-left" />
      </button>
      <div class="week-days">
        <button
          v-for="day in weekDays"
          :key="day.dateStr"
          class="day-cell"
          :class="{ today: day.isToday, selected: selectedDay === day.dateStr, 'has-hours': (dailyTotals[day.dateStr] || 0) > 0 }"
          @click="selectedDay = day.dateStr"
        >
          <span class="day-label">{{ day.label }}</span>
          <span class="day-date">{{ day.date.getDate() }}</span>
          <span class="day-hours">{{ (dailyTotals[day.dateStr] || 0).toFixed(1) }}h</span>
        </button>
      </div>
      <button class="week-nav" @click="weekOffset++">
        <i class="pi pi-chevron-right" />
      </button>
      <div class="week-total">
        <span class="week-total-label">Week</span>
        <span class="week-total-hours">{{ weekTotal.toFixed(1) }}h</span>
      </div>
    </div>

    <!-- Day entries -->
    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="dayEntries.length === 0" class="empty-state">
      <p>No time logged for {{ formatDateShort(selectedDay) }}</p>
    </div>

    <div v-else class="entry-list">
      <div v-for="entry in dayEntries" :key="entry.id" class="entry-card">
        <div class="entry-main">
          <span class="entry-project">{{ entry.project_name || entry.project_id }}</span>
          <span v-if="entry.contract_task_name" class="entry-task">{{ entry.contract_task_name }}</span>
        </div>
        <div v-if="entry.description" class="entry-desc">{{ entry.description }}</div>
        <div class="entry-footer">
          <div v-if="editingId === entry.id" class="edit-hours">
            <input
              v-model="editHours"
              type="number"
              step="0.25"
              min="0.25"
              class="edit-hours-input"
              @keydown.enter="saveEdit(entry)"
              @keydown.escape="cancelEdit"
            />
            <button class="btn-icon" @click="saveEdit(entry)"><i class="pi pi-check" /></button>
            <button class="btn-icon" @click="cancelEdit"><i class="pi pi-times" /></button>
          </div>
          <span v-else class="entry-hours" @click="startEdit(entry)">{{ Number(entry.hours).toFixed(1) }}h</span>
          <button v-if="editingId !== entry.id" class="btn-icon btn-delete" @click="handleDelete(entry.id)">
            <i class="pi pi-trash" />
          </button>
        </div>
      </div>
    </div>

    <LogTimeModal
      v-model:visible="showLogModal"
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
  cursor: pointer;
  transition: background 0.15s;
}

.day-cell:first-child { border-left: none; }
.day-cell:hover { background: var(--p-content-hover-background); }
.day-cell.selected { background: var(--p-highlight-background); }
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

.week-total {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  border-left: 1px solid var(--p-content-border-color);
  min-width: 60px;
}

.week-total-label {
  font-size: 0.625rem;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
  font-weight: 600;
}

.week-total-hours {
  font-size: 1rem;
  font-weight: 700;
  color: var(--p-text-color);
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

.entry-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.entry-card {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--p-content-background);
}

.entry-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.entry-project {
  font-weight: 600;
  font-size: 0.875rem;
}

.entry-task {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  padding: 0.0625rem 0.375rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.25rem;
}

.entry-desc {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  margin-bottom: 0.375rem;
}

.entry-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.entry-hours {
  font-weight: 700;
  font-size: 0.9375rem;
  color: var(--p-primary-color);
  cursor: pointer;
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
}

.entry-hours:hover { background: var(--p-content-hover-background); }

.edit-hours {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.edit-hours-input {
  width: 60px;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--p-primary-color);
  border-radius: 0.25rem;
  font-size: 0.875rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
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
