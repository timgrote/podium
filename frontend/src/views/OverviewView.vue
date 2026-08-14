<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { getActivityLog, type ActivityItem } from '../api/activityLog'
import { getCalendar, type CalendarItem } from '../api/calendar'
import { getOverviewItems, type OverviewItems } from '../api/overview'
import { getEmployees } from '../api/employees'
import { bulkUpdateTasks, bulkDeleteTasks } from '../api/tasks'
import type { Employee } from '../types'
import { todayStr, addDaysStr, formatDateShort } from '../utils/dates'

const router = useRouter()
const toast = useToast()
const { user } = useAuth()

type RangeMode = '1d' | '3d' | '7d'
const rangeMode = ref<RangeMode>('3d')
const loading = ref(true)

const activity = ref<ActivityItem[]>([])
const deadlines = ref<CalendarItem[]>([])
const overviewItems = ref<OverviewItems>({ tasks: [], deliverables: [] })
const employees = ref<Employee[]>([])
const selectedEmployeeIds = ref<string[]>([])
const employeeDropdownOpen = ref(false)

const rangeDays = computed(() => rangeMode.value === '1d' ? 1 : rangeMode.value === '3d' ? 3 : 7)
const fromDate = computed(() => addDaysStr(todayStr(), -(rangeDays.value - 1)))

// Selected employee IDs (empty = all). For activity log, we fetch per-employee.
// For deadlines and unfinished work, we filter client-side by assignee match.
const employeeFilterLabel = computed(() => {
  if (selectedEmployeeIds.value.length === 0) return 'All employees'
  if (selectedEmployeeIds.value.length === 1) {
    const emp = employees.value.find(e => e.id === selectedEmployeeIds.value[0])
    return emp ? [emp.first_name, emp.last_name].filter(Boolean).join(' ') || emp.email || 'Unknown' : 'Unknown'
  }
  return `${selectedEmployeeIds.value.length} employees`
})

function toggleEmployee(id: string) {
  if (selectedEmployeeIds.value.includes(id)) {
    selectedEmployeeIds.value = selectedEmployeeIds.value.filter(eid => eid !== id)
  } else {
    selectedEmployeeIds.value = [...selectedEmployeeIds.value, id]
  }
}

function isEmployeeSelected(id: string): boolean {
  return selectedEmployeeIds.value.includes(id)
}

function clearEmployeeFilter() {
  selectedEmployeeIds.value = []
}

// --- Task selection + bulk actions ---
const selectedTaskIds = ref<Set<string>>(new Set())
const bulkAction = ref<'none' | 'reschedule' | 'assign'>('none')
const rescheduleDate = ref('')
const assignDropdownOpen = ref(false)
const bulkAssigneeIds = ref<string[]>([])
const acting = ref(false)

function itemKey(it: { kind: string; id: string }): string {
  return it.kind + it.id
}

function toggleSelectTask(taskId: string) {
  if (selectedTaskIds.value.has(taskId)) {
    selectedTaskIds.value.delete(taskId)
  } else {
    selectedTaskIds.value.add(taskId)
  }
  selectedTaskIds.value = new Set(selectedTaskIds.value)
  if (selectedTaskIds.value.size === 0) bulkAction.value = 'none'
}

function selectAllTasks() {
  for (const t of overviewItems.value.tasks) {
    selectedTaskIds.value.add(t.id)
  }
  selectedTaskIds.value = new Set(selectedTaskIds.value)
}

function clearSelection() {
  selectedTaskIds.value = new Set()
  bulkAction.value = 'none'
  rescheduleDate.value = ''
  bulkAssigneeIds.value = []
}

function toggleBulkAssignee(id: string) {
  if (bulkAssigneeIds.value.includes(id)) {
    bulkAssigneeIds.value = bulkAssigneeIds.value.filter(eid => eid !== id)
  } else {
    bulkAssigneeIds.value = [...bulkAssigneeIds.value, id]
  }
}

function isBulkAssigneeSelected(id: string): boolean {
  return bulkAssigneeIds.value.includes(id)
}

const selectedCount = computed(() => selectedTaskIds.value.size)

async function bulkMarkDone() {
  if (selectedTaskIds.value.size === 0) return
  acting.value = true
  try {
    const ids = [...selectedTaskIds.value]
    await bulkUpdateTasks(ids, { status: 'done' })
    // Update local state
    for (const t of overviewItems.value.tasks) {
      if (selectedTaskIds.value.has(t.id)) t.status = 'done'
    }
    toast.success(`${ids.length} task${ids.length === 1 ? '' : 's'} marked done`)
    clearSelection()
  } catch (e) {
    toast.error(`Failed: ${e}`)
  } finally {
    acting.value = false
  }
}

async function bulkReschedule() {
  if (selectedTaskIds.value.size === 0 || !rescheduleDate.value) return
  acting.value = true
  try {
    const ids = [...selectedTaskIds.value]
    await bulkUpdateTasks(ids, { due_date: rescheduleDate.value })
    for (const t of overviewItems.value.tasks) {
      if (selectedTaskIds.value.has(t.id)) t.due_date = rescheduleDate.value
    }
    toast.success(`${ids.length} task${ids.length === 1 ? '' : 's'} rescheduled to ${rescheduleDate.value}`)
    clearSelection()
  } catch (e) {
    toast.error(`Failed: ${e}`)
  } finally {
    acting.value = false
  }
}

async function bulkAssign() {
  if (selectedTaskIds.value.size === 0 || bulkAssigneeIds.value.length === 0) return
  acting.value = true
  try {
    const ids = [...selectedTaskIds.value]
    await bulkUpdateTasks(ids, { assignee_ids: bulkAssigneeIds.value })
    toast.success(`${ids.length} task${ids.length === 1 ? '' : 's'} assigned`)
    clearSelection()
  } catch (e) {
    toast.error(`Failed: ${e}`)
  } finally {
    acting.value = false
  }
}

async function bulkDelete() {
  if (selectedTaskIds.value.size === 0) return
  acting.value = true
  try {
    const ids = [...selectedTaskIds.value]
    await bulkDeleteTasks(ids)
    overviewItems.value.tasks = overviewItems.value.tasks.filter(t => !selectedTaskIds.value.has(t.id))
    toast.success(`${ids.length} task${ids.length === 1 ? '' : 's'} deleted`)
    clearSelection()
  } catch (e) {
    toast.error(`Failed: ${e}`)
  } finally {
    acting.value = false
  }
}

// Unique projects from activity feed — used to fetch unfinished work
const activeProjectIds = computed(() => {
  const ids = new Set<string>()
  for (const a of activity.value) {
    if (a.project_id) ids.add(a.project_id)
  }
  return Array.from(ids)
})

// Group activity by day
const activityByDay = computed(() => {
  const map = new Map<string, ActivityItem[]>()
  for (const a of activity.value) {
    const day = a.timestamp.slice(0, 10)
    if (!map.has(day)) map.set(day, [])
    map.get(day)!.push(a)
  }
  return Array.from(map.entries()).sort((a, b) => b[0].localeCompare(a[0]))
})

// Upcoming deadlines (today onward, not done), filtered by selected employees
const upcomingDeadlines = computed(() => {
  const t = todayStr()
  return deadlines.value
    .filter(it => it.date >= t && it.status !== 'done' && it.status !== 'accepted')
    .filter(it => selectedEmployeeIds.value.length === 0 || it.assignees.some(a => selectedEmployeeIds.value.includes(a.id)))
    .sort((a, b) => a.date.localeCompare(b.date))
})

// Overdue items, filtered by selected employees
const overdueItems = computed(() => {
  const t = todayStr()
  return deadlines.value
    .filter(it => it.date < t && it.status !== 'done' && it.status !== 'accepted')
    .filter(it => selectedEmployeeIds.value.length === 0 || it.assignees.some(a => selectedEmployeeIds.value.includes(a.id)))
    .sort((a, b) => a.date.localeCompare(b.date))
})

// Unfinished work grouped by project, filtered by selected employees.
// Tasks are filtered by assignee; deliverables are project-level so always shown.
const unfinishedByProject = computed(() => {
  const sel = selectedEmployeeIds.value
  const map = new Map<string, { project_id: string; project_name: string; items: (OverviewItems['tasks'][0] | OverviewItems['deliverables'][0])[] }>()
  const all = [...overviewItems.value.tasks, ...overviewItems.value.deliverables] as (OverviewItems['tasks'][0] | OverviewItems['deliverables'][0])[]
  for (const it of all) {
    // Tasks: filter by assignee match; Deliverables: always include (project-level)
    if (sel.length > 0 && it.kind === 'task' && !it.assignees.some(a => sel.includes(a.id))) continue
    if (!map.has(it.project_id)) {
      map.set(it.project_id, { project_id: it.project_id, project_name: it.project_name, items: [] })
    }
    map.get(it.project_id)!.items.push(it)
  }
  return Array.from(map.values()).sort((a, b) => a.project_name.localeCompare(b.project_name))
})

function priorityLabel(p: number | null): string {
  if (p === 1) return 'Low'
  if (p === 2) return 'Medium'
  if (p === 3) return 'High'
  return ''
}

function priorityClass(p: number | null): string {
  if (p === 1) return 'priority-low'
  if (p === 2) return 'priority-medium'
  if (p === 3) return 'priority-high'
  return ''
}

function statusLabel(status: string): string {
  return status.replace(/_/g, ' ')
}

function kindLabel(kind: string): string {
  return kind === 'task' ? 'Task' : 'Deliverable'
}

function kindClass(kind: string): string {
  return kind === 'task' ? 'kind-task' : 'kind-deliverable'
}

function formatDuration(minutes: number | null): string {
  if (!minutes) return ''
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h && m) return `${h}h ${m}m`
  if (h) return `${h}h`
  return `${m}m`
}

function openProject(projectId: string) {
  router.push(`/projects/${projectId}`)
}

function rangeLabel(r: RangeMode): string {
  return r === '1d' ? 'Today' : r === '3d' ? '3 Days' : '7 Days'
}

async function load() {
  loading.value = true
  try {
    // Fetch employee list on first load
    if (employees.value.length === 0) {
      try { employees.value = await getEmployees() } catch { /* ignore */ }
    }

    const today = todayStr()
    const from = fromDate.value

    // Fetch activity log, upcoming deadlines, and overview items in parallel
    const promises: Promise<unknown>[] = []

    // Activity log — fetch for each selected employee (or logged-in user if none selected)
    const empIds = selectedEmployeeIds.value.length > 0
      ? selectedEmployeeIds.value
      : (user.value?.id ? [user.value.id] : [])
    if (empIds.length > 0) {
      // Fetch each employee's activity in parallel, merge results
      promises.push(
        Promise.all(
          empIds.map(eid =>
            getActivityLog({ employee_id: eid, date_from: from, date_to: today })
              .catch(() => [] as ActivityItem[]),
          ),
        ).then(results => {
          activity.value = results.flat().sort((a, b) =>
            (b.timestamp || '').localeCompare(a.timestamp || ''),
          )
        }),
      )
    } else {
      promises.push(Promise.resolve())
    }

    // Calendar items (fetch a wide range to catch overdue + upcoming)
    promises.push(
      getCalendar({ from: addDaysStr(today, -30), to: addDaysStr(today, 60) })
        .then(data => { deadlines.value = data })
        .catch(() => { deadlines.value = [] }),
    )

    await Promise.all(promises)

    // Fetch unfinished items for projects in the activity feed
    if (activeProjectIds.value.length > 0) {
      try {
        overviewItems.value = await getOverviewItems(activeProjectIds.value)
      } catch {
        overviewItems.value = { tasks: [], deliverables: [] }
      }
    } else {
      overviewItems.value = { tasks: [], deliverables: [] }
    }
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

// Reload when range or employee filter changes
watch(rangeMode, () => { load() })
watch(selectedEmployeeIds, () => { load() })

onMounted(load)
</script>

<template>
  <div class="overview-view">
    <!-- Header -->
    <div class="overview-header">
      <h1>Overview</h1>
      <div class="header-controls">
        <div class="emp-dropdown">
          <button class="emp-dropdown-btn" @click="employeeDropdownOpen = !employeeDropdownOpen">
            <i class="pi pi-users" />
            <span>{{ employeeFilterLabel }}</span>
            <i class="pi pi-chevron-down" :class="{ rotated: employeeDropdownOpen }" />
          </button>
          <div v-if="employeeDropdownOpen" class="emp-dropdown-panel">
            <div class="emp-dropdown-actions">
              <button class="emp-clear" @click="clearEmployeeFilter">Clear</button>
            </div>
            <label
              v-for="emp in employees"
              :key="emp.id"
              class="emp-option"
            >
              <input
                type="checkbox"
                :checked="isEmployeeSelected(emp.id)"
                @change="toggleEmployee(emp.id)"
              >
              <span>{{ [emp.first_name, emp.last_name].filter(Boolean).join(' ') || emp.email }}</span>
            </label>
          </div>
        </div>
        <div class="range-switcher">
          <button
            v-for="r in (['1d','3d','7d'] as RangeMode[])"
            :key="r"
            class="btn range-btn"
            :class="{ active: rangeMode === r }"
            @click="rangeMode = r"
          >{{ rangeLabel(r) }}</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="empty">Loading overview…</div>

    <template v-else>
      <div class="overview-grid">
        <!-- LEFT: Recent Activity -->
        <section class="overview-section">
          <h2 class="section-title">Recent Activity</h2>
          <div v-if="activityByDay.length === 0" class="empty">No activity in the selected range.</div>
          <div v-for="[day, items] in activityByDay" :key="day" class="activity-day">
            <div class="day-header">
              <span class="day-date">{{ formatDateShort(day) }}</span>
              <span v-if="day === todayStr()" class="today-chip">Today</span>
            </div>
            <div v-for="a in items" :key="a.id" class="activity-item" @click="a.project_id && openProject(a.project_id)">
              <div class="activity-top">
                <span class="activity-desc">{{ a.description }}</span>
                <span v-if="a.duration_minutes" class="activity-duration">{{ formatDuration(a.duration_minutes) }}</span>
              </div>
              <div class="activity-meta">
                <span v-if="a.project_name" class="activity-project">{{ a.project_name }}</span>
                <span v-if="a.source" class="activity-source">{{ a.source }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- MIDDLE: Upcoming Deadlines + Overdue -->
        <section class="overview-section">
          <h2 class="section-title">Upcoming Deadlines</h2>
          <div v-if="overdueItems.length > 0" class="overdue-group">
            <div class="subhead overdue-subhead">⚠ Overdue ({{ overdueItems.length }})</div>
            <div
              v-for="it in overdueItems.slice(0, 10)"
              :key="it.kind + it.id"
              class="deadline-item overdue"
              @click="openProject(it.project_id)"
            >
              <span class="deadline-date">{{ formatDateShort(it.date) }}</span>
              <span class="deadline-kind" :class="kindClass(it.kind)">{{ kindLabel(it.kind) }}</span>
              <span class="deadline-title">{{ it.title }}</span>
              <span v-if="it.priority" class="pill" :class="priorityClass(it.priority)">{{ priorityLabel(it.priority) }}</span>
              <span class="deadline-project">{{ it.project_name }}</span>
            </div>
          </div>
          <div v-if="upcomingDeadlines.length === 0 && overdueItems.length === 0" class="empty">No upcoming deadlines.</div>
          <div
            v-for="it in upcomingDeadlines.slice(0, 15)"
            :key="it.kind + it.id"
            class="deadline-item"
            @click="openProject(it.project_id)"
          >
            <span class="deadline-date">{{ formatDateShort(it.date) }}</span>
            <span class="deadline-kind" :class="kindClass(it.kind)">{{ kindLabel(it.kind) }}</span>
            <span class="deadline-title">{{ it.title }}</span>
            <span v-if="it.priority" class="pill" :class="priorityClass(it.priority)">{{ priorityLabel(it.priority) }}</span>
            <span class="deadline-project">{{ it.project_name }}</span>
          </div>
        </section>

        <!-- RIGHT: Unfinished Work on Active Projects -->
        <section class="overview-section">
          <div class="section-header">
            <h2 class="section-title">Unfinished Work</h2>
            <div v-if="overviewItems.tasks.length > 0" class="select-controls">
              <button v-if="selectedCount === 0" class="link-btn" @click="selectAllTasks">Select all tasks</button>
              <button v-else class="link-btn" @click="clearSelection">Clear</button>
            </div>
          </div>

          <!-- Bulk action bar -->
          <div v-if="selectedCount > 0" class="bulk-bar">
            <span class="bulk-count">{{ selectedCount }} selected</span>
            <button class="bulk-btn" :disabled="acting" @click="bulkMarkDone">
              <i class="pi pi-check" /> Mark Done
            </button>
            <button class="bulk-btn" :disabled="acting" @click="bulkAction = bulkAction === 'reschedule' ? 'none' : 'reschedule'">
              <i class="pi pi-calendar" /> Reschedule
            </button>
            <button class="bulk-btn" :disabled="acting" @click="bulkAction = bulkAction === 'assign' ? 'none' : 'assign'; assignDropdownOpen = false">
              <i class="pi pi-users" /> Assign
            </button>
            <button class="bulk-btn bulk-danger" :disabled="acting" @click="bulkDelete">
              <i class="pi pi-trash" /> Delete
            </button>

            <!-- Reschedule inline input -->
            <div v-if="bulkAction === 'reschedule'" class="bulk-inline">
              <input type="date" v-model="rescheduleDate" class="bulk-date-input">
              <button class="bulk-btn bulk-primary" :disabled="acting || !rescheduleDate" @click="bulkReschedule">Apply</button>
              <button class="bulk-btn" @click="bulkAction = 'none'">Cancel</button>
            </div>

            <!-- Assign inline dropdown -->
            <div v-if="bulkAction === 'assign'" class="bulk-inline">
              <div class="emp-dropdown">
                <button class="emp-dropdown-btn" @click="assignDropdownOpen = !assignDropdownOpen">
                  <i class="pi pi-users" />
                  <span>{{ bulkAssigneeIds.length === 0 ? 'Select assignees' : `${bulkAssigneeIds.length} selected` }}</span>
                  <i class="pi pi-chevron-down" :class="{ rotated: assignDropdownOpen }" />
                </button>
                <div v-if="assignDropdownOpen" class="emp-dropdown-panel">
                  <label v-for="emp in employees" :key="emp.id" class="emp-option">
                    <input type="checkbox" :checked="isBulkAssigneeSelected(emp.id)" @change="toggleBulkAssignee(emp.id)">
                    <span>{{ [emp.first_name, emp.last_name].filter(Boolean).join(' ') || emp.email }}</span>
                  </label>
                </div>
              </div>
              <button class="bulk-btn bulk-primary" :disabled="acting || bulkAssigneeIds.length === 0" @click="bulkAssign">Apply</button>
              <button class="bulk-btn" @click="bulkAction = 'none'">Cancel</button>
            </div>
          </div>

          <div v-if="unfinishedByProject.length === 0" class="empty">No active projects with unfinished work in this range.</div>
          <div v-for="proj in unfinishedByProject" :key="proj.project_id" class="project-group">
            <div class="project-head" @click="openProject(proj.project_id)">
              <span class="project-name">{{ proj.project_name }}</span>
              <span class="project-count">{{ proj.items.length }}</span>
            </div>
            <div
              v-for="it in proj.items"
              :key="itemKey(it)"
              class="work-item"
              :class="[kindClass(it.kind), { selected: it.kind === 'task' && selectedTaskIds.has(it.id) }]"
              @click="openProject(proj.project_id)"
            >
              <input
                v-if="it.kind === 'task'"
                type="checkbox"
                class="task-checkbox"
                :checked="selectedTaskIds.has(it.id)"
                @click.stop="toggleSelectTask(it.id)"
              >
              <span class="work-kind">{{ kindLabel(it.kind) }}</span>
              <span class="work-title">{{ it.title }}</span>
              <span v-if="'progress_percent' in it" class="work-progress">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: it.progress_percent + '%' }"></div>
                </div>
                <span class="progress-text">{{ Math.round(it.progress_percent) }}%</span>
              </span>
              <span v-if="'due_date' in it && it.due_date" class="work-date">{{ formatDateShort(it.due_date) }}</span>
              <span v-if="'deadline' in it && it.deadline" class="work-date">{{ formatDateShort(it.deadline) }}</span>
              <span class="work-status" :class="'status-' + it.status">{{ statusLabel(it.status) }}</span>
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.overview-view { display: flex; flex-direction: column; gap: 1rem; }
.overview-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.overview-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
.header-controls { display: flex; align-items: center; gap: 0.75rem; }
.emp-dropdown { position: relative; }
.emp-dropdown-btn {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.375rem 0.625rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem;
  background: var(--p-form-field-background); color: var(--p-text-color); font-size: 0.8125rem; cursor: pointer;
}
.emp-dropdown-btn:hover { border-color: var(--p-primary-color); }
.emp-dropdown-btn .pi.pi-chevron-down { font-size: 0.625rem; transition: transform 0.15s; }
.emp-dropdown-btn .pi.pi-chevron-down.rotated { transform: rotate(180deg); }
.emp-dropdown-panel {
  position: absolute; top: calc(100% + 0.25rem); left: 0; z-index: 100;
  min-width: 12rem; max-height: 16rem; overflow-y: auto;
  border: 1px solid var(--p-content-border-color); border-radius: 0.375rem;
  background: var(--p-content-background); box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  padding: 0.25rem;
}
.emp-dropdown-actions { display: flex; justify-content: flex-end; padding: 0.25rem 0.5rem; border-bottom: 1px solid var(--p-content-border-color); margin-bottom: 0.25rem; }
.emp-clear { font-size: 0.6875rem; color: var(--p-primary-color); background: none; border: none; cursor: pointer; }
.emp-clear:hover { text-decoration: underline; }
.emp-option {
  display: flex; align-items: center; gap: 0.5rem; padding: 0.3125rem 0.5rem;
  font-size: 0.8125rem; cursor: pointer; border-radius: 0.25rem;
}
.emp-option:hover { background: var(--p-content-hover-background); }
.emp-option input { width: 0.875rem; height: 0.875rem; }

.range-switcher { display: flex; gap: 0.25rem; }
.btn {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.375rem 0.75rem; border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem; background: var(--p-form-field-background); color: var(--p-text-color);
  font-size: 0.8125rem; cursor: pointer;
}
.btn:hover { border-color: var(--p-primary-color); }
.range-btn.active { background: var(--p-primary-color); border-color: var(--p-primary-color); color: #fff; }

.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1.5rem;
  align-items: start;
}
@media (max-width: 1100px) { .overview-grid { grid-template-columns: 1fr; } }

.overview-section {
  display: flex; flex-direction: column; gap: 0.5rem;
}
.section-title {
  font-size: 0.875rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--p-text-muted-color); margin: 0 0 0.25rem 0;
  padding-bottom: 0.5rem; border-bottom: 1px solid var(--p-content-border-color);
}
.empty { font-size: 0.8125rem; color: var(--p-text-muted-color); font-style: italic; padding: 1rem 0; }

/* ACTIVITY */
.activity-day { display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.75rem; }
.day-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
.day-date { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--p-text-color); }
.today-chip { font-size: 0.625rem; font-weight: 700; background: var(--p-primary-color); color: #fff; padding: 0.0625rem 0.375rem; border-radius: 999px; }
.activity-item { padding: 0.4rem 0.5rem; border-radius: 0.3125rem; cursor: pointer; border-left: 3px solid var(--p-surface-300); }
.activity-item:hover { background: var(--p-content-hover-background); }
.activity-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; }
.activity-desc { font-size: 0.8125rem; font-weight: 500; flex: 1; min-width: 0; }
.activity-duration { font-size: 0.75rem; font-weight: 600; color: var(--p-primary-color); flex-shrink: 0; }
.activity-meta { display: flex; gap: 0.5rem; margin-top: 0.125rem; }
.activity-project { font-size: 0.6875rem; color: var(--p-text-muted-color); }
.activity-source { font-size: 0.625rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--p-text-muted-color); padding: 0.0625rem 0.3125rem; border-radius: 0.25rem; background: var(--p-surface-200); }

/* DEADLINES */
.overdue-group { margin-bottom: 0.75rem; }
.subhead { font-size: 0.6875rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.25rem; }
.overdue-subhead { color: var(--p-red-600); }
.deadline-item {
  display: flex; align-items: center; gap: 0.5rem; padding: 0.35rem 0.5rem; font-size: 0.8125rem;
  border-radius: 0.3125rem; cursor: pointer; border-left: 3px solid var(--p-surface-300);
}
.deadline-item:hover { background: var(--p-content-hover-background); }
.deadline-item.overdue { border-left-color: var(--p-red-500); }
.deadline-date { font-size: 0.6875rem; font-weight: 600; color: var(--p-text-muted-color); width: 3.5rem; flex-shrink: 0; }
.deadline-item.overdue .deadline-date { color: var(--p-red-600); }
.deadline-kind { font-size: 0.5625rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; width: 4rem; flex-shrink: 0; }
.kind-task .deadline-kind, .kind-task.work-kind { color: var(--p-primary-color); }
.kind-deliverable .deadline-kind, .kind-deliverable.work-kind { color: var(--p-purple-400); }
.deadline-title { flex: 1; min-width: 0; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.deadline-project { font-size: 0.6875rem; color: var(--p-text-muted-color); flex-shrink: 0; max-width: 8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* PILLS */
.pill { font-size: 0.625rem; font-weight: 600; padding: 0.0625rem 0.3125rem; border-radius: 999px; flex-shrink: 0; }
.priority-high { background: var(--p-red-100); color: var(--p-red-700); }
.priority-medium { background: var(--p-amber-100); color: var(--p-amber-700); }
.priority-low { background: var(--p-green-100); color: var(--p-green-600); }

/* UNFINISHED WORK */
.project-group { margin-bottom: 0.75rem; }
.project-head { display: flex; align-items: center; justify-content: space-between; cursor: pointer; padding: 0.25rem 0; }
.project-head:hover { color: var(--p-primary-color); }
.project-name { font-size: 0.75rem; font-weight: 600; }
.project-count { font-size: 0.625rem; font-weight: 700; background: var(--p-surface-200); color: var(--p-text-muted-color); padding: 0.0625rem 0.375rem; border-radius: 999px; }
.work-item {
  display: flex; align-items: center; gap: 0.5rem; padding: 0.3rem 0.5rem; font-size: 0.8125rem;
  border-radius: 0.3125rem; cursor: pointer; border-left: 3px solid var(--p-surface-300);
}
.work-item:hover { background: var(--p-content-hover-background); }
.work-item.kind-task { border-left-color: var(--p-primary-color); }
.work-item.kind-deliverable { border-left-color: var(--p-purple-400); }
.work-kind { font-size: 0.5625rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; width: 4rem; flex-shrink: 0; }
.work-title { flex: 1; min-width: 0; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.work-progress { display: flex; align-items: center; gap: 0.25rem; flex-shrink: 0; }
.progress-bar { width: 3rem; height: 0.375rem; background: var(--p-surface-200); border-radius: 999px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--p-primary-color); border-radius: 999px; transition: width 0.2s; }
.progress-text { font-size: 0.625rem; color: var(--p-text-muted-color); width: 2rem; text-align: right; }
.work-date { font-size: 0.6875rem; color: var(--p-text-muted-color); flex-shrink: 0; }
.work-status { font-size: 0.625rem; text-transform: capitalize; padding: 0.0625rem 0.3125rem; border-radius: 0.25rem; background: var(--p-surface-200); color: var(--p-text-muted-color); flex-shrink: 0; }
.work-status.status-done, .work-status.status-accepted { background: var(--p-green-100); color: var(--p-green-700); }
.work-status.status-sent { background: var(--p-amber-100); color: var(--p-amber-700); }
.work-status.status-in_progress { background: var(--p-blue-100); color: var(--p-blue-700); }
.work-status.status-not_started { background: var(--p-surface-200); color: var(--p-text-muted-color); }

/* BULK ACTIONS */
.section-header { display: flex; align-items: center; justify-content: space-between; }
.select-controls { display: flex; gap: 0.5rem; }
.link-btn { font-size: 0.6875rem; color: var(--p-primary-color); background: none; border: none; cursor: pointer; }
.link-btn:hover { text-decoration: underline; }

.bulk-bar {
  display: flex; align-items: center; flex-wrap: wrap; gap: 0.375rem;
  padding: 0.5rem; border-radius: 0.375rem; background: var(--p-surface-100);
  border: 1px solid var(--p-content-border-color); margin-bottom: 0.5rem;
}
.bulk-count { font-size: 0.75rem; font-weight: 600; margin-right: 0.5rem; }
.bulk-btn {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.25rem 0.5rem; border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.25rem; background: var(--p-form-field-background); color: var(--p-text-color);
  font-size: 0.75rem; cursor: pointer;
}
.bulk-btn:hover:not(:disabled) { border-color: var(--p-primary-color); }
.bulk-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.bulk-primary { background: var(--p-primary-color); border-color: var(--p-primary-color); color: #fff; }
.bulk-danger { color: var(--p-red-600); border-color: var(--p-red-300); }
.bulk-danger:hover:not(:disabled) { background: var(--p-red-50); border-color: var(--p-red-500); }
.bulk-inline { display: flex; align-items: center; gap: 0.375rem; width: 100%; margin-top: 0.25rem; }
.bulk-date-input {
  padding: 0.25rem 0.375rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.25rem;
  background: var(--p-form-field-background); color: var(--p-text-color); font-size: 0.75rem;
}

.task-checkbox { flex-shrink: 0; width: 0.875rem; height: 0.875rem; cursor: pointer; }
.work-item.selected { background: color-mix(in srgb, var(--p-primary-color) 12%, transparent); }
</style>
