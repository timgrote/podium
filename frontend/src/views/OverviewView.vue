<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { getActivityLog, type ActivityItem } from '../api/activityLog'
import { getCalendar, type CalendarItem } from '../api/calendar'
import { getOverviewItems, type OverviewItems } from '../api/overview'
import { getEmployees } from '../api/employees'
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
const selectedEmployeeId = ref('')

const rangeDays = computed(() => rangeMode.value === '1d' ? 1 : rangeMode.value === '3d' ? 3 : 7)
const fromDate = computed(() => addDaysStr(todayStr(), -(rangeDays.value - 1)))

// Effective employee: explicit selection > logged-in user
const effectiveEmployeeId = computed(() => selectedEmployeeId.value || user.value?.id || '')

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

// Upcoming deadlines (today onward, not done), filtered by selected employee
const upcomingDeadlines = computed(() => {
  const t = todayStr()
  return deadlines.value
    .filter(it => it.date >= t && it.status !== 'done' && it.status !== 'accepted')
    .filter(it => !effectiveEmployeeId.value || it.assignees.some(a => a.id === effectiveEmployeeId.value))
    .sort((a, b) => a.date.localeCompare(b.date))
})

// Overdue items, filtered by selected employee
const overdueItems = computed(() => {
  const t = todayStr()
  return deadlines.value
    .filter(it => it.date < t && it.status !== 'done' && it.status !== 'accepted')
    .filter(it => !effectiveEmployeeId.value || it.assignees.some(a => a.id === effectiveEmployeeId.value))
    .sort((a, b) => a.date.localeCompare(b.date))
})

// Unfinished work grouped by project, filtered by selected employee.
// Tasks are filtered by assignee; deliverables are project-level so always shown.
const unfinishedByProject = computed(() => {
  const empId = effectiveEmployeeId.value
  const map = new Map<string, { project_id: string; project_name: string; items: (OverviewItems['tasks'][0] | OverviewItems['deliverables'][0])[] }>()
  const all = [...overviewItems.value.tasks, ...overviewItems.value.deliverables] as (OverviewItems['tasks'][0] | OverviewItems['deliverables'][0])[]
  for (const it of all) {
    // Tasks: filter by assignee match; Deliverables: always include (project-level)
    if (empId && it.kind === 'task' && !it.assignees.some(a => a.id === empId)) continue
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

    // Activity log
    const empId = effectiveEmployeeId.value
    if (empId) {
      promises.push(
        getActivityLog({ employee_id: empId, date_from: from, date_to: today })
          .then(data => { activity.value = data })
          .catch(() => { activity.value = [] }),
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

// Reload when range or employee changes
watch(rangeMode, () => { load() })
watch(selectedEmployeeId, () => { load() })

onMounted(load)
</script>

<template>
  <div class="overview-view">
    <!-- Header -->
    <div class="overview-header">
      <h1>Overview</h1>
      <div class="header-controls">
        <select v-model="selectedEmployeeId" class="employee-select" title="Filter by employee">
          <option value="">All employees</option>
          <option v-for="emp in employees" :key="emp.id" :value="emp.id">
            {{ [emp.first_name, emp.last_name].filter(Boolean).join(' ') || emp.email }}
          </option>
        </select>
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
          <h2 class="section-title">Unfinished Work</h2>
          <div v-if="unfinishedByProject.length === 0" class="empty">No active projects with unfinished work in this range.</div>
          <div v-for="proj in unfinishedByProject" :key="proj.project_id" class="project-group">
            <div class="project-head" @click="openProject(proj.project_id)">
              <span class="project-name">{{ proj.project_name }}</span>
              <span class="project-count">{{ proj.items.length }}</span>
            </div>
            <div
              v-for="it in proj.items"
              :key="it.kind + it.id"
              class="work-item"
              :class="kindClass(it.kind)"
              @click="openProject(proj.project_id)"
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
.employee-select {
  padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem;
  background: var(--p-form-field-background); color: var(--p-text-color); font-size: 0.8125rem;
}

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
</style>
