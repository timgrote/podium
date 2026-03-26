<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ProjectSummary } from '../types'
import { useProjects } from '../composables/useProjects'
import { useProjectUpdates } from '../composables/useProjectUpdates'
import { useToast } from '../composables/useToast'
import { getUserSettings } from '../api/auth'
import ProjectHeader from '../components/project/ProjectHeader.vue'
import ProjectSidebar from '../components/project/ProjectSidebar.vue'
import type { Section } from '../components/project/ProjectSidebar.vue'
import ProjectTasks from '../components/project/ProjectTasks.vue'
import ProjectNotes from '../components/project/ProjectNotes.vue'
import ProjectTime from '../components/project/ProjectTime.vue'
import ProjectTeam from '../components/project/ProjectTeam.vue'
import ProjectContracts from '../components/project/ProjectContracts.vue'
import ProjectInvoices from '../components/project/ProjectInvoices.vue'
import ProjectProposals from '../components/project/ProjectProposals.vue'
import ProjectModal from '../components/modals/ProjectModal.vue'
import ContractModal from '../components/modals/ContractModal.vue'
import InvoiceCreateModal from '../components/modals/InvoiceCreateModal.vue'
import InvoiceEditModal from '../components/modals/InvoiceEditModal.vue'
import InvoiceActionsModal from '../components/modals/InvoiceActionsModal.vue'
import ProposalModal from '../components/modals/ProposalModal.vue'
import PromoteProposalModal from '../components/modals/PromoteProposalModal.vue'
import DeleteConfirmModal from '../components/modals/DeleteConfirmModal.vue'
import ErrorModal from '../components/modals/ErrorModal.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { projects: allProjects, load: loadProjects } = useProjects()

// Route params
const routeProjectNumber = computed(() => (route.params.projectId as string) || null)
const routeEntityId = computed(() => (route.params.entityId as string) || null)
const routeEntityType = computed(() => {
  const path = route.path
  if (path.includes('/tasks/')) return 'task'
  if (path.includes('/contracts/')) return 'contract'
  if (path.includes('/invoices/')) return 'invoice'
  if (path.includes('/proposals/')) return 'proposal'
  return null
})

// Find the project by project_number or id
const project = computed<ProjectSummary | null>(() => {
  if (!routeProjectNumber.value) return null
  return allProjects.value.find(p =>
    p.project_number === routeProjectNumber.value || p.id === routeProjectNumber.value
  ) || null
})

// Active section from query param
const validSections: Section[] = ['tasks', 'notes', 'time', 'contracts', 'invoices', 'proposals', 'team']
const activeSection = computed<Section>({
  get() {
    const s = route.query.section as string
    if (s && validSections.includes(s as Section)) return s as Section
    // Auto-select based on entity type route
    if (routeEntityType.value === 'contract') return 'contracts'
    if (routeEntityType.value === 'invoice') return 'invoices'
    if (routeEntityType.value === 'proposal') return 'proposals'
    if (routeEntityType.value === 'task') return 'tasks'
    return 'tasks'
  },
  set(section: Section) {
    router.replace({ query: { ...route.query, section } })
  },
})

// Dropbox folder link
const DEFAULT_DROPBOX_PATH = 'D:/Dropbox/TIE'
const dropboxBasePath = ref(DEFAULT_DROPBOX_PATH)
getUserSettings().then(s => {
  if (s.dropbox_base_path) dropboxBasePath.value = s.dropbox_base_path
}).catch(() => {})

const folderHref = computed(() => {
  if (!project.value?.data_path || !dropboxBasePath.value) return null
  const base = dropboxBasePath.value.replace(/\/+$/, '')
  return `openfolder://${base}/${project.value.data_path}`
})

// Component refs for badge counts
const tasksRef = ref<InstanceType<typeof ProjectTasks> | null>(null)
const notesRef = ref<InstanceType<typeof ProjectNotes> | null>(null)
const timeRef = ref<InstanceType<typeof ProjectTime> | null>(null)
const teamRef = ref<InstanceType<typeof ProjectTeam> | null>(null)

// Badge counts
const taskCount = computed(() => tasksRef.value?.totalTaskCount || 0)
const notesCount = computed(() => notesRef.value?.notesCount || 0)
const totalHours = computed(() => timeRef.value?.totalHours || 0)
const teamCount = computed(() => teamRef.value?.teamCount || 0)

// SSE live updates
const projectIdRef = computed(() => project.value?.id || null)
useProjectUpdates(projectIdRef, (eventType) => {
  if (eventType.startsWith('task_')) {
    tasksRef.value?.loadTasks?.()
  } else if (eventType === 'note_added' || eventType === 'note_deleted') {
    notesRef.value?.loadNotes?.()
  } else if (eventType === 'project_updated' || eventType === 'contract_updated' || eventType === 'invoice_updated' || eventType === 'proposal_updated') {
    loadProjects()
  }
})

// Modal state
const showProjectModal = ref(false)
const showContractModal = ref(false)
const contractProjectId = ref('')
const editingContractId = ref<string | null>(null)
const showInvoiceCreateModal = ref(false)
const invoiceContractId = ref('')
const showInvoiceEditModal = ref(false)
const editingInvoiceId = ref('')
const showInvoiceActionsModal = ref(false)
const actionsInvoiceId = ref('')
const showProposalModal = ref(false)
const proposalProjectId = ref('')
const editingProposalId = ref<string | null>(null)
const showPromoteModal = ref(false)
const promoteProposalId = ref('')
const showDeleteModal = ref(false)
const deleteLabel = ref('')
const deleteAction = ref<(() => Promise<void>) | null>(null)
const showErrorModal = ref(false)
const errorMessage = ref('')
const projectsLoaded = ref(false)

// Deep-link: open entity modal when route + projects are ready
watch([routeEntityType, routeEntityId, () => projectsLoaded.value], ([type, id, loaded]) => {
  if (!type || !id || !loaded) return
  if (type === 'task') return // handled by ProjectTasks autoOpenTaskId
  if (type === 'contract') openEditContract(id as string)
  else if (type === 'invoice') openEditInvoice(id as string)
  else if (type === 'proposal') openEditProposal(id as string)
}, { immediate: true })

// Modal handlers
function openEditProject() {
  showProjectModal.value = true
}

function openCreateContract(projectId: string) {
  contractProjectId.value = projectId
  editingContractId.value = null
  showContractModal.value = true
}

function openEditContract(contractId: string) {
  editingContractId.value = contractId
  showContractModal.value = true
}

function openDeleteContract(contractId: string) {
  deleteLabel.value = 'this contract'
  deleteAction.value = async () => {
    const { deleteContract } = await import('../api/contracts')
    await deleteContract(contractId)
    toast.success('Contract deleted')
    await loadProjects()
  }
  showDeleteModal.value = true
}

function openCreateInvoice(contractId: string) {
  invoiceContractId.value = contractId
  showInvoiceCreateModal.value = true
}

function openEditInvoice(invoiceId: string) {
  editingInvoiceId.value = invoiceId
  showInvoiceEditModal.value = true
}

function openDeleteInvoice(invoiceId: string) {
  deleteLabel.value = 'this invoice'
  deleteAction.value = async () => {
    const { deleteInvoice } = await import('../api/invoices')
    await deleteInvoice(invoiceId)
    toast.success('Invoice deleted')
    await loadProjects()
  }
  showDeleteModal.value = true
}

function openInvoiceActions(invoiceId: string) {
  actionsInvoiceId.value = invoiceId
  showInvoiceActionsModal.value = true
}

function openCreateProposal(projectId: string) {
  proposalProjectId.value = projectId
  editingProposalId.value = null
  showProposalModal.value = true
}

function openEditProposal(proposalId: string) {
  editingProposalId.value = proposalId
  showProposalModal.value = true
}

function openDeleteProposal(proposalId: string) {
  deleteLabel.value = 'this proposal'
  deleteAction.value = async () => {
    const { deleteProposal } = await import('../api/proposals')
    await deleteProposal(proposalId)
    toast.success('Proposal deleted')
    await loadProjects()
  }
  showDeleteModal.value = true
}

function openPromoteProposal(proposalId: string) {
  promoteProposalId.value = proposalId
  showPromoteModal.value = true
}

function showError(msg: string) {
  errorMessage.value = msg
  showErrorModal.value = true
}

async function handleSaved() {
  await loadProjects()
}

// URL sync: when modals close, update URL
watch(showContractModal, (v) => {
  if (!v && routeEntityType.value === 'contract') {
    router.replace(`/projects/${routeProjectNumber.value}?section=contracts`)
  }
})

watch(showInvoiceEditModal, (v) => {
  if (!v && routeEntityType.value === 'invoice') {
    router.replace(`/projects/${routeProjectNumber.value}?section=invoices`)
  }
})

watch(showProposalModal, (v) => {
  if (!v && routeEntityType.value === 'proposal') {
    router.replace(`/projects/${routeProjectNumber.value}?section=proposals`)
  }
})

function onTaskEntityClicked(entityType: string, entityId: string) {
  if (routeProjectNumber.value) {
    router.push(`/projects/${routeProjectNumber.value}/${entityType}s/${entityId}`)
  }
}

function onTaskModalClosed() {
  if (routeEntityType.value === 'task' && routeProjectNumber.value) {
    router.replace(`/projects/${routeProjectNumber.value}`)
  }
}

onMounted(async () => {
  if (allProjects.value.length === 0) {
    await loadProjects()
  }
  projectsLoaded.value = true
})
</script>

<template>
  <div v-if="project" class="project-page">
    <ProjectHeader
      :project="project"
      @edit-project="openEditProject"
    />

    <div class="project-body">
      <ProjectSidebar
        :active-section="activeSection"
        :task-count="taskCount"
        :notes-count="notesCount"
        :total-hours="totalHours"
        :team-count="teamCount"
        :contract-count="project.contracts?.length || 0"
        :invoice-count="project.invoices?.length || 0"
        :proposal-count="project.proposals?.length || 0"
        :folder-href="folderHref"
        @update:active-section="activeSection = $event"
      />

      <div class="project-content">
        <ProjectTasks
          v-if="activeSection === 'tasks'"
          ref="tasksRef"
          :project="project"
          :auto-open-task-id="routeEntityType === 'task' ? routeEntityId : null"
          @refresh-project="loadProjects"
          @entity-clicked="onTaskEntityClicked"
          @task-modal-closed="onTaskModalClosed"
        />

        <ProjectNotes
          v-if="activeSection === 'notes'"
          ref="notesRef"
          :project="project"
        />

        <ProjectTime
          v-if="activeSection === 'time'"
          ref="timeRef"
          :project="project"
        />

        <ProjectTeam
          v-if="activeSection === 'team'"
          ref="teamRef"
          :project="project"
        />

        <ProjectContracts
          v-if="activeSection === 'contracts'"
          :project="project"
          @create-contract="openCreateContract"
          @edit-contract="openEditContract"
          @delete-contract="openDeleteContract"
          @create-invoice="openCreateInvoice"
        />

        <ProjectInvoices
          v-if="activeSection === 'invoices'"
          :project="project"
          @edit-invoice="openEditInvoice"
          @delete-invoice="openDeleteInvoice"
          @invoice-actions="openInvoiceActions"
          @refresh-project="loadProjects"
        />

        <ProjectProposals
          v-if="activeSection === 'proposals'"
          :project="project"
          @create-proposal="openCreateProposal"
          @edit-proposal="openEditProposal"
          @delete-proposal="openDeleteProposal"
          @promote-proposal="openPromoteProposal"
          @refresh-project="loadProjects"
        />
      </div>
    </div>

    <!-- Modals -->
    <ProjectModal
      v-model:visible="showProjectModal"
      :project="project"
      @saved="handleSaved"
      @error="showError"
    />

    <ContractModal
      v-model:visible="showContractModal"
      :project-id="contractProjectId || project.id"
      :contract-id="editingContractId"
      @saved="handleSaved"
      @error="showError"
    />

    <InvoiceCreateModal
      v-model:visible="showInvoiceCreateModal"
      :contract-id="invoiceContractId"
      @saved="handleSaved"
      @error="showError"
    />

    <InvoiceEditModal
      v-model:visible="showInvoiceEditModal"
      :invoice-id="editingInvoiceId"
      @saved="handleSaved"
      @error="showError"
    />

    <InvoiceActionsModal
      v-model:visible="showInvoiceActionsModal"
      :invoice-id="actionsInvoiceId"
      @saved="handleSaved"
      @error="showError"
    />

    <ProposalModal
      v-model:visible="showProposalModal"
      :project-id="proposalProjectId || project.id"
      :proposal-id="editingProposalId"
      @saved="handleSaved"
      @error="showError"
    />

    <PromoteProposalModal
      v-model:visible="showPromoteModal"
      :proposal-id="promoteProposalId"
      @saved="handleSaved"
      @error="showError"
    />

    <DeleteConfirmModal
      v-model:visible="showDeleteModal"
      :label="deleteLabel"
      :action="deleteAction ?? (async () => {})"
      @error="showError"
    />

    <ErrorModal
      v-model:visible="showErrorModal"
      :message="errorMessage"
    />
  </div>

  <div v-else class="project-loading">
    <p>Loading project...</p>
  </div>
</template>

<style scoped>
.project-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.project-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.project-content {
  flex: 1;
  padding: 1.25rem;
  overflow-y: auto;
}

.project-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--p-text-muted-color);
}
</style>
