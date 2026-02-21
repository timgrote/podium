<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { ProjectSummary } from '../types'
import { useProjects } from '../composables/useProjects'
import { useClients } from '../composables/useClients'
import { useToast } from '../composables/useToast'
import StatsBar from '../components/dashboard/StatsBar.vue'
import ProjectList from '../components/dashboard/ProjectList.vue'
import ProjectModal from '../components/modals/ProjectModal.vue'
import ContractModal from '../components/modals/ContractModal.vue'
import InvoiceCreateModal from '../components/modals/InvoiceCreateModal.vue'
import InvoiceEditModal from '../components/modals/InvoiceEditModal.vue'
import InvoiceActionsModal from '../components/modals/InvoiceActionsModal.vue'
import ProposalModal from '../components/modals/ProposalModal.vue'
import PromoteProposalModal from '../components/modals/PromoteProposalModal.vue'
import DeleteConfirmModal from '../components/modals/DeleteConfirmModal.vue'
import CompanySettingsModal from '../components/modals/CompanySettingsModal.vue'
import NotesModal from '../components/modals/NotesModal.vue'
import ErrorModal from '../components/modals/ErrorModal.vue'

const {
  filtered,
  stats,
  searchQuery,
  statusFilter,
  pmFilter,
  clientFilter,
  uniqueStatuses,
  uniquePMs,
  load: loadProjects,
} = useProjects()
const { load: loadClients } = useClients()
const toast = useToast()

// Modal state
const showProjectModal = ref(false)
const editingProject = ref<ProjectSummary | null>(null)
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
const showSettingsModal = ref(false)
const showNotesModal = ref(false)
const notesProjectId = ref('')
const showErrorModal = ref(false)
const errorMessage = ref('')

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

function openNotes(projectId: string) {
  notesProjectId.value = projectId
  showNotesModal.value = true
}

function showError(msg: string) {
  errorMessage.value = msg
  showErrorModal.value = true
}

async function handleSaved() {
  await loadProjects()
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadClients()])
})
</script>

<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1>Dashboard</h1>
      <button class="btn-settings" @click="showSettingsModal = true">
        <i class="pi pi-cog" />
      </button>
    </div>

    <StatsBar v-bind="stats" />

    <ProjectList
      :projects="filtered"
      :search-query="searchQuery"
      :status-filter="statusFilter"
      :pm-filter="pmFilter"
      :client-filter="clientFilter"
      :unique-statuses="uniqueStatuses"
      :unique-p-ms="uniquePMs"
      @update:search-query="searchQuery = $event"
      @update:status-filter="statusFilter = $event"
      @update:pm-filter="pmFilter = $event"
      @update:client-filter="clientFilter = $event"
      @create-project="openCreateProject"
      @edit-project="openEditProject"
      @delete-project="openDeleteProject"
      @create-contract="openCreateContract"
      @edit-contract="openEditContract"
      @delete-contract="openDeleteContract"
      @create-invoice="openCreateInvoice"
      @edit-invoice="openEditInvoice"
      @delete-invoice="openDeleteInvoice"
      @invoice-actions="openInvoiceActions"
      @create-proposal="openCreateProposal"
      @edit-proposal="openEditProposal"
      @delete-proposal="openDeleteProposal"
      @promote-proposal="openPromoteProposal"
      @view-notes="openNotes"
    />

    <!-- Modals -->
    <ProjectModal
      v-model:visible="showProjectModal"
      :project="editingProject"
      @saved="handleSaved"
      @error="showError"
    />

    <ContractModal
      v-model:visible="showContractModal"
      :project-id="contractProjectId"
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
      :project-id="proposalProjectId"
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
      :action="deleteAction!"
      @error="showError"
    />

    <CompanySettingsModal
      v-model:visible="showSettingsModal"
      @error="showError"
    />

    <NotesModal
      v-model:visible="showNotesModal"
      :project-id="notesProjectId"
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
