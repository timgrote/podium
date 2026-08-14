<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { CalendarItem } from '../api/calendar'
import { getCalendar } from '../api/calendar'
import { updateTask } from '../api/tasks'
import { updateDeliverable } from '../api/deliverables'
import { useToast } from '../composables/useToast'
import {
  todayStr, addDaysStr, addMonthsStr, isoWeekRange, monthStart, monthEnd, dayRange,
  monthGrid, startOfWeek, weekdayShort, formatDateShort,
} from '../utils/dates'

type ViewMode = 'list' | 'week' | 'twoweek' | 'month'

const toast = useToast()
const router = useRouter()

const items = ref<CalendarItem[]>([])
const loading = ref(true)

// Anchor date used to compute the visible range (YYYY-MM-DD).
const anchor = ref(todayStr())

// Filters (empty = all)
const viewMode = ref<ViewMode>('month')
const priorityFilter = ref<number | null>(null)
const companyFilter = ref<string>('')      // client_id
const assigneeFilter = ref<string>('')     // employee_id

const priorities: { value: number | null; label: string }[] = [
  { value: null, label: 'All priorities' },
  { value: 3, label: 'High' },
  { value: 2, label: 'Medium' },
  { value: 1, label: 'Low' },
]

// Filter option lists derived from the loaded items.
const companies = computed(() => {
  const map = new Map<string, string>()
  for (const it of items.value) {
    if (it.client_id && it.client_name) map.set(it.client_id, it.client_name)
  }
  return Array.from(map.entries()).map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name))
})

const assignees = computed(() => {
  const map = new Map<string, string>()
  for (const it of items.value) {
    for (const a of it.assignees) map.set(a.id, `${a.first_name} ${a.last_name}`.trim())
  }
  return Array.from(map.entries()).map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name))
})

function matchesFilters(it: CalendarItem): boolean {
  if (priorityFilter.value != null && it.priority !== priorityFilter.value) return false
  if (companyFilter.value && it.client_id !== companyFilter.value) return false
  if (assigneeFilter.value && !it.assignees.some(a => a.id === assigneeFilter.value)) return false
  return true
}

const filtered = computed(() => items.value.filter(matchesFilters))

function itemsOn(dateStr: string): CalendarItem[] {
  return filtered.value.filter(it => it.date === dateStr)
}

// --- Visible range per view mode ---
const visibleRange = computed<[string, string]>(() => {
  const a = anchor.value
  switch (viewMode.value) {
    case 'list': {
      const { start } = isoWeekRange(a)
      return [start, addDaysStr(start, 13)]
    }
    case 'week': {
      const { start, end } = isoWeekRange(a)
      return [start, end]
    }
    case 'twoweek': {
      const start = startOfWeek(a)
      return [start, addDaysStr(start, 13)]
    }
    case 'month': {
      return [monthStart(a), monthEnd(a)]
    }
  }
})

// List view: two weeks of days, grouped.
const listDays = computed(() => {
  const [start, end] = visibleRange.value
  const days: { date: string; items: CalendarItem[] }[] = []
  let d = start
  while (d <= end) {
    const dayItems = itemsOn(d)
    if (dayItems.length > 0) days.push({ date: d, items: dayItems })
    d = addDaysStr(d, 1)
  }
  return days
})

const weekDays = computed(() => {
  const [start, end] = visibleRange.value
  return dayRange(start, Math.round((Date.parse(end) - Date.parse(start)) / 86400000) + 1)
})

// Chunk weekDays into rows of 7 (1 row for week, 2 for two-week).
const gridRows = computed(() => {
  const days = weekDays.value
  const rows: string[][] = []
  for (let i = 0; i < days.length; i += 7) rows.push(days.slice(i, i + 7))
  return rows
})

const monthRows = computed(() => monthGrid(anchor.value))

const rangeLabel = computed(() => {
  const [start, end] = visibleRange.value
  return `${formatDateShort(start)} – ${formatDateShort(end)}`
})

function gotoToday() { anchor.value = todayStr() }

function prev() {
  if (viewMode.value === 'month') anchor.value = addMonthsStr(anchor.value, -1)
  else anchor.value = addDaysStr(anchor.value, viewMode.value === 'week' ? -7 : -14)
}

function next() {
  if (viewMode.value === 'month') anchor.value = addMonthsStr(anchor.value, 1)
  else anchor.value = addDaysStr(anchor.value, viewMode.value === 'week' ? 7 : 14)
}

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

function kindClass(it: CalendarItem): string {
  return it.kind === 'task' ? 'kind-task' : 'kind-deliverable'
}

function kindLabel(it: CalendarItem): string {
  return it.kind === 'task' ? 'Task' : 'Deliverable'
}

function isPast(dateStr: string): boolean {
  return dateStr < todayStr()
}

// --- Checkbox / completion toggle ---
const DONE_STATUSES = { task: 'done', deliverable: 'accepted' } as const
const NOT_DONE_STATUSES = { task: 'todo', deliverable: 'not_started' } as const
const toggling = ref<Set<string>>(new Set())

function isDone(it: CalendarItem): boolean {
  return it.status === DONE_STATUSES[it.kind]
}

function checkboxId(it: CalendarItem): string {
  return `cal-check-${it.kind}-${it.id}`
}

async function toggleDone(it: CalendarItem, event: Event) {
  event.stopPropagation()
  if (toggling.value.has(it.id)) return
  toggling.value.add(it.id)
  const done = isDone(it)
  const newStatus = done ? NOT_DONE_STATUSES[it.kind] : DONE_STATUSES[it.kind]
  try {
    if (it.kind === 'task') {
      await updateTask(it.id, { status: newStatus })
    } else {
      // When marking a deliverable done, set progress to 100%;
      // when un-checking, revert to whatever it was before completion.
      const patch: { status: string; progress_percent?: number } = { status: newStatus }
      if (!done) {
        patch.progress_percent = 100
      } else if (it.progress_percent === 100) {
        patch.progress_percent = 0
      }
      await updateDeliverable(it.id, patch)
      if ('progress_percent' in patch) {
        it.progress_percent = patch.progress_percent!
      }
    }
    it.status = newStatus
  } catch (e) {
    toast.error(`Failed to update: ${e}`)
  } finally {
    toggling.value.delete(it.id)
  }
}

function openItem(it: CalendarItem) {
  router.push(`/projects/${it.project_id}`)
}

async function load() {
  loading.value = true
  try {
    items.value = await getCalendar()
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="calendar-view">
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="btn" @click="prev"><i class="pi pi-chevron-left" /></button>
        <button class="btn" @click="gotoToday">Today</button>
        <button class="btn" @click="next"><i class="pi pi-chevron-right" /></button>
        <span class="range-label">{{ rangeLabel }}</span>
      </div>
      <div class="view-switcher">
        <button
          v-for="mode in ([['list','List'],['week','Week'],['twoweek','2 Weeks'],['month','Month']] as [ViewMode,string][])"
          :key="mode[0]"
          class="btn view-btn"
          :class="{ active: viewMode === mode[0] }"
          @click="viewMode = mode[0]"
        >{{ mode[1] }}</button>
      </div>
    </div>

    <div class="filter-bar">
      <select v-model="priorityFilter" class="filter-select" title="Priority">
        <option v-for="p in priorities" :key="p.value ?? 'all'" :value="p.value ?? ''">
          {{ p.label }}
        </option>
      </select>
      <select v-model="companyFilter" class="filter-select" title="Company">
        <option value="">All companies</option>
        <option v-for="c in companies" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <select v-model="assigneeFilter" class="filter-select" title="Assignee">
        <option value="">All assignees</option>
        <option v-for="a in assignees" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <div v-if="priorityFilter || companyFilter || assigneeFilter" class="filter-count">
        {{ filtered.length }} item{{ filtered.length === 1 ? '' : 's' }}
      </div>
    </div>

    <div v-if="loading" class="empty">Loading calendar…</div>

    <!-- LIST VIEW -->
    <div v-else-if="viewMode === 'list'" class="list-layout">
      <div v-if="listDays.length === 0" class="empty">No deadlines in this range.</div>
      <div v-for="day in listDays" :key="day.date" class="list-day">
        <div class="list-day-head">
          <span class="list-date" :class="{ past: isPast(day.date) }">{{ formatDateShort(day.date) }}</span>
          <span v-if="day.date === todayStr()" class="today-chip">Today</span>
        </div>
        <div class="list-items">
          <div
            v-for="it in day.items"
            :key="it.kind + it.id"
            class="item-row"
            :class="kindClass(it)"
            @click="openItem(it)"
          >
            <input
              type="checkbox"
              class="cal-checkbox"
              :id="checkboxId(it)"
              :checked="isDone(it)"
              :disabled="toggling.has(it.id)"
              @click="toggleDone(it, $event)"
            >
            <span class="item-kind">{{ kindLabel(it) }}</span>
            <span class="item-title" :class="{ 'done-text': isDone(it) }">{{ it.title }}</span>
            <span v-if="it.priority" class="pill" :class="priorityClass(it.priority)">{{ priorityLabel(it.priority) }}</span>
            <span class="item-project">{{ it.project_name }}</span>
            <span v-if="it.client_name" class="item-company">{{ it.client_name }}</span>
            <span v-if="it.assignees.length" class="item-assignees">
              {{ it.assignees.map(a => `${a.first_name} ${a.last_name}`.trim()).join(', ') }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- WEEK / 2-WEEK GRID -->
    <div v-else-if="viewMode === 'week' || viewMode === 'twoweek'" class="grid-wrap">
      <div v-for="(row, ri) in gridRows" :key="ri" class="grid-layout">
        <div class="grid-head">
          <div v-for="d in row" :key="d" class="grid-head-cell">
            <span class="head-weekday">{{ weekdayShort(d) }}</span>
            <span class="head-date" :class="{ 'is-today': d === todayStr(), past: isPast(d) }">{{ d.slice(8) }}</span>
          </div>
        </div>
        <div class="grid-body">
          <div v-for="d in row" :key="d" class="grid-day" :class="{ 'is-today': d === todayStr(), 'is-past': isPast(d) }">
            <template v-for="it in itemsOn(d)" :key="it.kind + it.id">
              <div class="grid-item" :class="[kindClass(it), priorityClass(it.priority)]" :title="it.title" @click="openItem(it)">
                <div class="grid-item-row">
                  <input
                    type="checkbox"
                    class="cal-checkbox cal-checkbox-sm"
                    :checked="isDone(it)"
                    :disabled="toggling.has(it.id)"
                    @click="toggleDone(it, $event)"
                  >
                  <span class="grid-item-company">{{ it.client_name || it.project_name }}</span>
                </div>
                <span class="grid-item-title" :class="{ 'done-text': isDone(it) }">{{ it.title }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- MONTH GRID -->
    <div v-else class="month-layout">
      <div class="month-head">
        <div v-for="wd in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']" :key="wd" class="month-head-cell">{{ wd }}</div>
      </div>
      <div v-for="(row, ri) in monthRows" :key="ri" class="month-row">
        <div v-for="d in row" :key="d" class="month-day" :class="{ 'is-today': d === todayStr(), 'is-past': isPast(d), 'is-other-month': d.slice(0,7) !== monthStart(anchor).slice(0,7) }">
          <span class="month-date">{{ d.slice(8) }}</span>
          <template v-for="it in itemsOn(d).slice(0, 3)" :key="it.kind + it.id">
            <div class="month-item" :class="[kindClass(it), priorityClass(it.priority)]" :title="it.title" @click="openItem(it)">
              <div class="grid-item-row">
                <input
                  type="checkbox"
                  class="cal-checkbox cal-checkbox-sm"
                  :checked="isDone(it)"
                  :disabled="toggling.has(it.id)"
                  @click="toggleDone(it, $event)"
                >
                <span class="grid-item-company">{{ it.client_name || it.project_name }}</span>
              </div>
              <span class="grid-item-title" :class="{ 'done-text': isDone(it) }">{{ it.title }}</span>
            </div>
          </template>
          <span v-if="itemsOn(d).length > 3" class="month-more">+{{ itemsOn(d).length - 3 }} more</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.calendar-view { display: flex; flex-direction: column; gap: 0.75rem; }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap; }
.toolbar-left { display: flex; align-items: center; gap: 0.25rem; }
.range-label { font-size: 0.8125rem; color: var(--p-text-muted-color); font-weight: 500; margin-left: 0.5rem; }
.view-switcher { display: flex; gap: 0.25rem; }

.btn {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.375rem 0.625rem; border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem; background: var(--p-form-field-background); color: var(--p-text-color);
  font-size: 0.8125rem; cursor: pointer;
}
.btn:hover { border-color: var(--p-primary-color); }
.view-btn.active { background: var(--p-primary-color); border-color: var(--p-primary-color); color: #fff; }

.filter-bar { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.filter-select {
  padding: 0.375rem 0.5rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem;
  background: var(--p-form-field-background); color: var(--p-text-color); font-size: 0.8125rem;
}
.filter-count { font-size: 0.8125rem; color: var(--p-text-muted-color); }
.empty { font-size: 0.8125rem; color: var(--p-text-muted-color); font-style: italic; padding: 1rem 0; }

/* Shared pills */
.pill { font-size: 0.6875rem; font-weight: 600; padding: 0.0625rem 0.375rem; border-radius: 999px; flex-shrink: 0; }
.priority-high { background: var(--p-red-100); color: var(--p-red-700); }
.priority-medium { background: var(--p-amber-100); color: var(--p-amber-700); }
.priority-low { background: var(--p-green-100); color: var(--p-green-600); }

/* LIST */
.list-layout { display: flex; flex-direction: column; gap: 1rem; }
.list-day-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
.list-date { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--p-text-color); }
.list-date.past { color: var(--p-red-600); }
.today-chip { font-size: 0.625rem; font-weight: 700; background: var(--p-primary-color); color: #fff; padding: 0.0625rem 0.375rem; border-radius: 999px; }
.list-items { display: flex; flex-direction: column; gap: 0.25rem; }
.item-row {
  display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.5rem; font-size: 0.8125rem;
  border-radius: 0.3125rem; cursor: pointer; border-left: 3px solid var(--p-surface-300);
}
.item-row:hover { background: var(--p-content-hover-background); }
.item-row.kind-task { border-left-color: var(--p-primary-color); }
.item-row.kind-deliverable { border-left-color: var(--p-purple-400); }
.item-kind { font-size: 0.625rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; width: 5rem; flex-shrink: 0; }
.kind-task .item-kind { color: var(--p-primary-color); }
.kind-deliverable .item-kind { color: var(--p-purple-400); }
.item-title { flex: 1; min-width: 0; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-project { font-size: 0.75rem; color: var(--p-text-muted-color); flex-shrink: 0; max-width: 14rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-company { font-size: 0.75rem; color: var(--p-text-muted-color); flex-shrink: 0; }
.item-assignees { font-size: 0.75rem; color: var(--p-text-muted-color); flex-shrink: 0; }

/* WEEK / 2-WEEK GRID */
.grid-wrap { display: flex; flex-direction: column; gap: 1rem; }
.grid-layout { border: 1px solid var(--p-content-border-color); border-radius: 0.5rem; overflow: hidden; }
.grid-head { display: grid; grid-template-columns: repeat(7, 1fr); border-bottom: 1px solid var(--p-content-border-color); }
.grid-head-cell { padding: 0.5rem; display: flex; flex-direction: column; align-items: center; gap: 0.125rem; }
.head-weekday { font-size: 0.6875rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; }
.head-date { font-size: 0.75rem; font-weight: 600; }
.head-date.is-today { color: var(--p-primary-color); }
.head-date.past { color: var(--p-red-600); }
.grid-body { display: grid; grid-template-columns: repeat(7, 1fr); }
.grid-day { min-height: 4.5rem; padding: 0.25rem; border-right: 1px solid var(--p-content-border-color); display: flex; flex-direction: column; gap: 0.125rem; overflow: hidden; }
.grid-day:last-child { border-right: none; }
.grid-day.is-past { background: var(--p-content-hover-background); }
.grid-day.is-today { background: color-mix(in srgb, var(--p-primary-color) 8%, transparent); }
.grid-item {
  font-size: 0.6875rem; padding: 0.125rem 0.25rem; border-radius: 0.25rem; cursor: pointer;
  overflow: hidden; background: var(--p-surface-200); color: var(--p-text-color);
  display: flex; flex-direction: column; line-height: 1.2;
}
.grid-item-company {
  font-size: 0.5625rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--p-text-muted-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.grid-item-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kind-task.grid-item { background: color-mix(in srgb, var(--p-primary-color) 14%, transparent); }
.kind-deliverable.grid-item { background: color-mix(in srgb, var(--p-purple-400) 16%, transparent); }
.grid-item:hover { filter: brightness(0.95); }

/* MONTH */
.month-layout { border: 1px solid var(--p-content-border-color); border-radius: 0.5rem; overflow: hidden; }
.month-head { display: grid; grid-template-columns: repeat(7, 1fr); border-bottom: 1px solid var(--p-content-border-color); }
.month-head-cell { padding: 0.375rem; text-align: center; font-size: 0.6875rem; font-weight: 600; color: var(--p-text-muted-color); text-transform: uppercase; }
.month-row { display: grid; grid-template-columns: repeat(7, 1fr); }
.month-day { min-height: 5rem; padding: 0.25rem; border-right: 1px solid var(--p-content-border-color); border-bottom: 1px solid var(--p-content-border-color); display: flex; flex-direction: column; gap: 0.125rem; overflow: hidden; }
.month-row:last-child .month-day { border-bottom: none; }
.month-day:nth-child(7n) { border-right: none; }
.month-day.is-other-month { opacity: 0.4; }
.month-day.is-past .month-date { color: var(--p-red-600); }
.month-date { font-size: 0.6875rem; font-weight: 600; }
.month-day.is-today .month-date {
  background: var(--p-primary-color); color: #fff; border-radius: 999px; width: 1.25rem; height: 1.25rem;
  display: flex; align-items: center; justify-content: center;
}
.month-item {
  font-size: 0.625rem; padding: 0.0625rem 0.25rem; border-radius: 0.25rem; cursor: pointer;
  overflow: hidden; display: flex; flex-direction: column; line-height: 1.2;
}
.month-item .grid-item-company { font-size: 0.5rem; }
.month-item .grid-item-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kind-task.month-item { background: color-mix(in srgb, var(--p-primary-color) 14%, transparent); }
.kind-deliverable.month-item { background: color-mix(in srgb, var(--p-purple-400) 16%, transparent); }
.month-more { font-size: 0.625rem; color: var(--p-text-muted-color); }

/* CHECKBOX */
.cal-checkbox { flex-shrink: 0; cursor: pointer; width: 1rem; height: 1rem; margin: 0; }
.cal-checkbox-sm { width: 0.75rem; height: 0.75rem; }
.cal-checkbox:disabled { cursor: wait; opacity: 0.6; }
.grid-item-row { display: flex; align-items: center; gap: 0.1875rem; min-width: 0; }
.done-text { text-decoration: line-through; opacity: 0.5; }
</style>
