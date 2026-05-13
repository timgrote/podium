<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { MyTask, Task, ProjectSummary } from '../types'
import { getMyTasks, getDoneToday, createTask, updateTask } from '../api/tasks'
import { getProjects } from '../api/projects'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import TaskDetailModal from '../components/modals/TaskDetailModal.vue'
import {
  formatDateShort,
  isOverdue as isDateOverdue,
  todayStr,
  addDaysStr,
  isoWeekRange,
} from '../utils/dates'
import { copyLink } from '../utils/clipboard'

type FilterKey = 'up_next' | 'this_week' | 'overdue' | 'no_due_date' | 'stale'

const route = useRoute()
const router = useRouter()
const { user } = useAuth()
const toast = useToast()

const tasks = ref<MyTask[]>([])
const doneToday = ref<MyTask[]>([])
const loading = ref(true)
const taskModalVisible = ref(false)
const selectedTaskId = ref<string | null>(null)
const selectedProjectId = ref<string>('')
const expandedTasks = ref<Set<string>>(new Set())
const searchQuery = ref('')

const activeFilter = ref<FilterKey>('up_next')
const selectedProjectIds = ref<Set<string>>(new Set())
const projectFilterOpen = ref(false)

const doneTodayOpen = ref(true)
const laterOpen = ref(false)
const collapsedLaterProjects = ref<Set<string>>(new Set())

const showQuickAdd = ref(false)
const quickAddTitle = ref('')
const quickAddProjectId = ref('')
const quickAddDueDate = ref(todayStr())
const quickAddSubmitting = ref(false)
const projects = ref<ProjectSummary[]>([])

const activeTasks = computed(() =>
  tasks.value.filter(t => t.status !== 'done' && t.status !== 'canceled')
)

function matchesSearch(task: MyTask): boolean {
  if (!searchQuery.value.trim()) return true
  const q = searchQuery.value.toLowerCase()
  return (
    task.title.toLowerCase().includes(q) ||
    (task.project_name?.toLowerCase().includes(q) ?? false) ||
    (task.subtasks || []).some(s => s.title.toLowerCase().includes(q))
  )
}

function matchesProjectFilter(task: MyTask): boolean {
  if (selectedProjectIds.value.size === 0) return true
  return selectedProjectIds.value.has(task.project_id)
}

// Tasks that pass search + project filters but ignore the filter chip
const searchedActive = computed(() =>
  activeTasks.value.filter(t => matchesSearch(t) && matchesProjectFilter(t))
)

const todayValue = computed(() => todayStr())

function dueWithinDays(task: MyTask, days: number): boolean {
  if (!task.due_date) return false
  const cutoff = addDaysStr(todayValue.value, days)
  return task.due_date <= cutoff
}

// Up Next: due_date <= today+3, status open, with adaptive fill out to today+14 to ensure >= 3 rows
const upNextTasks = computed(() => {
  if (activeFilter.value !== 'up_next') return []
  let windowDays = 3
  let result: MyTask[] = []
  while (windowDays <= 14) {
    result = searchedActive.value.filter(t => dueWithinDays(t, windowDays))
    if (result.length >= 3) break
    windowDays += 1
  }
  return sortForUpNext(result)
})

function sortForUpNext(list: MyTask[]): MyTask[] {
  return [...list].sort((a, b) => {
    const aDue = a.due_date ?? '9999-12-31'
    const bDue = b.due_date ?? '9999-12-31'
    if (aDue !== bDue) return aDue.localeCompare(bDue)
    const aPri = a.priority ?? 0
    const bPri = b.priority ?? 0
    if (aPri !== bPri) return bPri - aPri
    return (a.created_at ?? '').localeCompare(b.created_at ?? '')
  })
}

// The main "Up Next" section content varies by active filter
const sectionTasks = computed<MyTask[]>(() => {
  if (activeFilter.value === 'up_next') return upNextTasks.value
  if (activeFilter.value === 'this_week') {
    const { start, end } = isoWeekRange(todayValue.value)
    return sortForUpNext(
      searchedActive.value.filter(
        t => t.due_date && t.due_date >= start && t.due_date <= end
      )
    )
  }
  if (activeFilter.value === 'overdue') {
    return sortForUpNext(searchedActive.value.filter(t => isOverdue(t)))
  }
  if (activeFilter.value === 'no_due_date') {
    return sortForUpNext(searchedActive.value.filter(t => !t.due_date))
  }
  if (activeFilter.value === 'stale') {
    return sortForUpNext(searchedActive.value.filter(t => t.is_stale))
  }
  return []
})

// IDs in the top section — exclude them from "Later"
const sectionIds = computed(() => new Set(sectionTasks.value.map(t => t.id)))

// Later: everything active that's not in the top section
const laterTasks = computed(() =>
  searchedActive.value.filter(t => !sectionIds.value.has(t.id))
)

interface ProjectGroup {
  projectName: string
  jobCode: string | null
  tasks: MyTask[]
}

const laterGroups = computed<Array<[string, ProjectGroup]>>(() => {
  const groups = new Map<string, ProjectGroup>()
  for (const task of laterTasks.value) {
    const key = task.project_id
    if (!groups.has(key)) {
      groups.set(key, {
        projectName: task.project_name || 'Unknown Project',
        jobCode: task.job_code,
        tasks: [],
      })
    }
    groups.get(key)!.tasks.push(task)
  }
  for (const g of groups.values()) g.tasks = sortForUpNext(g.tasks)
  return Array.from(groups.entries()).sort(
    ([, a], [, b]) => a.projectName.localeCompare(b.projectName)
  )
})

const filteredDoneToday = computed(() =>
  doneToday.value.filter(t => matchesSearch(t) && matchesProjectFilter(t))
)

// Per-filter count for chips (uses searchedActive so search + project filter affect counts)
const filterCounts = computed<Record<FilterKey, number>>(() => {
  const week = isoWeekRange(todayValue.value)
  return {
    up_next: upNextTasksUnclamped.value,
    this_week: searchedActive.value.filter(
      t => t.due_date && t.due_date >= week.start && t.due_date <= week.end
    ).length,
    overdue: searchedActive.value.filter(isOverdue).length,
    no_due_date: searchedActive.value.filter(t => !t.due_date).length,
    stale: searchedActive.value.filter(t => t.is_stale).length,
  }
})

// Count of Up Next using the same adaptive window as the section
const upNextTasksUnclamped = computed(() => {
  let windowDays = 3
  let count = 0
  while (windowDays <= 14) {
    count = searchedActive.value.filter(t => dueWithinDays(t, windowDays)).length
    if (count >= 3) break
    windowDays += 1
  }
  return count
})

const sectionLabel = computed(() => {
  switch (activeFilter.value) {
    case 'up_next': return 'Up Next'
    case 'this_week': return 'This Week'
    case 'overdue': return 'Overdue'
    case 'no_due_date': return 'No Due Date'
    case 'stale': return 'Stale'
  }
  return 'Up Next'
})

async function loadAll() {
  if (!user.value) return
  loading.value = true
  try {
    const [all, today] = await Promise.all([
      getMyTasks(user.value.id),
      getDoneToday(user.value.id, todayValue.value),
    ])
    tasks.value = all
    doneToday.value = today
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

function setFilter(f: FilterKey) {
  activeFilter.value = f
}

function toggleProjectFilter(projectId: string) {
  if (selectedProjectIds.value.has(projectId)) {
    selectedProjectIds.value.delete(projectId)
  } else {
    selectedProjectIds.value.add(projectId)
  }
}

function clearProjectFilter() {
  selectedProjectIds.value.clear()
}

function toggleLaterProject(projectId: string) {
  if (collapsedLaterProjects.value.has(projectId)) {
    collapsedLaterProjects.value.delete(projectId)
  } else {
    collapsedLaterProjects.value.add(projectId)
  }
}

function toggleExpand(taskId: string, event: Event) {
  event.stopPropagation()
  if (expandedTasks.value.has(taskId)) {
    expandedTasks.value.delete(taskId)
  } else {
    expandedTasks.value.add(taskId)
  }
}

async function toggleDone(task: MyTask | Task, event: Event) {
  event.stopPropagation()
  const newStatus = task.status === 'done' ? 'todo' : 'done'
  try {
    await updateTask(task.id, { status: newStatus })
    await loadAll()
  } catch (e) {
    toast.error(String(e))
  }
}

function openTask(task: MyTask | Task, projectId?: string) {
  selectedTaskId.value = task.id
  selectedProjectId.value = projectId || (task as MyTask).project_id
  taskModalVisible.value = true
}

function isOverdue(task: MyTask | Task): boolean {
  if (!task.due_date || task.status === 'done' || task.status === 'canceled') return false
  return isDateOverdue(task.due_date)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return formatDateShort(dateStr)
}

function priorityLabel(priority: number | null): string {
  if (priority === 1) return 'Low'
  if (priority === 2) return 'Medium'
  if (priority === 3) return 'High'
  return ''
}

function priorityClass(priority: number | null): string {
  if (priority === 1) return 'priority-low'
  if (priority === 2) return 'priority-medium'
  if (priority === 3) return 'priority-high'
  return ''
}

async function loadProjects() {
  try {
    projects.value = await getProjects()
  } catch (e) {
    toast.error(String(e))
  }
}

function openQuickAdd() {
  showQuickAdd.value = true
  if (!projects.value.length) loadProjects()
}

async function submitQuickAdd() {
  if (!quickAddTitle.value.trim() || !quickAddProjectId.value) return
  quickAddSubmitting.value = true
  try {
    await createTask(quickAddProjectId.value, {
      title: quickAddTitle.value.trim(),
      due_date: quickAddDueDate.value || undefined,
      assignee_ids: user.value ? [user.value.id] : undefined,
    })
    quickAddTitle.value = ''
    quickAddDueDate.value = todayStr()
    showQuickAdd.value = false
    await loadAll()
    toast.success('Task created')
  } catch (e) {
    toast.error(String(e))
  } finally {
    quickAddSubmitting.value = false
  }
}

// Project filter dropdown — load the project list when first opened
function openProjectFilter() {
  projectFilterOpen.value = !projectFilterOpen.value
  if (projectFilterOpen.value && !projects.value.length) loadProjects()
}

// Deep-link: open task from URL
watch([() => route.params.taskId, () => tasks.value.length], ([taskId, len]) => {
  if (taskId && len > 0) {
    const task = tasks.value.find(t => t.id === taskId) ||
      tasks.value.flatMap(t => t.subtasks || []).find(s => s.id === taskId)
    if (task) {
      openTask(task)
    }
  }
})

watch(taskModalVisible, (visible) => {
  if (!visible && route.params.taskId) {
    router.replace('/my-tasks')
  }
})

onMounted(loadAll)
</script>

<template>
  <div class="my-tasks">
    <div class="page-header">
      <div class="header-top">
        <h1>My Tasks</h1>
        <div class="header-actions">
          <span class="task-count">{{ activeTasks.length }} active</span>
          <button class="btn-add-task" @click="openQuickAdd">
            <i class="pi pi-plus" />
            Add Task
          </button>
        </div>
      </div>
      <div class="search-bar">
        <i class="pi pi-search search-icon" />
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          placeholder="Search tasks..."
        />
        <button
          v-if="searchQuery"
          class="search-clear"
          @click="searchQuery = ''"
        >
          <i class="pi pi-times" />
        </button>
      </div>
    </div>

    <!-- Quick Add Form -->
    <div v-if="showQuickAdd" class="quick-add-form">
      <div class="quick-add-row">
        <select v-model="quickAddProjectId" class="quick-add-select">
          <option value="" disabled>Select project...</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">
            {{ p.project_name }}{{ p.job_code ? ` (${p.job_code})` : '' }}
          </option>
        </select>
        <input
          v-model="quickAddTitle"
          class="quick-add-input"
          type="text"
          placeholder="Task title..."
          @keydown.enter="submitQuickAdd"
        />
        <input
          v-model="quickAddDueDate"
          class="quick-add-date"
          type="date"
        />
        <button
          class="quick-add-submit"
          :disabled="!quickAddTitle.trim() || !quickAddProjectId || quickAddSubmitting"
          @click="submitQuickAdd"
        >
          <i class="pi pi-check" />
        </button>
        <button class="quick-add-cancel" @click="showQuickAdd = false">
          <i class="pi pi-times" />
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading tasks...</div>

    <template v-else>
      <!-- Done today section -->
      <section class="my-section">
        <div class="section-header" @click="doneTodayOpen = !doneTodayOpen">
          <i class="pi section-chevron" :class="doneTodayOpen ? 'pi-chevron-down' : 'pi-chevron-right'" />
          <span class="section-title">Done today</span>
          <span class="section-count">{{ filteredDoneToday.length }}</span>
        </div>
        <div v-if="doneTodayOpen" class="section-body">
          <div v-if="filteredDoneToday.length === 0" class="empty-row">
            Nothing checked off yet today.
          </div>
          <div
            v-for="task in filteredDoneToday"
            :key="task.id"
            class="task-row done-row"
            @click="openTask(task)"
          >
            <button
              class="checkbox checked"
              title="Mark as not done"
              @click="toggleDone(task, $event)"
            >
              <i class="pi pi-check" />
            </button>
            <span class="task-title completed">{{ task.title }}</span>
            <span class="project-chip">{{ task.project_name }}</span>
          </div>
        </div>
      </section>

      <!-- Filter chips -->
      <div class="filter-chips">
        <button
          v-for="key in (['up_next','this_week','overdue','no_due_date','stale'] as FilterKey[])"
          :key="key"
          class="chip"
          :class="{ active: activeFilter === key }"
          @click="setFilter(key)"
        >
          {{ {
            up_next: 'Up Next',
            this_week: 'This Week',
            overdue: 'Overdue',
            no_due_date: 'No due date',
            stale: 'Stale',
          }[key] }}
          <span class="chip-count">{{ filterCounts[key] }}</span>
        </button>

        <div class="chip-divider" />

        <div class="project-chip-wrap">
          <button
            class="chip"
            :class="{ active: selectedProjectIds.size > 0 }"
            @click="openProjectFilter"
          >
            <i class="pi pi-folder" style="font-size: 0.625rem; margin-right: 0.25rem" />
            Projects
            <span v-if="selectedProjectIds.size > 0" class="chip-count">{{ selectedProjectIds.size }}</span>
          </button>
          <div v-if="projectFilterOpen" class="project-dropdown">
            <div class="dropdown-header">
              <span>Filter by project</span>
              <button v-if="selectedProjectIds.size > 0" class="link-btn" @click="clearProjectFilter">Clear</button>
            </div>
            <label
              v-for="p in projects"
              :key="p.id"
              class="dropdown-row"
            >
              <input
                type="checkbox"
                :checked="selectedProjectIds.has(p.id)"
                @change="toggleProjectFilter(p.id)"
              />
              <span>{{ p.project_name }}<span v-if="p.job_code" class="job-code"> ({{ p.job_code }})</span></span>
            </label>
            <div v-if="!projects.length" class="dropdown-empty">Loading…</div>
          </div>
        </div>
      </div>

      <!-- Up Next / active filter section -->
      <section class="my-section">
        <div class="section-header static">
          <span class="section-title">{{ sectionLabel }}</span>
          <span class="section-count">{{ sectionTasks.length }}</span>
        </div>
        <div class="section-body">
          <div v-if="sectionTasks.length === 0" class="empty-row">
            <template v-if="activeFilter === 'up_next'">All caught up — nothing due in the next two weeks.</template>
            <template v-else-if="activeFilter === 'overdue'">No overdue tasks. Nice.</template>
            <template v-else-if="activeFilter === 'no_due_date'">No orphan tasks.</template>
            <template v-else-if="activeFilter === 'stale'">No stale tasks (untouched 30+ days).</template>
            <template v-else>Nothing in this view.</template>
          </div>
          <div v-for="task in sectionTasks" :key="task.id" class="task-block">
            <div class="task-row" @click="openTask(task)">
              <button
                class="checkbox"
                :class="{ checked: task.status === 'done' }"
                title="Toggle complete"
                @click="toggleDone(task, $event)"
              >
                <i class="pi" :class="task.status === 'done' ? 'pi-check' : ''" />
              </button>
              <span class="task-title" :class="{ completed: task.status === 'done' }">{{ task.title }}</span>
              <span class="project-chip" @click.stop="router.push('/projects/' + task.project_id)">
                {{ task.project_name }}<span v-if="task.job_code" class="job-code"> ({{ task.job_code }})</span>
              </span>
              <button
                v-if="task.subtasks && task.subtasks.length"
                class="expand-btn"
                @click="toggleExpand(task.id, $event)"
              >
                <i class="pi" :class="expandedTasks.has(task.id) ? 'pi-chevron-up' : 'pi-chevron-down'" />
                <span class="subtask-count">{{ task.subtasks.length }}</span>
              </button>
              <button class="btn-copy-link" title="Copy link" @click.stop="copyLink(`/my-tasks/${task.id}`)">
                <i class="pi pi-link" />
              </button>
              <span class="spacer" />
              <span class="task-priority">
                <span v-if="task.priority" class="priority-badge" :class="priorityClass(task.priority)">
                  {{ priorityLabel(task.priority) }}
                </span>
              </span>
              <span class="task-due">
                <span v-if="task.due_date" class="due-date" :class="{ overdue: isOverdue(task) }">
                  {{ formatDate(task.due_date) }}
                </span>
                <span v-else class="due-date muted">—</span>
              </span>
            </div>
            <div v-if="task.subtasks && task.subtasks.length && expandedTasks.has(task.id)" class="subtask-list">
              <div
                v-for="sub in task.subtasks"
                :key="sub.id"
                class="subtask-row"
                @click="openTask(sub, task.project_id)"
              >
                <button
                  class="checkbox checkbox-sm"
                  :class="{ checked: sub.status === 'done' }"
                  @click="toggleDone(sub, $event)"
                >
                  <i class="pi" :class="sub.status === 'done' ? 'pi-check' : ''" />
                </button>
                <span class="task-title subtask-title" :class="{ completed: sub.status === 'done' }">{{ sub.title }}</span>
                <span v-if="sub.due_date" class="due-date" :class="{ overdue: isOverdue(sub) }">
                  {{ formatDate(sub.due_date) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Later section -->
      <section class="my-section">
        <div class="section-header" @click="laterOpen = !laterOpen">
          <i class="pi section-chevron" :class="laterOpen ? 'pi-chevron-down' : 'pi-chevron-right'" />
          <span class="section-title">Later</span>
          <span class="section-count">{{ laterTasks.length }}</span>
        </div>
        <div v-if="laterOpen" class="section-body">
          <div v-if="laterTasks.length === 0" class="empty-row">
            Nothing parked here.
          </div>
          <div
            v-for="[projectId, group] in laterGroups"
            :key="projectId"
            class="project-group-inline"
          >
            <div class="group-header-row" @click="toggleLaterProject(projectId)">
              <i class="pi header-chevron" :class="collapsedLaterProjects.has(projectId) ? 'pi-chevron-right' : 'pi-chevron-down'" />
              <span class="project-name">{{ group.projectName }}</span>
              <span v-if="group.jobCode" class="job-code">{{ group.jobCode }}</span>
              <span class="group-count">{{ group.tasks.length }}</span>
            </div>
            <div v-if="!collapsedLaterProjects.has(projectId)" class="task-list">
              <div v-for="task in group.tasks" :key="task.id" class="task-block">
                <div class="task-row" @click="openTask(task)">
                  <button
                    class="checkbox"
                    :class="{ checked: task.status === 'done' }"
                    @click="toggleDone(task, $event)"
                  >
                    <i class="pi" :class="task.status === 'done' ? 'pi-check' : ''" />
                  </button>
                  <span class="task-title">{{ task.title }}</span>
                  <button class="btn-copy-link" title="Copy link" @click.stop="copyLink(`/my-tasks/${task.id}`)">
                    <i class="pi pi-link" />
                  </button>
                  <span class="spacer" />
                  <span class="task-priority">
                    <span v-if="task.priority" class="priority-badge" :class="priorityClass(task.priority)">
                      {{ priorityLabel(task.priority) }}
                    </span>
                  </span>
                  <span class="task-due">
                    <span v-if="task.due_date" class="due-date" :class="{ overdue: isOverdue(task) }">
                      {{ formatDate(task.due_date) }}
                    </span>
                    <span v-else class="due-date muted">—</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>

    <TaskDetailModal
      v-model:visible="taskModalVisible"
      :task-id="selectedTaskId"
      :project-id="selectedProjectId"
      @saved="loadAll"
      @deleted="loadAll"
    />
  </div>
</template>

<style scoped>
.my-tasks {
  max-width: 900px;
  margin: 0 auto;
}

.page-header { margin-bottom: 1rem; }

.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.search-bar { position: relative; display: flex; align-items: center; }

.search-icon {
  position: absolute;
  left: 0.75rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.5rem 2rem 0.5rem 2.25rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
}

.search-input:focus { outline: none; border-color: var(--p-primary-color); }
.search-input::placeholder { color: var(--p-text-muted-color); }

.search-clear {
  position: absolute;
  right: 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--p-text-muted-color);
  display: flex;
  align-items: center;
}
.search-clear:hover { color: var(--p-text-color); }
.search-clear .pi { font-size: 0.6875rem; }

.header-actions { display: flex; align-items: center; gap: 1rem; }

.task-count { font-size: 0.8125rem; color: var(--p-text-muted-color); }

.loading { text-align: center; padding: 3rem; color: var(--p-text-muted-color); }

/* Sections */
.my-section {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  overflow: hidden;
  margin-bottom: 0.75rem;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: var(--p-content-hover-background);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
}
.section-header.static { cursor: default; }
.section-header:hover:not(.static) { background: var(--p-surface-200); }
:root.p-dark .section-header:hover:not(.static) { background: var(--p-surface-700); }

.section-chevron { font-size: 0.625rem; color: var(--p-text-muted-color); }

.section-title { color: var(--p-text-color); }

.section-count {
  margin-left: auto;
  font-size: 0.6875rem;
  background: var(--p-surface-300);
  color: var(--p-text-muted-color);
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
}
:root.p-dark .section-count { background: var(--p-surface-600); }

.section-body { background: var(--p-content-background); }

.empty-row {
  padding: 1rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  text-align: center;
}

/* Filter chips */
.filter-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  margin: 0.5rem 0 0.75rem;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.3125rem 0.625rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 9999px;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.1s;
}
.chip:hover { background: var(--p-content-hover-background); }
.chip.active {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.chip-count {
  font-size: 0.625rem;
  background: var(--p-surface-200);
  color: var(--p-text-muted-color);
  padding: 0 0.375rem;
  border-radius: 9999px;
  min-width: 1rem;
  text-align: center;
}
.chip.active .chip-count {
  background: rgba(255,255,255,0.25);
  color: #fff;
}

.chip-divider {
  width: 1px;
  height: 1.25rem;
  background: var(--p-content-border-color);
  margin: 0 0.25rem;
}

.project-chip-wrap { position: relative; }

.project-dropdown {
  position: absolute;
  top: calc(100% + 0.25rem);
  left: 0;
  min-width: 260px;
  max-height: 320px;
  overflow-y: auto;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  z-index: 10;
  padding: 0.375rem 0;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.75rem 0.5rem;
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--p-content-border-color);
  margin-bottom: 0.25rem;
}

.link-btn {
  background: none;
  border: none;
  color: var(--p-primary-color);
  font-size: 0.6875rem;
  cursor: pointer;
  padding: 0;
}

.dropdown-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
  cursor: pointer;
}
.dropdown-row:hover { background: var(--p-content-hover-background); }

.dropdown-empty {
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

/* Task rows (shared) */
.task-block { border-bottom: 1px solid var(--p-content-border-color); }
.task-block:last-child { border-bottom: none; }

.task-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.625rem 1rem;
  cursor: pointer;
  transition: background 0.1s;
}
.task-row:hover { background: var(--p-content-hover-background); }

.done-row {
  padding: 0.5rem 1rem;
  border-bottom: 1px solid var(--p-content-border-color);
}
.done-row:last-child { border-bottom: none; }

.checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid var(--p-content-border-color);
  border-radius: 4px;
  background: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
  padding: 0;
}
.checkbox .pi { font-size: 0.625rem; color: #fff; }
.checkbox:hover { border-color: var(--p-primary-color); }
.checkbox.checked { background: var(--p-primary-color); border-color: var(--p-primary-color); }

.checkbox-sm { width: 16px; height: 16px; }
.checkbox-sm .pi { font-size: 0.5rem; }

.task-title {
  font-size: 0.875rem;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-title.completed {
  text-decoration: line-through;
  color: var(--p-text-muted-color);
}

.project-chip {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  background: var(--p-surface-100);
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  cursor: pointer;
  flex-shrink: 0;
}
:root.p-dark .project-chip { background: var(--p-surface-700); }
.project-chip:hover { color: var(--p-primary-color); }
.project-chip .job-code { font-family: monospace; opacity: 0.75; }

.spacer { flex: 1; }

.task-priority { width: 5rem; flex-shrink: 0; text-align: center; }
.task-due { width: 5rem; flex-shrink: 0; text-align: right; }

.priority-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 500;
  white-space: nowrap;
}
.priority-low { background: var(--p-surface-200); color: var(--p-text-muted-color); }
:root.p-dark .priority-low { background: var(--p-surface-600); color: var(--p-surface-100); }
.priority-medium { background: #fef3c7; color: #92400e; }
:root.p-dark .priority-medium { background: #451a03; color: #fcd34d; }
.priority-high { background: #fee2e2; color: #dc2626; }
:root.p-dark .priority-high { background: #450a0a; color: #fca5a5; }

.due-date { font-size: 0.75rem; color: var(--p-text-muted-color); white-space: nowrap; }
.due-date.overdue { color: #dc2626; font-weight: 600; }
.due-date.muted { opacity: 0.5; }

.expand-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  background: none;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.25rem;
  padding: 0.125rem 0.375rem;
  cursor: pointer;
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
}
.expand-btn:hover {
  background: var(--p-content-hover-background);
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
}
.expand-btn .pi { font-size: 0.5rem; }
.subtask-count { font-weight: 600; }

.subtask-list {
  background: var(--p-content-hover-background);
  border-top: 1px solid var(--p-content-border-color);
}

.subtask-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 1rem 0.5rem 2.75rem;
  cursor: pointer;
  border-bottom: 1px solid var(--p-content-border-color);
}
.subtask-row:last-child { border-bottom: none; }
.subtask-row:hover { background: var(--p-surface-200); }
:root.p-dark .subtask-row:hover { background: var(--p-surface-700); }
.subtask-title { font-size: 0.8125rem; }

/* Later section: project grouping inline */
.project-group-inline { border-bottom: 1px solid var(--p-content-border-color); }
.project-group-inline:last-child { border-bottom: none; }

.group-header-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--p-text-color);
}
.group-header-row:hover { background: var(--p-content-hover-background); }

.header-chevron { font-size: 0.5625rem; color: var(--p-text-muted-color); }
.project-name { font-weight: 500; }
.job-code { font-size: 0.6875rem; color: var(--p-text-muted-color); font-family: monospace; }

.group-count {
  margin-left: auto;
  font-size: 0.625rem;
  background: var(--p-surface-300);
  color: var(--p-text-muted-color);
  padding: 0.0625rem 0.4375rem;
  border-radius: 9999px;
}
:root.p-dark .group-count { background: var(--p-surface-600); }

.task-list { border-top: 1px solid var(--p-content-border-color); }

/* Add Task button */
.btn-add-task {
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
.btn-add-task:hover { filter: brightness(1.1); }
.btn-add-task .pi { font-size: 0.625rem; }

/* Quick Add Form */
.quick-add-form {
  margin-bottom: 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 0.75rem;
  background: var(--p-content-background);
}
.quick-add-row { display: flex; align-items: center; gap: 0.5rem; }

.quick-add-select, .quick-add-input, .quick-add-date {
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
}
.quick-add-select { min-width: 160px; max-width: 200px; }
.quick-add-input { flex: 1; }
.quick-add-date { width: 140px; }
.quick-add-input:focus, .quick-add-select:focus, .quick-add-date:focus {
  outline: none;
  border-color: var(--p-primary-color);
}

.quick-add-submit, .quick-add-cancel {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  cursor: pointer;
  flex-shrink: 0;
}
.quick-add-submit:hover:not(:disabled) {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}
.quick-add-submit:disabled { opacity: 0.4; cursor: not-allowed; }
.quick-add-cancel:hover { background: var(--p-content-hover-background); }
.quick-add-submit .pi, .quick-add-cancel .pi { font-size: 0.75rem; }

.btn-copy-link {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.125rem;
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
  opacity: 0;
  transition: opacity 0.15s;
}
.task-row:hover .btn-copy-link { opacity: 1; }
.btn-copy-link:hover { color: var(--p-primary-color); }
</style>
