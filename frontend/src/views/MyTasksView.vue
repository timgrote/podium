<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { MyTask, Task, ProjectSummary, Employee } from '../types'
import { getMyTasks, getDoneToday, createTask, updateTask, getTags, bulkUpdateTasks, bulkDeleteTasks, reorderTasks } from '../api/tasks'
import type { BulkPatchFields } from '../api/tasks'
import { getProjects } from '../api/projects'
import { getEmployees } from '../api/employees'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import TaskDetailModal from '../components/modals/TaskDetailModal.vue'
import TasksBoard from '../components/kanban/TasksBoard.vue'
import {
  formatDateShort,
  isOverdue as isDateOverdue,
  todayStr,
  addDaysStr,
  nextMondayStr,
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

// View mode: 'list' (default) or 'kanban'
const viewMode = ref<'list' | 'kanban'>('list')

// Assignee filter for the Kanban board: 'me' -> current user, else all.
const boardAssignee = computed(() => {
  if (assigneeFilter.value === 'me' && user.value) return user.value.id
  return undefined
})

const doneTodayOpen = ref(true)
const laterOpen = ref(false)
const collapsedLaterProjects = ref<Set<string>>(new Set())

const showQuickAdd = ref(false)
const quickAddTitle = ref('')
const quickAddProjectId = ref('')
const quickAddDueDate = ref(todayStr())
const quickAddPriority = ref<number | null>(null)
const quickAddTags = ref('')
const quickAddSubmitting = ref(false)
const projects = ref<ProjectSummary[]>([])
const sortedProjects = computed(() =>
  [...projects.value].sort((a, b) =>
    (a.project_name || '').localeCompare(b.project_name || ''),
  ),
)
const employees = ref<Employee[]>([])
const allTags = ref<string[]>([])

// Sort mode: 'due_date' (default), 'project', 'assignee', 'tags', 'priority', 'manual'
type SortMode = 'due_date' | 'project' | 'assignee' | 'tags' | 'priority' | 'manual'
const sortMode = ref<SortMode>('due_date')

// Assignee filter: 'me' (self), 'everyone' (all), or specific employee IDs
type AssigneeFilter = 'me' | 'everyone' | 'custom'
const assigneeFilter = ref<AssigneeFilter>('me')
const selectedAssigneeIds = ref<Set<string>>(new Set())
const assigneeFilterOpen = ref(false)

// Tag filter
const selectedTagIds = ref<Set<string>>(new Set())
const tagFilterOpen = ref(false)

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
const tomorrowValue = computed(() => addDaysStr(todayValue.value, 1))
const nextMondayValue = computed(() => nextMondayStr(todayValue.value))

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
  const sorted = [...list]
  // Always pin first
  sorted.sort((a, b) => {
    const aPin = a.is_pinned ? 1 : 0
    const bPin = b.is_pinned ? 1 : 0
    if (aPin !== bPin) return bPin - aPin

    if (sortMode.value === 'project') {
      const aP = a.project_name ?? ''
      const bP = b.project_name ?? ''
      if (aP !== bP) return aP.localeCompare(bP)
    } else if (sortMode.value === 'assignee') {
      const aA = (a.assignees || []).map(e => e.last_name).join(', ')
      const bA = (b.assignees || []).map(e => e.last_name).join(', ')
      if (aA !== bA) return aA.localeCompare(bA)
    } else if (sortMode.value === 'tags') {
      const aT = (a.tags || []).join(', ')
      const bT = (b.tags || []).join(', ')
      if (aT !== bT) return aT.localeCompare(bT)
    } else if (sortMode.value === 'priority') {
      const aPri = a.priority ?? 0
      const bPri = b.priority ?? 0
      if (aPri !== bPri) return bPri - aPri
    } else if (sortMode.value === 'manual') {
      const aSort = a.sort_order ?? 9999
      const bSort = b.sort_order ?? 9999
      if (aSort !== bSort) return aSort - bSort
    }

    // Default: due date, then priority, then created
    const aDue = a.due_date ?? '9999-12-31'
    const bDue = b.due_date ?? '9999-12-31'
    if (aDue !== bDue) return aDue.localeCompare(bDue)
    const aPri = a.priority ?? 0
    const bPri = b.priority ?? 0
    if (aPri !== bPri) return bPri - aPri
    return (a.created_at ?? '').localeCompare(b.created_at ?? '')
  })
  return sorted
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
    // Determine which assignee IDs to filter by
    let assigneeIds: string[] | undefined
    if (assigneeFilter.value === 'me') {
      assigneeIds = [user.value.id]
    } else if (assigneeFilter.value === 'everyone') {
      assigneeIds = employees.value.map(e => e.id)
    } else if (assigneeFilter.value === 'custom' && selectedAssigneeIds.value.size > 0) {
      assigneeIds = [...selectedAssigneeIds.value]
    }

    // Determine tag filter
    const tagFilter = selectedTagIds.value.size > 0 ? [...selectedTagIds.value] : undefined

    const [all, today] = await Promise.all([
      getMyTasks(user.value.id, {
        assignee_ids: assigneeIds,
        tags: tagFilter,
      }),
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

async function rescheduleTask(task: MyTask | Task, dueDate: string, event?: Event) {
  event?.stopPropagation()
  try {
    await updateTask(task.id, { due_date: dueDate })
    await loadAll()
  } catch (e) {
    toast.error(String(e))
  }
}

function onPickDate(task: MyTask | Task, event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.value) return
  rescheduleTask(task, input.value)
}

function openDatePicker(event: MouseEvent) {
  const el = event.currentTarget as HTMLElement
  const input = el.querySelector('input[type="date"]') as HTMLInputElement | null
  if (input) {
    try { input.showPicker() } catch { input.focus(); input.click() }
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

function openAddTask() {
  selectedTaskId.value = null
  selectedProjectId.value = ''
  taskModalVisible.value = true
}

async function submitQuickAdd() {
  if (!quickAddTitle.value.trim() || !quickAddProjectId.value) return
  quickAddSubmitting.value = true
  try {
    await createTask(quickAddProjectId.value, {
      title: quickAddTitle.value.trim(),
      due_date: quickAddDueDate.value || undefined,
      priority: quickAddPriority.value || undefined,
      tags: quickAddTags.value.trim()
        ? quickAddTags.value.split(',').map(t => t.trim().toLowerCase()).filter(Boolean)
        : undefined,
      assignee_ids: user.value ? [user.value.id] : undefined,
    })
    quickAddTitle.value = ''
    quickAddDueDate.value = todayStr()
    quickAddPriority.value = null
    quickAddTags.value = ''
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

// Assignee filter
function setAssigneeFilter(mode: AssigneeFilter) {
  assigneeFilter.value = mode
  selectedAssigneeIds.value.clear()
  assigneeFilterOpen.value = false
  loadAll()
}

function toggleAssigneeFilter(empId: string) {
  if (selectedAssigneeIds.value.has(empId)) {
    selectedAssigneeIds.value.delete(empId)
  } else {
    selectedAssigneeIds.value.add(empId)
  }
  if (selectedAssigneeIds.value.size > 0) {
    assigneeFilter.value = 'custom'
  } else if (assigneeFilter.value === 'custom') {
    // No one selected — fall back to "me" so the list isn't empty
    assigneeFilter.value = 'me'
  }
  loadAll()
}

const assigneeFilterLabel = computed(() => {
  if (assigneeFilter.value === 'me') return 'Just me'
  if (assigneeFilter.value === 'everyone') return 'Everyone'
  if (selectedAssigneeIds.value.size > 0) return `${selectedAssigneeIds.value.size} people`
  return 'Custom'
})

// Tag filter
function toggleTagFilter(tag: string) {
  if (selectedTagIds.value.has(tag)) {
    selectedTagIds.value.delete(tag)
  } else {
    selectedTagIds.value.add(tag)
  }
  loadAll()
}

function clearTagFilter() {
  selectedTagIds.value.clear()
  loadAll()
}

// Pin toggle from row
async function togglePin(task: MyTask | Task, event: Event) {
  event.stopPropagation()
  try {
    await updateTask(task.id, { is_pinned: !task.is_pinned })
    await loadAll()
  } catch (e) {
    toast.error(String(e))
  }
}

// Manual reordering — drag and up/down buttons
const draggingTaskId = ref<string | null>(null)
const dragOverTaskId = ref<string | null>(null)

async function moveTask(sourceId: string, targetId: string) {
  const list = sectionTasks.value
  const fromIdx = list.findIndex(t => t.id === sourceId)
  const toIdx = list.findIndex(t => t.id === targetId)
  if (fromIdx === -1 || toIdx === -1 || fromIdx === toIdx) return

  // Reorder
  const reordered = [...list]
  const [moved] = reordered.splice(fromIdx, 1)
  if (!moved) return
  reordered.splice(toIdx, 0, moved)

  // Persist new sort_order for all affected tasks in a single request
  const items = reordered.map((t, i) => ({ task_id: t.id, sort_order: i + 1 }))
  try {
    await reorderTasks(items)
    await loadAll()
  } catch (e) {
    toast.error(String(e))
  }
}

function onTaskDragStart(taskId: string, event: DragEvent) {
  draggingTaskId.value = taskId
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', taskId)
  }
}

function onTaskDragOver(taskId: string, event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
  dragOverTaskId.value = taskId
}

function onTaskDragLeave() {
  dragOverTaskId.value = null
}

function onTaskDrop(targetId: string, event: DragEvent) {
  event.preventDefault()
  const sourceId = draggingTaskId.value
  draggingTaskId.value = null
  dragOverTaskId.value = null
  if (sourceId && sourceId !== targetId) {
    moveTask(sourceId, targetId)
  }
}

function onTaskDragEnd() {
  draggingTaskId.value = null
  dragOverTaskId.value = null
}

async function moveTaskUp(task: MyTask | Task, event: Event) {
  event.stopPropagation()
  const list = sectionTasks.value
  const idx = list.findIndex(t => t.id === task.id)
  if (idx <= 0) return
  const target = list[idx - 1]
  if (target) await moveTask(task.id, target.id)
}

async function moveTaskDown(task: MyTask | Task, event: Event) {
  event.stopPropagation()
  const list = sectionTasks.value
  const idx = list.findIndex(t => t.id === task.id)
  if (idx === -1 || idx >= list.length - 1) return
  const target = list[idx + 1]
  if (target) await moveTask(task.id, target.id)
}

function isTopTask(task: MyTask | Task): boolean {
  const list = sectionTasks.value
  return list.length > 0 && list[0]?.id === task.id
}

function isBottomTask(task: MyTask | Task): boolean {
  const list = sectionTasks.value
  return list.length > 0 && list[list.length - 1]?.id === task.id
}

// Multi-select for bulk actions
const selectedTaskIds = ref<Set<string>>(new Set())
const bulkMode = ref(false)
const bulkPriority = ref<number | null>(null)
const bulkDueDate = ref<string>('')
const bulkAddTags = ref('')
const bulkSaving = ref(false)

function toggleBulkMode() {
  bulkMode.value = !bulkMode.value
  if (!bulkMode.value) {
    selectedTaskIds.value.clear()
    bulkPriority.value = null
    bulkDueDate.value = ''
  }
}

function toggleTaskSelection(taskId: string, event: Event) {
  event.stopPropagation()
  if (selectedTaskIds.value.has(taskId)) {
    selectedTaskIds.value.delete(taskId)
  } else {
    selectedTaskIds.value.add(taskId)
  }
}

function selectAllVisible() {
  for (const t of sectionTasks.value) {
    selectedTaskIds.value.add(t.id)
  }
}

function clearSelection() {
  selectedTaskIds.value.clear()
}

async function applyBulkUpdate() {
  if (selectedTaskIds.value.size === 0) return
  bulkSaving.value = true
  try {
    const patch: BulkPatchFields = {}
    if (bulkPriority.value !== null) patch.priority = bulkPriority.value
    if (bulkDueDate.value) patch.due_date = bulkDueDate.value
    if (bulkAddTags.value.trim()) {
      patch.add_tags = bulkAddTags.value.split(',').map(t => t.trim().toLowerCase()).filter(Boolean)
    }
    if (bulkPriority.value === null && !bulkDueDate.value && !bulkAddTags.value.trim()) {
      toast.info('Nothing to update — set a priority, date, or tags first')
      return
    }
    const ids = Array.from(selectedTaskIds.value)
    await bulkUpdateTasks(ids, patch)
    bulkPriority.value = null
    bulkDueDate.value = ''
    bulkAddTags.value = ''
    await loadAll()
    toast.success(`Updated ${ids.length} task${ids.length > 1 ? 's' : ''}`)
  } catch (e) {
    toast.error(String(e))
  } finally {
    bulkSaving.value = false
  }
}

async function bulkMarkDone() {
  if (selectedTaskIds.value.size === 0) return
  bulkSaving.value = true
  try {
    const ids = Array.from(selectedTaskIds.value)
    await bulkUpdateTasks(ids, { status: 'done' })
    clearSelection()
    await loadAll()
    toast.success(`Marked ${ids.length} task${ids.length > 1 ? 's' : ''} done`)
  } catch (e) {
    toast.error(String(e))
  } finally {
    bulkSaving.value = false
  }
}

const showBulkDeleteConfirm = ref(false)

async function bulkDeleteSelected() {
  if (selectedTaskIds.value.size === 0) return
  bulkSaving.value = true
  try {
    const ids = Array.from(selectedTaskIds.value)
    await bulkDeleteTasks(ids)
    clearSelection()
    showBulkDeleteConfirm.value = false
    await loadAll()
    toast.success(`Deleted ${ids.length} task${ids.length > 1 ? 's' : ''}`)
  } catch (e) {
    toast.error(String(e))
  } finally {
    bulkSaving.value = false
  }
}

// Load employees and tags
async function loadEmployees() {
  try {
    employees.value = await getEmployees()
  } catch (e) {
    toast.error(String(e))
  }
}

async function loadAllTags() {
  try {
    allTags.value = await getTags()
  } catch (e) {
    toast.error(String(e))
  }
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

onMounted(() => {
  loadAll()
  loadEmployees()
  loadAllTags()
})
</script>

<template>
  <div class="my-tasks" :class="{ 'board-mode': viewMode === 'kanban' }">
    <div class="page-header">
      <div class="header-top">
        <h1>My Tasks</h1>
        <div class="header-actions">
          <span class="task-count">{{ activeTasks.length }} active</span>
          <button
            class="btn-bulk-toggle"
            :class="{ active: viewMode === 'kanban' }"
            @click="viewMode = viewMode === 'list' ? 'kanban' : 'list'"
            :title="viewMode === 'list' ? 'Switch to Kanban board' : 'Switch to list view'"
          >
            <i class="pi pi-th-large" />
            {{ viewMode === 'list' ? 'Board' : 'List' }}
          </button>
          <button
            class="btn-bulk-toggle"
            :class="{ active: bulkMode }"
            @click="toggleBulkMode"
          >
            <i class="pi pi-check-square" />
            {{ bulkMode ? 'Done' : 'Select' }}
          </button>
          <button class="btn-add-task btn-quick-task" @click="openQuickAdd">
            <i class="pi pi-plus" />
            Quick Task
          </button>
          <button class="btn-add-task" @click="openAddTask">
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

    <!-- Kanban board view -->
    <TasksBoard v-if="viewMode === 'kanban'" :assignee="boardAssignee" class="tasks-board" />

    <template v-if="viewMode === 'list'">
    <!-- Quick Add Form -->
    <div v-if="showQuickAdd" class="quick-add-form">
      <div class="quick-add-row">
        <select v-model="quickAddProjectId" class="quick-add-select">
          <option value="" disabled>Select project...</option>
          <option v-for="p in sortedProjects" :key="p.id" :value="p.id">
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
        <select v-model="quickAddPriority" class="quick-add-priority">
          <option :value="null">Priority...</option>
          <option :value="1">Low</option>
          <option :value="2">Medium</option>
          <option :value="3">High</option>
        </select>
        <input
          v-model="quickAddTags"
          class="quick-add-tags"
          type="text"
          placeholder="Tags (comma-separated)..."
          @keydown.enter="submitQuickAdd"
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

    <!-- Bulk action bar -->
    <div v-if="bulkMode && selectedTaskIds.size > 0" class="bulk-action-bar">
      <span class="bulk-count">{{ selectedTaskIds.size }} selected</span>
      <select v-model="bulkPriority" class="bulk-select">
        <option :value="null">Priority...</option>
        <option :value="1">Low</option>
        <option :value="2">Medium</option>
        <option :value="3">High</option>
      </select>
      <input v-model="bulkDueDate" type="date" class="bulk-date" />
      <input
        v-model="bulkAddTags"
        type="text"
        class="bulk-tags"
        placeholder="Add tags (comma-separated)..."
      />
      <button class="btn btn-sm btn-success" :disabled="bulkSaving" @click="bulkMarkDone">
        <i class="pi pi-check" /> Mark Done
      </button>
      <template v-if="!showBulkDeleteConfirm">
        <button class="btn btn-sm btn-danger" :disabled="bulkSaving" @click="showBulkDeleteConfirm = true">
          <i class="pi pi-trash" /> Delete
        </button>
      </template>
      <template v-else>
        <span class="bulk-confirm-text">Delete {{ selectedTaskIds.size }} task{{ selectedTaskIds.size > 1 ? 's' : '' }}?</span>
        <button class="btn btn-sm btn-danger" :disabled="bulkSaving" @click="bulkDeleteSelected">
          {{ bulkSaving ? 'Deleting...' : 'Yes, delete' }}
        </button>
        <button class="btn btn-sm" @click="showBulkDeleteConfirm = false">Cancel</button>
      </template>
      <span class="bulk-spacer" />
      <button class="btn btn-sm btn-primary" :disabled="bulkSaving" @click="applyBulkUpdate">
        {{ bulkSaving ? 'Updating...' : 'Apply' }}
      </button>
      <button class="btn btn-sm" @click="clearSelection">Clear</button>
    </div>
    <div v-else-if="bulkMode" class="bulk-action-hint">
      Select tasks to update. <button class="link-btn" @click="selectAllVisible">Select all visible</button>
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
              v-for="p in sortedProjects"
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

        <!-- Assignee filter -->
        <div class="project-chip-wrap">
          <button
            class="chip"
            :class="{ active: assigneeFilter !== 'me' || selectedAssigneeIds.size > 0 }"
            @click="assigneeFilterOpen = !assigneeFilterOpen"
          >
            <i class="pi pi-users" style="font-size: 0.625rem; margin-right: 0.25rem" />
            {{ assigneeFilterLabel }}
          </button>
          <div v-if="assigneeFilterOpen" class="project-dropdown">
            <div class="dropdown-header">
              <span>Filter by assignee</span>
            </div>
            <button class="dropdown-row dropdown-row-btn" :class="{ selected: assigneeFilter === 'me' }" @click="setAssigneeFilter('me')">
              Just me
            </button>
            <button class="dropdown-row dropdown-row-btn" :class="{ selected: assigneeFilter === 'everyone' }" @click="setAssigneeFilter('everyone')">
              Everyone
            </button>
            <div class="dropdown-divider" />
            <label
              v-for="emp in employees"
              :key="emp.id"
              class="dropdown-row"
            >
              <input
                type="checkbox"
                :checked="selectedAssigneeIds.has(emp.id)"
                @change="toggleAssigneeFilter(emp.id)"
              />
              <span>{{ emp.first_name }} {{ emp.last_name }}</span>
            </label>
          </div>
        </div>

        <!-- Tag filter -->
        <div v-if="allTags.length > 0" class="project-chip-wrap">
          <button
            class="chip"
            :class="{ active: selectedTagIds.size > 0 }"
            @click="tagFilterOpen = !tagFilterOpen"
          >
            <i class="pi pi-tags" style="font-size: 0.625rem; margin-right: 0.25rem" />
            Tags
            <span v-if="selectedTagIds.size > 0" class="chip-count">{{ selectedTagIds.size }}</span>
          </button>
          <div v-if="tagFilterOpen" class="project-dropdown">
            <div class="dropdown-header">
              <span>Filter by tag</span>
              <button v-if="selectedTagIds.size > 0" class="link-btn" @click="clearTagFilter">Clear</button>
            </div>
            <label
              v-for="tag in allTags"
              :key="tag"
              class="dropdown-row"
            >
              <input
                type="checkbox"
                :checked="selectedTagIds.has(tag)"
                @change="toggleTagFilter(tag)"
              />
              <span class="tag-label">{{ tag }}</span>
            </label>
          </div>
        </div>

        <!-- Sort dropdown -->
        <div class="project-chip-wrap sort-wrap">
          <select v-model="sortMode" class="sort-select" @change="loadAll">
            <option value="due_date">Sort: Due date</option>
            <option value="priority">Sort: Priority</option>
            <option value="project">Sort: Project</option>
            <option value="assignee">Sort: Assignee</option>
            <option value="tags">Sort: Tags</option>
            <option value="manual">Sort: Manual</option>
          </select>
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
          <div
            v-for="task in sectionTasks"
            :key="task.id"
            class="task-block"
            :class="{
              'task-pinned': task.is_pinned,
              'dragging': draggingTaskId === task.id,
              'drag-over': dragOverTaskId === task.id,
              'reorderable': sortMode === 'manual',
            }"
            :draggable="sortMode === 'manual'"
            @dragstart="onTaskDragStart(task.id, $event)"
            @dragover="onTaskDragOver(task.id, $event)"
            @dragleave="onTaskDragLeave"
            @drop="onTaskDrop(task.id, $event)"
            @dragend="onTaskDragEnd"
          >
            <div class="task-row" @click="openTask(task)">
              <button
                v-if="bulkMode"
                class="checkbox bulk-checkbox"
                :class="{ checked: selectedTaskIds.has(task.id) }"
                @click="toggleTaskSelection(task.id, $event)"
              >
                <i class="pi" :class="selectedTaskIds.has(task.id) ? 'pi-check' : ''" />
              </button>
              <button
                class="checkbox"
                :class="{ checked: task.status === 'done' }"
                title="Toggle complete"
                @click="toggleDone(task, $event)"
              >
                <i class="pi" :class="task.status === 'done' ? 'pi-check' : ''" />
              </button>
              <button
                class="pin-btn"
                :class="{ active: task.is_pinned }"
                title="Pin to top"
                @click.stop="togglePin(task, $event)"
              >
                <i class="pi" :class="task.is_pinned ? 'pi-bookmark-fill' : 'pi-bookmark'" />
              </button>
              <template v-if="sortMode === 'manual'">
                <button
                  class="reorder-btn"
                  :disabled="isTopTask(task)"
                  title="Move up"
                  @click.stop="moveTaskUp(task, $event)"
                >
                  <i class="pi pi-angle-up" />
                </button>
                <button
                  class="reorder-btn"
                  :disabled="isBottomTask(task)"
                  title="Move down"
                  @click.stop="moveTaskDown(task, $event)"
                >
                  <i class="pi pi-angle-down" />
                </button>
              </template>
              <span class="task-title" :class="{ completed: task.status === 'done' }">{{ task.title }}</span>
              <span v-if="task.tags && task.tags.length" class="task-tags">
                <span v-for="tag in task.tags" :key="tag" class="task-tag-chip">{{ tag }}</span>
              </span>
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
              <span class="spacer" />
              <span class="task-priority">
                <span v-if="task.priority" class="priority-badge" :class="priorityClass(task.priority)">
                  {{ priorityLabel(task.priority) }}
                </span>
              </span>
              <span class="row-chips">
                <button class="btn-copy-link row-chip-icon" title="Copy link" @click.stop="copyLink(`/my-tasks/${task.id}`)">
                  <i class="pi pi-link" />
                </button>
                <button
                  class="row-chip"
                  title="Push to tomorrow"
                  @click.stop="rescheduleTask(task, tomorrowValue, $event)"
                >→ Tomorrow</button>
                <button
                  class="row-chip"
                  title="Push to next Monday"
                  @click.stop="rescheduleTask(task, nextMondayValue, $event)"
                >→ Next Mon</button>
              </span>
              <span
                class="task-due-inline"
                :class="{ overdue: isOverdue(task), 'no-date': !task.due_date }"
                title="Pick date"
                @click.stop="openDatePicker"
              >
                <span v-if="task.due_date">{{ formatDate(task.due_date) }}</span>
                <span v-else>—</span>
                <input
                  type="date"
                  class="inline-date-input"
                  :value="task.due_date || ''"
                  @change="onPickDate(task, $event)"
                />
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
              <div v-for="task in group.tasks" :key="task.id" class="task-block" :class="{ 'task-pinned': task.is_pinned }">
                <div class="task-row" @click="openTask(task)">
                  <button
                    v-if="bulkMode"
                    class="checkbox bulk-checkbox"
                    :class="{ checked: selectedTaskIds.has(task.id) }"
                    @click="toggleTaskSelection(task.id, $event)"
                  >
                    <i class="pi" :class="selectedTaskIds.has(task.id) ? 'pi-check' : ''" />
                  </button>
                  <button
                    class="checkbox"
                    :class="{ checked: task.status === 'done' }"
                    @click="toggleDone(task, $event)"
                  >
                    <i class="pi" :class="task.status === 'done' ? 'pi-check' : ''" />
                  </button>
                  <button
                    class="pin-btn"
                    :class="{ active: task.is_pinned }"
                    title="Pin to top"
                    @click.stop="togglePin(task, $event)"
                  >
                    <i class="pi" :class="task.is_pinned ? 'pi-bookmark-fill' : 'pi-bookmark'" />
                  </button>
                  <span class="task-title">{{ task.title }}</span>
                  <span v-if="task.tags && task.tags.length" class="task-tags">
                    <span v-for="tag in task.tags" :key="tag" class="task-tag-chip">{{ tag }}</span>
                  </span>
                  <span class="spacer" />
                  <span class="row-chips">
                    <button class="btn-copy-link row-chip-icon" title="Copy link" @click.stop="copyLink(`/my-tasks/${task.id}`)">
                      <i class="pi pi-link" />
                    </button>
                    <button
                      class="row-chip"
                      title="Push to tomorrow"
                      @click.stop="rescheduleTask(task, tomorrowValue, $event)"
                    >→ Tomorrow</button>
                    <button
                      class="row-chip"
                      title="Push to next Monday"
                      @click.stop="rescheduleTask(task, nextMondayValue, $event)"
                    >→ Next Mon</button>
                  </span>
                  <span class="task-priority">
                    <span v-if="task.priority" class="priority-badge" :class="priorityClass(task.priority)">
                      {{ priorityLabel(task.priority) }}
                    </span>
                  </span>
                  <span
                    class="task-due-inline"
                    :class="{ overdue: isOverdue(task), 'no-date': !task.due_date }"
                    title="Pick date"
                    @click.stop="openDatePicker"
                  >
                    <span v-if="task.due_date">{{ formatDate(task.due_date) }}</span>
                    <span v-else>—</span>
                    <input
                      type="date"
                      class="inline-date-input"
                      :value="task.due_date || ''"
                      @change="onPickDate(task, $event)"
                    />
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
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
.my-tasks.board-mode {
  /* Kanban board fills the full main content width. */
  max-width: none;
  width: 100%;
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
  color: #1e293b;
  background: #e2e8f0;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  cursor: pointer;
  flex-shrink: 0;
  font-weight: 500;
}
:root.p-dark .project-chip { background: #475569; color: #f1f5f9; }
.project-chip:hover { background: var(--p-primary-color); color: #fff; }
.project-chip .job-code { font-family: monospace; opacity: 0.75; }
.project-chip:hover .job-code { color: #fff; opacity: 1; }

.spacer { flex: 1; }

.task-priority { width: 5rem; flex-shrink: 0; text-align: center; }
.task-due { width: 5rem; flex-shrink: 0; text-align: right; }

.task-due-inline {
  width: 5rem;
  flex-shrink: 0;
  position: relative;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
}
.task-due-inline:hover { color: var(--p-primary-color); }
.task-due-inline.overdue { color: #dc2626; font-weight: 600; }
.task-due-inline.overdue:hover { color: #b91c1c; }
.task-due-inline.no-date { opacity: 0.5; }

.inline-date-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  width: 100%;
  cursor: pointer;
  font-size: 0.75rem;
  border: none;
  padding: 0;
  background: transparent;
}

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
.btn-quick-task {
  background: var(--p-content-background);
  color: var(--p-text-color);
  border: 1px solid var(--p-content-border-color);
}
.btn-quick-task:hover { background: var(--p-content-hover-background); filter: none; }

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
.quick-add-priority {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
  cursor: pointer;
}
.quick-add-priority:focus { outline: none; border-color: var(--p-primary-color); }
.quick-add-tags {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
  min-width: 160px;
}
.quick-add-tags:focus { outline: none; border-color: var(--p-primary-color); }
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

/* Inline reschedule chips — hover-revealed, flush right against due date */
.row-chips {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.15s;
  margin-right: 0.5rem;
}
.task-row:hover .row-chips { opacity: 1; }

.row-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.1875rem 0.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 9999px;
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
  cursor: pointer;
  white-space: nowrap;
  line-height: 1;
}
.row-chip:hover {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}
.row-chip-icon {
  padding: 0.1875rem 0.375rem;
  opacity: 1 !important;
}

/* Pin button on task rows */
.pin-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--p-text-muted-color);
  padding: 0.1875rem 0.25rem;
  font-size: 0.75rem;
  opacity: 0.4;
  transition: opacity 0.15s, color 0.15s;
}
.pin-btn:hover { opacity: 1; color: var(--p-primary-color); }
.pin-btn.active { opacity: 1; color: var(--p-primary-color); }
.task-pinned {
  background: var(--p-highlight-background);
  border-left: 3px solid var(--p-primary-color);
  border-radius: 0.25rem;
}

/* Tag chips on task rows */
.task-tags {
  display: inline-flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}
.task-tag-chip {
  font-size: 0.625rem;
  padding: 0.0625rem 0.375rem;
  background: var(--p-content-hover-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 9999px;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

/* Sort dropdown */
.sort-wrap { margin-left: auto; }
.sort-select {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.75rem;
  cursor: pointer;
}
.sort-select:focus { outline: none; border-color: var(--p-primary-color); }

/* Dropdown helpers for assignee/tag filter */
.dropdown-row-btn {
  display: flex;
  align-items: center;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.375rem 0.5rem;
  font-size: 0.8125rem;
  color: var(--p-text-color);
}
.dropdown-row-btn:hover { background: var(--p-content-hover-background); }
.dropdown-row-btn.selected { font-weight: 600; color: var(--p-primary-color); }
.dropdown-divider {
  height: 1px;
  background: var(--p-content-border-color);
  margin: 0.25rem 0;
}
.tag-label { text-transform: lowercase; }

/* Bulk action bar */
.btn-bulk-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  cursor: pointer;
  font-size: 0.75rem;
  transition: all 0.15s;
}
.btn-bulk-toggle:hover { border-color: var(--p-primary-color); color: var(--p-text-color); }
.btn-bulk-toggle.active { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.bulk-action-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  margin-bottom: 0.75rem;
  background: var(--p-highlight-background);
  border: 1px solid var(--p-primary-color);
  border-radius: 0.5rem;
}
.bulk-count { font-size: 0.8125rem; font-weight: 600; color: var(--p-primary-color); }
.bulk-spacer { flex: 1; }
.bulk-select, .bulk-date, .bulk-tags {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
}
.bulk-select:focus, .bulk-date:focus, .bulk-tags:focus { outline: none; border-color: var(--p-primary-color); }
.bulk-tags { min-width: 180px; }
.bulk-action-hint {
  padding: 0.5rem 1rem;
  margin-bottom: 0.75rem;
  background: var(--p-content-hover-background);
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}
.link-btn {
  background: none;
  border: none;
  color: var(--p-primary-color);
  cursor: pointer;
  font-size: 0.8125rem;
  text-decoration: underline;
  padding: 0;
}
.bulk-checkbox { border-color: var(--p-primary-color); }
.bulk-confirm-text { font-size: 0.8125rem; color: var(--p-red-600); font-weight: 600; }
.btn-success { background: var(--p-green-600); color: #fff; border-color: var(--p-green-600); }
.btn-success:hover { background: var(--p-green-700); }
.btn-success:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger { color: var(--p-red-600); border-color: var(--p-red-300); }
.btn-danger:hover { background: var(--p-red-50); }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

/* Manual reordering */
.reorder-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--p-text-muted-color);
  padding: 0.125rem 0.1875rem;
  font-size: 0.8125rem;
  opacity: 0.4;
  transition: opacity 0.15s, color 0.15s;
}
.reorder-btn:hover { opacity: 1; color: var(--p-primary-color); }
.reorder-btn:disabled { opacity: 0.2; cursor: not-allowed; }
.task-block.reorderable { cursor: grab; }
.task-block.reorderable:active { cursor: grabbing; }
.task-block.dragging { opacity: 0.4; }
.task-block.drag-over { border-top: 2px solid var(--p-primary-color); }
</style>
