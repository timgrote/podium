<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ProjectSummary } from '../../types'
import ProjectCard from './ProjectCard.vue'

const props = defineProps<{
  projects: ProjectSummary[]
  pinnedIds: Set<string>
  searchQuery: string
  statusFilter: string
  pmFilter: string
  clientFilter: string
  sortField: string
  sortOrder: string
  uniqueStatuses: string[]
  uniquePMs: string[]
}>()

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  'update:statusFilter': [value: string]
  'update:pmFilter': [value: string]
  'update:clientFilter': [value: string]
  toggleSort: [field: string]
  createProject: []
  editProject: [project: ProjectSummary]
  deleteProject: [project: ProjectSummary]
  togglePin: [projectId: string]
  reorderPinned: [fromId: string, toId: string, position: 'before' | 'after']
}>()

const dragId = ref<string | null>(null)
const dragOverId = ref<string | null>(null)
const dragPosition = ref<'before' | 'after'>('before')

function onDragStart(projectId: string, e: DragEvent) {
  dragId.value = projectId
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
  }
}

function onDragOver(projectId: string, e: DragEvent) {
  if (!dragId.value || !props.pinnedIds.has(projectId) || dragId.value === projectId) return
  e.preventDefault()
  dragOverId.value = projectId
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  dragPosition.value = e.clientY < rect.top + rect.height / 2 ? 'before' : 'after'
}

function onDrop(projectId: string) {
  if (dragId.value && dragId.value !== projectId) {
    emit('reorderPinned', dragId.value, projectId, dragPosition.value)
  }
  dragId.value = null
  dragOverId.value = null
}

function onDragEnd() {
  dragId.value = null
  dragOverId.value = null
}

const pinnedProjects = computed(() => props.projects.filter((p) => props.pinnedIds.has(p.id)))
const unpinnedProjects = computed(() => props.projects.filter((p) => !props.pinnedIds.has(p.id)))
</script>

<template>
  <div class="project-list">
    <div class="sticky-header">
    <div class="list-toolbar">
      <div class="search-bar">
        <i class="pi pi-search" />
        <input
          type="text"
          placeholder="Search projects..."
          :value="searchQuery"
          @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
        />
        <button
          v-if="searchQuery"
          class="search-clear"
          @click="emit('update:searchQuery', '')"
        >
          <i class="pi pi-times" />
        </button>
      </div>
      <div class="filters">
        <select
          :value="statusFilter"
          @change="emit('update:statusFilter', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">All Statuses</option>
          <option v-for="s in uniqueStatuses" :key="s" :value="s">{{ s }}</option>
        </select>
        <select
          :value="pmFilter"
          @change="emit('update:pmFilter', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">All PMs</option>
          <option v-for="pm in uniquePMs" :key="pm" :value="pm">{{ pm }}</option>
        </select>
      </div>
      <button class="btn btn-primary" @click="emit('createProject')">
        <i class="pi pi-plus" /> New Project
      </button>
    </div>

    <div class="column-headers">
      <div class="col-pm"></div>
      <div class="col-project sortable" @click="emit('toggleSort', 'project_name')">
        Project
        <i v-if="sortField === 'project_name'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
      <div class="col-deadline sortable" @click="emit('toggleSort', 'next_task_deadline')">
        Deadline
        <i v-if="sortField === 'next_task_deadline'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
      <div class="col-financial sortable" @click="emit('toggleSort', 'total_contracted')">
        Contracted
        <i v-if="sortField === 'total_contracted'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
      <div class="col-financial sortable" @click="emit('toggleSort', 'total_invoiced')">
        Invoiced
        <i v-if="sortField === 'total_invoiced'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
      <div class="col-edit"></div>
    </div>
    </div>

    <div v-if="pinnedProjects.length > 0" class="pinned-section">
      <ProjectCard
        v-for="project in pinnedProjects"
        :key="project.id"
        :project="project"
        :pinned="true"
        :class="{ 'drag-insert-before': dragOverId === project.id && dragPosition === 'before', 'drag-insert-after': dragOverId === project.id && dragPosition === 'after' }"
        :draggable="true"
        @dragstart="onDragStart(project.id, $event)"
        @dragover="onDragOver(project.id, $event)"
        @drop="onDrop(project.id)"
        @dragend="onDragEnd"
        @edit="emit('editProject', project)"
        @toggle-pin="emit('togglePin', project.id)"
      />
    </div>

    <div class="cards">
      <ProjectCard
        v-for="project in unpinnedProjects"
        :key="project.id"
        :project="project"
        :pinned="false"
        @edit="emit('editProject', project)"
        @toggle-pin="emit('togglePin', project.id)"
      />
      <div v-if="projects.length === 0" class="empty-state">
        No projects found.
      </div>
    </div>
  </div>
</template>

<style scoped>
.project-list {
  display: flex;
  flex-direction: column;
}

.sticky-header {
  position: sticky;
  top: -1.5rem;
  z-index: 5;
  background: var(--p-surface-50);
  padding-top: 1.5rem;
  padding-bottom: 0.5rem;
  margin-top: -1.5rem;
}

:root.app-dark .sticky-header {
  background: var(--p-surface-950);
}

.list-toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding-bottom: 0.75rem;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  flex: 1;
  min-width: 200px;
}

.search-bar i {
  color: var(--p-text-muted-color);
}

.search-bar input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 0.875rem;
  background: transparent;
  color: var(--p-text-color);
}

.search-clear {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.125rem;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  display: flex;
  align-items: center;
}

.search-clear:hover {
  color: var(--p-text-color);
}

.filters {
  display: flex;
  gap: 0.5rem;
}

.filters select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  cursor: pointer;
}

.column-headers {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.025em;
  gap: 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.column-headers .sortable {
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.column-headers .sortable:hover {
  color: var(--p-text-color);
}

.column-headers .sortable .pi {
  font-size: 0.625rem;
}

.col-pm { width: 48px; flex-shrink: 0; }
.col-project { flex: 1; min-width: 0; }
.col-deadline { width: 6.5rem; flex-shrink: 0; }
.col-financial { width: 5rem; flex-shrink: 0; text-align: right; justify-content: flex-end; }
.col-edit { width: 1.5rem; flex-shrink: 0; }

.cards {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.5rem;
}

.pinned-section {
  position: sticky;
  top: 5.5rem;
  z-index: 4;
  background: var(--p-surface-50);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem 0;
}

:root.app-dark .pinned-section {
  background: var(--p-surface-950);
}

.drag-insert-before {
  box-shadow: 0 -2px 0 0 var(--p-primary-color);
}

.drag-insert-after {
  box-shadow: 0 2px 0 0 var(--p-primary-color);
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.15s;
  white-space: nowrap;
  color: var(--p-text-color);
}

.btn-primary {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.btn-primary:hover {
  background: var(--p-primary-hover-color);
}
</style>
