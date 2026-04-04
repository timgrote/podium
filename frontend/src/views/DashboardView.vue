<script setup lang="ts">
import { onMounted, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { ProjectSummary, CompanySettings } from '../types'
import { useProjects } from '../composables/useProjects'
import { useClients } from '../composables/useClients'
import { getCompanySettings } from '../api/company'
import { useToast } from '../composables/useToast'
import ProjectList from '../components/dashboard/ProjectList.vue'
import ProjectModal from '../components/modals/ProjectModal.vue'
import DeleteConfirmModal from '../components/modals/DeleteConfirmModal.vue'
import CompanySettingsModal from '../components/modals/CompanySettingsModal.vue'
import ErrorModal from '../components/modals/ErrorModal.vue'

const router = useRouter()

const {
  filtered,
  searchQuery,
  statusFilter,
  pmFilter,
  clientFilter,
  sortField,
  sortOrder,
  uniqueStatuses,
  uniquePMs,
  pinnedIds,
  togglePin,
  reorderPinned,
  load: loadProjects,
  toggleSort,
} = useProjects()
const { load: loadClients } = useClients()
const toast = useToast()

// Modal state
const showProjectModal = ref(false)
const editingProject = ref<ProjectSummary | null>(null)
const showDeleteModal = ref(false)
const deleteLabel = ref('')
const deleteAction = ref<(() => Promise<void>) | null>(null)
const showSettingsModal = ref(false)
const showErrorModal = ref(false)
const errorMessage = ref('')
const company = ref<CompanySettings>({})

function openCreateProject() {
  editingProject.value = null
  showProjectModal.value = true
}

function openEditProject(project: ProjectSummary) {
  editingProject.value = project
  showProjectModal.value = true
}

function openDeleteProject(project: ProjectSummary) {
  deleteLabel.value = `project "${project.project_name}"`
  deleteAction.value = async () => {
    const { deleteProject } = await import('../api/projects')
    await deleteProject(project.id, true)
    toast.success('Project deleted')
    await loadProjects()
  }
  showDeleteModal.value = true
}

function showError(msg: string) {
  errorMessage.value = msg
  showErrorModal.value = true
}

async function handleSaved(created?: { id: string; project_number: string | null }) {
  await loadProjects()
  if (created) {
    router.push(`/projects/${created.project_number || created.id}`)
  }
}

async function reloadCompany() {
  try {
    const settings = await getCompanySettings()
    company.value = settings
    if (settings.company_name) {
      document.title = `${settings.company_name} — Projects`
    }
  } catch { /* non-critical */ }
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadClients()])
  reloadCompany()

  // Restore scroll position after navigating back from a project
  const savedScroll = sessionStorage.getItem('dashboardScrollY')
  if (savedScroll) {
    sessionStorage.removeItem('dashboardScrollY')
    await nextTick()
    const main = document.querySelector('.main-content')
    if (main) main.scrollTop = parseInt(savedScroll, 10)
  }
})
</script>

<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <div class="dashboard-title">
        <img v-if="company.logo_url" :src="company.logo_url" alt="" class="company-logo" />
        <h1>{{ company.company_name || 'Projects' }}</h1>
      </div>
      <button class="btn-settings" @click="showSettingsModal = true">
        <i class="pi pi-cog" />
      </button>
    </div>

    <ProjectList
      :projects="filtered"
      :pinned-ids="pinnedIds"
      :search-query="searchQuery"
      :status-filter="statusFilter"
      :pm-filter="pmFilter"
      :client-filter="clientFilter"
      :sort-field="sortField"
      :sort-order="sortOrder"
      :unique-statuses="uniqueStatuses"
      :unique-p-ms="uniquePMs"
      @update:search-query="searchQuery = $event"
      @update:status-filter="statusFilter = $event"
      @update:pm-filter="pmFilter = $event"
      @update:client-filter="clientFilter = $event"
      @toggle-sort="toggleSort"
      @toggle-pin="togglePin"
      @reorder-pinned="reorderPinned"
      @create-project="openCreateProject"
      @edit-project="openEditProject"
      @delete-project="openDeleteProject"
    />

    <!-- Modals -->
    <ProjectModal
      v-model:visible="showProjectModal"
      :project="editingProject"
      @saved="handleSaved"
      @error="showError"
      @delete="editingProject && openDeleteProject(editingProject)"
    />

    <DeleteConfirmModal
      v-model:visible="showDeleteModal"
      :label="deleteLabel"
      :action="deleteAction ?? (async () => {})"
      @error="showError"
    />

    <CompanySettingsModal
      v-model:visible="showSettingsModal"
      @saved="reloadCompany"
      @error="showError"
    />

    <ErrorModal
      v-model:visible="showErrorModal"
      :message="errorMessage"
    />
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.dashboard-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.company-logo {
  height: 2rem;
  width: auto;
  object-fit: contain;
}

.dashboard-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.btn-settings {
  background: none;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.5rem;
  cursor: pointer;
  color: var(--p-text-muted-color);
  font-size: 1rem;
}

.btn-settings:hover {
  background: var(--p-content-hover-background);
  color: var(--p-text-color);
}
</style>
