<script setup lang="ts">
import { ref } from 'vue'
import type { ProjectSummary } from '../../types'
import ProjectCard from './ProjectCard.vue'
import ProjectDetail from './ProjectDetail.vue'

defineProps<{
  projects: ProjectSummary[]
  searchQuery: string
  statusFilter: string
  pmFilter: string
  clientFilter: string
  uniqueStatuses: string[]
  uniquePMs: string[]
}>()

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  'update:statusFilter': [value: string]
  'update:pmFilter': [value: string]
  'update:clientFilter': [value: string]
  createProject: []
  editProject: [project: ProjectSummary]
  deleteProject: [project: ProjectSummary]
  createContract: [projectId: string]
  editContract: [contractId: string]
  deleteContract: [contractId: string]
  createInvoice: [contractId: string]
  editInvoice: [invoiceId: string]
  deleteInvoice: [invoiceId: string]
  invoiceActions: [invoiceId: string]
  createProposal: [projectId: string]
  editProposal: [proposalId: string]
  deleteProposal: [proposalId: string]
  promoteProposal: [proposalId: string]
  viewNotes: [projectId: string]
}>()

const expandedId = ref<string | null>(null)

function toggleExpand(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}
</script>

<template>
  <div class="project-list">
    <div class="list-toolbar">
      <div class="search-bar">
        <i class="pi pi-search" />
        <input
          type="text"
          placeholder="Search projects..."
          :value="searchQuery"
          @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
        />
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

    <div class="cards">
      <ProjectCard
        v-for="project in projects"
        :key="project.id"
        :project="project"
        :expanded="expandedId === project.id"
        @toggle="toggleExpand(project.id)"
      >
        <ProjectDetail
          :project="project"
          @edit-project="emit('editProject', project)"
          @delete-project="emit('deleteProject', project)"
          @create-contract="emit('createContract', $event)"
          @edit-contract="emit('editContract', $event)"
          @delete-contract="emit('deleteContract', $event)"
          @create-invoice="emit('createInvoice', $event)"
          @edit-invoice="emit('editInvoice', $event)"
          @delete-invoice="emit('deleteInvoice', $event)"
          @invoice-actions="emit('invoiceActions', $event)"
          @create-proposal="emit('createProposal', $event)"
          @edit-proposal="emit('editProposal', $event)"
          @delete-proposal="emit('deleteProposal', $event)"
          @promote-proposal="emit('promoteProposal', $event)"
          @view-notes="emit('viewNotes', $event)"
        />
      </ProjectCard>
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
  gap: 1rem;
}

.list-toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
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

.cards {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
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
