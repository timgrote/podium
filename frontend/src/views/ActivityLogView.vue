<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import type { Employee, ProjectSummary } from '../types'
import type { ActivityItem } from '../api/activityLog'
import { getActivityLog, createOverride } from '../api/activityLog'
import { getProjects } from '../api/projects'
import { getEmployees } from '../api/employees'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { todayStr } from '../utils/dates'
import ProjectAssignPopover from '../components/activity/ProjectAssignPopover.vue'

const { user } = useAuth()
const toast = useToast()

const items = ref<ActivityItem[]>([])
const employees = ref<Employee[]>([])
const projects = ref<ProjectSummary[]>([])
const loading = ref(true)
const selectedEmployeeId = ref('')
const assigningItemId = ref<string | null>(null)
const expandedGroups = ref<Set<string>>(new Set())
const collapsedDays = ref<Set<string>>(new Set())

function toggleGroup(key: string) {
  if (expandedGroups.value.has(key)) {
    expandedGroups.value.delete(key)
  } else {
    expandedGroups.value.add(key)
  }
  expandedGroups.value = new Set(expandedGroups.value)
}

function toggleDay(dayKey: string) {
  if (collapsedDays.value.has(dayKey)) {
    collapsedDays.value.delete(dayKey)
  } else {
    collapsedDays.value.add(dayKey)
  }
  collapsedDays.value = new Set(collapsedDays.value)
}

function isDayExpanded(dayKey: string): boolean {
  return !collapsedDays.value.has(dayKey)
}

function isExpanded(dayKey: string, projectId: string | null): boolean {
  const key = `${dayKey}:${projectId || '__unassigned__'}`
  if (!projectId) return true
  return expandedGroups.value.has(key)
}

function dayTotalMinutes(projectGroups: { total_minutes: number }[]): number {
  return projectGroups.reduce((sum, pg) => sum + pg.total_minutes, 0)
}

// Week navigation (same pattern as Timesheet)
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

const effectiveEmployeeId = computed(() => {
  return selectedEmployeeId.value || user.value?.id || ''
})

// Consolidated file entry: one per unique file, with summed time
interface FileEntry {
  description: string
  source_path: string
  total_minutes: number
  total_commands: number
  sessions: number
  // Keep one representative item for assign functionality
  representative: ActivityItem
}

interface ProjectGroup {
  project_id: string | null
  project_name: string | null
  mapping_source: string | null
  files: FileEntry[]
  total_minutes: number
}

function consolidateByProject(dayItems: ActivityItem[]): ProjectGroup[] {
  const projectMap = new Map<string, ProjectGroup>()

  for (const item of dayItems) {
    const key = item.project_id || '__unassigned__'
    let group = projectMap.get(key)
    if (!group) {
      group = {
        project_id: item.project_id,
        project_name: item.project_name,
        mapping_source: item.mapping_source,
        files: [],
        total_minutes: 0,
      }
      projectMap.set(key, group)
    }

    // Find existing file entry by source_path (or description if no path)
    const fileKey = item.source_path || item.description
    let file = group.files.find((f) => (f.source_path || f.description) === fileKey)
    if (!file) {
      file = {
        description: item.description,
        source_path: item.source_path || '',
        total_minutes: 0,
        total_commands: 0,
        sessions: 0,
        representative: item,
      }
      group.files.push(file)
    }
    file.total_minutes += item.duration_minutes || 0
    file.sessions++
    // Parse command count from detail string
    const cmdMatch = item.detail?.match(/(\d+) cmds/)
    if (cmdMatch) file.total_commands += parseInt(cmdMatch[1])
    group.total_minutes += item.duration_minutes || 0
  }

  // Sort: assigned projects first, unassigned last. Within each, sort by total time desc
  const groups = [...projectMap.values()]
  groups.sort((a, b) => {
    if (a.project_id && !b.project_id) return -1
    if (!a.project_id && b.project_id) return 1
    return b.total_minutes - a.total_minutes
  })
  return groups
}

// Today's consolidated groups
const todayGroups = computed(() => {
  const today = todayStr()
  const dayItems = items.value.filter((i) => i.timestamp.startsWith(today))
  return consolidateByProject(dayItems)
})

// Week items grouped by day, then by project
const dailyCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const day of weekDays.value) {
    counts[day.dateStr] = 0
  }
  for (const item of items.value) {
    const dateStr = item.timestamp.substring(0, 10)
    if (dateStr in counts) {
      counts[dateStr] = (counts[dateStr] ?? 0) + 1
    }
  }
  return counts
})

interface DayGroup {
  dateStr: string
  label: string
  projectGroups: ProjectGroup[]
}

const weekGroups = computed<DayGroup[]>(() => {
  const groups: DayGroup[] = []
  // Reverse order: most recent day first
  const daysDesc = [...weekDays.value].reverse()
  for (const day of daysDesc) {
    const dayItems = items.value.filter((i) => i.timestamp.startsWith(day.dateStr))
    if (dayItems.length > 0) {
      groups.push({
        dateStr: day.dateStr,
        label: day.date.toLocaleDateString('en-US', {
          weekday: 'long',
          month: 'short',
          day: 'numeric',
        }),
        projectGroups: consolidateByProject(dayItems),
      })
    }
  }
  return groups
})

async function loadData() {
  if (!effectiveEmployeeId.value) return
  loading.value = true
  try {
    items.value = await getActivityLog({
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

async function loadProjects() {
  try {
    projects.value = await getProjects()
  } catch (e) {
    toast.error(String(e))
  }
}

async function handleAssign(
  item: ActivityItem,
  data: { project_id: string; remember: boolean; pattern: string },
) {
  try {
    await createOverride({
      source: item.source,
      source_key: item.id,
      employee_id: effectiveEmployeeId.value,
      project_id: data.project_id,
      remember: data.remember,
      pattern: data.pattern,
    })
    assigningItemId.value = null
    toast.success('Project assigned')
    await loadData()
  } catch (e) {
    toast.error(String(e))
  }
}

function formatTime(timestamp: string): string {
  const d = new Date(timestamp)
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

function formatDuration(minutes: number): string {
  const m = Math.round(minutes)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  const rem = m % 60
  return rem > 0 ? `${h}h ${rem}m` : `${h}h`
}

watch([effectiveEmployeeId, weekOffset], loadData)

onMounted(async () => {
  await Promise.all([loadEmployees(), loadProjects()])
  await loadData()
})
</script>

<template>
  <div class="activity-log">
    <div class="page-header">
      <h1>Activity Log</h1>
      <div class="header-actions">
        <select v-model="selectedEmployeeId" class="employee-select">
          <option value="">
            {{ user ? `${user.first_name} ${user.last_name}` : 'Me' }}
          </option>
          <option
            v-for="emp in employees.filter((e) => e.id !== user?.id)"
            :key="emp.id"
            :value="emp.id"
          >
            {{ emp.first_name }} {{ emp.last_name }}
          </option>
        </select>
      </div>
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
          :class="{
            today: day.isToday,
            'has-items': (dailyCounts[day.dateStr] || 0) > 0,
          }"
        >
          <span class="day-label">{{ day.label }}</span>
          <span class="day-date">{{ day.date.getDate() }}</span>
          <span class="day-count">{{ dailyCounts[day.dateStr] || 0 }}</span>
        </div>
      </div>
      <button class="week-nav" @click="weekOffset++">
        <i class="pi pi-chevron-right" />
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">Loading activity...</div>

    <!-- Empty -->
    <div v-else-if="items.length === 0" class="empty-state">
      <p>No activity found for this period</p>
      <p class="empty-hint">
        Make sure a Loki alias is configured in your profile settings.
      </p>
    </div>

    <!-- Grouped content -->
    <template v-else>
      <!-- Today section -->
      <div v-if="todayGroups.length > 0" class="day-section">
        <h3 class="day-heading clickable" @click="toggleDay('today')">
          <i class="pi collapse-icon" :class="isDayExpanded('today') ? 'pi-chevron-down' : 'pi-chevron-right'" />
          Today
          <span class="day-heading-meta">{{ formatDuration(dayTotalMinutes(todayGroups)) }}</span>
        </h3>
        <template v-if="isDayExpanded('today')">
        <div v-for="pg in todayGroups" :key="pg.project_id || 'unassigned'" class="project-group">
          <div
            class="project-group-header"
            :class="{ clickable: !!pg.project_id }"
            @click="pg.project_id ? toggleGroup(`today:${pg.project_id}`) : undefined"
          >
            <i v-if="pg.project_id" class="pi collapse-icon" :class="isExpanded('today', pg.project_id) ? 'pi-chevron-down' : 'pi-chevron-right'" />
            <span v-if="pg.project_name" class="project-pill" :class="{ auto: pg.mapping_source === 'auto' }">
              {{ pg.project_name }}
            </span>
            <span v-else class="project-unassigned">Unassigned</span>
            <span class="project-group-meta">{{ pg.files.length }} file{{ pg.files.length !== 1 ? 's' : '' }}</span>
            <span class="project-group-time">{{ formatDuration(pg.total_minutes) }}</span>
          </div>
          <div v-if="isExpanded('today', pg.project_id)" class="file-list">
            <div v-for="file in pg.files" :key="file.source_path || file.description" class="file-row">
              <i class="pi pi-file file-icon" />
              <div class="file-info">
                <span class="file-name">{{ file.description }}</span>
                <span v-if="file.source_path" class="file-path">{{ file.source_path }}</span>
              </div>
              <span v-if="file.total_commands" class="file-detail">{{ file.total_commands }} cmds</span>
              <span v-if="file.sessions > 1" class="file-sessions">{{ file.sessions }}x</span>
              <span v-if="file.total_minutes" class="file-duration">{{ formatDuration(file.total_minutes) }}</span>
              <div v-if="!pg.project_id" class="file-assign" style="position: relative">
                <button
                  class="assign-btn"
                  @click.stop="assigningItemId = assigningItemId === file.representative.id ? null : file.representative.id"
                >
                  Assign
                </button>
                <ProjectAssignPopover
                  v-if="assigningItemId === file.representative.id"
                  :item="file.representative"
                  :projects="projects"
                  @assigned="handleAssign(file.representative, $event)"
                  @cancel="assigningItemId = null"
                />
              </div>
            </div>
          </div>
        </div>
        </template>
      </div>

      <!-- Week groups -->
      <div v-for="group in weekGroups" :key="group.dateStr" class="day-section">
        <h3 class="day-heading clickable" @click="toggleDay(group.dateStr)">
          <i class="pi collapse-icon" :class="isDayExpanded(group.dateStr) ? 'pi-chevron-down' : 'pi-chevron-right'" />
          {{ group.label }}
          <span class="day-heading-meta">{{ formatDuration(dayTotalMinutes(group.projectGroups)) }}</span>
        </h3>
        <template v-if="isDayExpanded(group.dateStr)">
        <div v-for="pg in group.projectGroups" :key="pg.project_id || 'unassigned'" class="project-group">
          <div
            class="project-group-header"
            :class="{ clickable: !!pg.project_id }"
            @click="pg.project_id ? toggleGroup(`${group.dateStr}:${pg.project_id}`) : undefined"
          >
            <i v-if="pg.project_id" class="pi collapse-icon" :class="isExpanded(group.dateStr, pg.project_id) ? 'pi-chevron-down' : 'pi-chevron-right'" />
            <span v-if="pg.project_name" class="project-pill" :class="{ auto: pg.mapping_source === 'auto' }">
              {{ pg.project_name }}
            </span>
            <span v-else class="project-unassigned">Unassigned</span>
            <span class="project-group-meta">{{ pg.files.length }} file{{ pg.files.length !== 1 ? 's' : '' }}</span>
            <span class="project-group-time">{{ formatDuration(pg.total_minutes) }}</span>
          </div>
          <div v-if="isExpanded(group.dateStr, pg.project_id)" class="file-list">
            <div v-for="file in pg.files" :key="file.source_path || file.description" class="file-row">
              <i class="pi pi-file file-icon" />
              <div class="file-info">
                <span class="file-name">{{ file.description }}</span>
                <span v-if="file.source_path" class="file-path">{{ file.source_path }}</span>
              </div>
              <span v-if="file.total_commands" class="file-detail">{{ file.total_commands }} cmds</span>
              <span v-if="file.sessions > 1" class="file-sessions">{{ file.sessions }}x</span>
              <span v-if="file.total_minutes" class="file-duration">{{ formatDuration(file.total_minutes) }}</span>
              <div v-if="!pg.project_id" class="file-assign" style="position: relative">
                <button
                  class="assign-btn"
                  @click.stop="assigningItemId = assigningItemId === file.representative.id ? null : file.representative.id"
                >
                  Assign
                </button>
                <ProjectAssignPopover
                  v-if="assigningItemId === file.representative.id"
                  :item="file.representative"
                  :projects="projects"
                  @assigned="handleAssign(file.representative, $event)"
                  @cancel="assigningItemId = null"
                />
              </div>
            </div>
          </div>
        </div>
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.activity-log {
  max-width: 900px;
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

/* Week bar (same as Timesheet) */
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

.week-nav:hover {
  color: var(--p-text-color);
  background: var(--p-content-hover-background);
}

.week-nav .pi {
  font-size: 0.75rem;
}

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
  border-left: 1px solid var(--p-content-border-color);
}

.day-cell:first-child {
  border-left: none;
}

.day-cell.today .day-date {
  color: var(--p-primary-color);
  font-weight: 700;
}

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

.day-count {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.day-cell.has-items .day-count {
  color: var(--p-primary-color);
  font-weight: 600;
}

/* Content */
.loading,
.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.empty-hint {
  font-size: 0.75rem;
  margin-top: 0.5rem;
}

.day-section {
  margin-bottom: 1.5rem;
}

.day-heading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0 0 0.5rem 0;
  padding-bottom: 0.375rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.day-heading.clickable {
  cursor: pointer;
  user-select: none;
}

.day-heading.clickable:hover {
  color: var(--p-primary-color);
}

.day-heading-meta {
  margin-left: auto;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--p-primary-color);
}

.project-group {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  overflow: hidden;
  background: var(--p-content-background);
  margin-bottom: 0.75rem;
}

.project-group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--p-content-hover-background);
  border-bottom: 1px solid var(--p-content-border-color);
}

.project-group-header.clickable {
  cursor: pointer;
  user-select: none;
}

.project-group-header.clickable:hover {
  background: var(--p-surface-100);
}

:root.app-dark .project-group-header.clickable:hover {
  background: var(--p-surface-800);
}

.collapse-icon {
  font-size: 0.625rem;
  color: var(--p-text-muted-color);
  flex-shrink: 0;
}

.project-group-meta {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.project-group-time {
  margin-left: auto;
  font-weight: 700;
  font-size: 0.875rem;
  color: var(--p-primary-color);
}

.project-unassigned {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  font-style: italic;
}

.file-list {
  display: flex;
  flex-direction: column;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.375rem 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
  font-size: 0.8125rem;
}

.file-row:last-child { border-bottom: none; }
.file-row:hover { background: var(--p-content-hover-background); }

.file-icon {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  flex-shrink: 0;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  flex: 1;
  min-width: 0;
}

.file-name { font-weight: 500; }

.file-path {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-detail {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  flex-shrink: 0;
}

.file-sessions {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  padding: 0.0625rem 0.25rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.25rem;
  flex-shrink: 0;
}

.file-duration {
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--p-primary-color);
  flex-shrink: 0;
  min-width: 2.5rem;
  text-align: right;
}

.file-assign { flex-shrink: 0; }

.project-pill {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  background: var(--p-green-100);
  color: var(--p-green-700);
}

.project-pill.auto {
  background: var(--p-blue-100);
  color: var(--p-blue-700);
}

.assign-btn {
  font-size: 0.6875rem;
  padding: 0.125rem 0.5rem;
  border: 1px dashed var(--p-content-border-color);
  border-radius: 9999px;
  background: none;
  color: var(--p-text-muted-color);
  cursor: pointer;
}

.assign-btn:hover {
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
}
</style>
