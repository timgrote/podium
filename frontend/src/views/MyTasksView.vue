<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { MyTask } from '../types'
import { getMyTasks, updateTask } from '../api/tasks'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import TaskDetailModal from '../components/modals/TaskDetailModal.vue'

const { user } = useAuth()
const toast = useToast()
const tasks = ref<MyTask[]>([])
const loading = ref(true)
const taskModalVisible = ref(false)
const selectedTaskId = ref<string | null>(null)
const selectedProjectId = ref<string>('')
const collapsedProjects = ref<Set<string>>(new Set())
const showCompleted = ref(false)

const statusCycle = ['todo', 'in_progress', 'done'] as const

const activeTasks = computed(() => tasks.value.filter(t => t.status !== 'done' && t.status !== 'canceled'))
const completedTasks = computed(() => tasks.value.filter(t => t.status === 'done' || t.status === 'canceled'))

const displayTasks = computed(() => showCompleted.value ? completedTasks.value : activeTasks.value)

const groupedByProject = computed(() => {
  const groups = new Map<string, { projectName: string; jobCode: string | null; tasks: MyTask[] }>()
  for (const task of displayTasks.value) {
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
  return groups
})

async function loadTasks() {
  if (!user.value) return
  try {
    tasks.value = await getMyTasks(user.value.id)
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

function toggleProject(projectId: string) {
  if (collapsedProjects.value.has(projectId)) {
    collapsedProjects.value.delete(projectId)
  } else {
    collapsedProjects.value.add(projectId)
  }
}

async function cycleStatus(task: MyTask, event: Event) {
  event.stopPropagation()
  const currentIdx = statusCycle.indexOf(task.status as typeof statusCycle[number])
  const nextStatus = statusCycle[(currentIdx + 1) % statusCycle.length]
  try {
    await updateTask(task.id, { status: nextStatus })
    await loadTasks()
  } catch (e) {
    toast.error(String(e))
  }
}

function openTask(task: MyTask) {
  selectedTaskId.value = task.id
  selectedProjectId.value = task.project_id
  taskModalVisible.value = true
}

function isOverdue(task: MyTask): boolean {
  if (!task.due_date || task.status === 'done' || task.status === 'canceled') return false
  return new Date(task.due_date) < new Date(new Date().toDateString())
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function statusLabel(status: string): string {
  return status.replace('_', ' ')
}

onMounted(loadTasks)
</script>

<template>
  <div class="my-tasks">
    <div class="page-header">
      <h1>My Tasks</h1>
      <div class="header-actions">
        <span class="task-count">{{ activeTasks.length }} active</span>
        <button
          class="toggle-completed"
          :class="{ active: showCompleted }"
          @click="showCompleted = !showCompleted"
        >
          <i class="pi" :class="showCompleted ? 'pi-eye-slash' : 'pi-eye'" />
          {{ showCompleted ? 'Show Active' : 'Show Completed' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading tasks...</div>

    <div v-else-if="displayTasks.length === 0" class="empty-state">
      <i class="pi pi-check-circle empty-icon" />
      <p v-if="showCompleted">No completed tasks</p>
      <p v-else>No tasks assigned to you</p>
    </div>

    <div v-else class="project-groups">
      <div
        v-for="[projectId, group] in groupedByProject"
        :key="projectId"
        class="project-group"
      >
        <button class="group-header" @click="toggleProject(projectId)">
          <i class="pi" :class="collapsedProjects.has(projectId) ? 'pi-chevron-right' : 'pi-chevron-down'" />
          <span class="project-name">{{ group.projectName }}</span>
          <span v-if="group.jobCode" class="job-code">{{ group.jobCode }}</span>
          <span class="group-count">{{ group.tasks.length }}</span>
        </button>

        <div v-if="!collapsedProjects.has(projectId)" class="task-list">
          <div
            v-for="task in group.tasks"
            :key="task.id"
            class="task-row"
            @click="openTask(task)"
          >
            <button
              class="status-badge"
              :class="task.status"
              :title="'Click to change status'"
              @click="cycleStatus(task, $event)"
            >
              {{ statusLabel(task.status) }}
            </button>
            <span class="task-title">{{ task.title }}</span>
            <span
              v-if="task.due_date"
              class="due-date"
              :class="{ overdue: isOverdue(task) }"
            >
              {{ formatDate(task.due_date) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <TaskDetailModal
      v-model:visible="taskModalVisible"
      :task-id="selectedTaskId"
      :project-id="selectedProjectId"
      @saved="loadTasks"
      @deleted="loadTasks"
    />
  </div>
</template>

<style scoped>
.my-tasks {
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
  gap: 1rem;
}

.task-count {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.toggle-completed {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  cursor: pointer;
}

.toggle-completed:hover {
  background: var(--p-content-hover-background);
}

.toggle-completed.active {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--p-text-muted-color);
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--p-text-muted-color);
}

.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
  display: block;
}

.empty-state p {
  font-size: 0.9375rem;
  margin: 0;
}

.project-groups {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.project-group {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  overflow: hidden;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--p-content-hover-background);
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--p-text-color);
  text-align: left;
}

.group-header:hover {
  background: var(--p-surface-200);
}

:root.p-dark .group-header:hover {
  background: var(--p-surface-700);
}

.group-header .pi {
  font-size: 0.625rem;
  color: var(--p-text-muted-color);
}

.project-name {
  font-weight: 600;
}

.job-code {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  font-family: monospace;
}

.group-count {
  margin-left: auto;
  font-size: 0.6875rem;
  background: var(--p-surface-300);
  color: var(--p-text-muted-color);
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
}

:root.p-dark .group-count {
  background: var(--p-surface-600);
}

.task-list {
  border-top: 1px solid var(--p-content-border-color);
}

.task-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  cursor: pointer;
  transition: background 0.1s;
  border-bottom: 1px solid var(--p-content-border-color);
}

.task-row:last-child {
  border-bottom: none;
}

.task-row:hover {
  background: var(--p-content-hover-background);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.5rem;
  border: none;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: capitalize;
  cursor: pointer;
  white-space: nowrap;
  transition: filter 0.1s;
}

.status-badge:hover {
  filter: brightness(0.9);
}

.status-badge.todo {
  background: var(--p-surface-200);
  color: var(--p-text-muted-color);
}

:root.p-dark .status-badge.todo {
  background: var(--p-surface-600);
}

.status-badge.in_progress {
  background: #dbeafe;
  color: #1d4ed8;
}

:root.p-dark .status-badge.in_progress {
  background: #1e3a5f;
  color: #93c5fd;
}

.status-badge.blocked {
  background: #fef3c7;
  color: #92400e;
}

:root.p-dark .status-badge.blocked {
  background: #451a03;
  color: #fcd34d;
}

.status-badge.done {
  background: #dcfce7;
  color: #166534;
}

:root.p-dark .status-badge.done {
  background: #14532d;
  color: #86efac;
}

.status-badge.canceled {
  background: var(--p-surface-200);
  color: var(--p-text-muted-color);
  text-decoration: line-through;
}

.task-title {
  flex: 1;
  font-size: 0.875rem;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.due-date {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

.due-date.overdue {
  color: #dc2626;
  font-weight: 600;
}
</style>
