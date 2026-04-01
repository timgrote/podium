<script setup lang="ts">
import type { ProjectDetail } from '../../types'
import ProjectProposals from './ProjectProposals.vue'
import ProjectContracts from './ProjectContracts.vue'
import ProjectInvoices from './ProjectInvoices.vue'

defineProps<{
  project: ProjectDetail
}>()

const emit = defineEmits<{
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
  refreshProject: []
}>()
</script>

<template>
  <div class="financial-sections">
    <ProjectInvoices
      :project="project"
      @edit-invoice="emit('editInvoice', $event)"
      @delete-invoice="emit('deleteInvoice', $event)"
      @invoice-actions="emit('invoiceActions', $event)"
      @create-invoice="emit('createInvoice', $event)"
      @refresh-project="emit('refreshProject')"
    />

    <ProjectContracts
      :project="project"
      @create-contract="emit('createContract', $event)"
      @edit-contract="emit('editContract', $event)"
      @delete-contract="emit('deleteContract', $event)"
      @create-invoice="emit('createInvoice', $event)"
    />

    <ProjectProposals
      :project="project"
      @create-proposal="emit('createProposal', $event)"
      @edit-proposal="emit('editProposal', $event)"
      @delete-proposal="emit('deleteProposal', $event)"
      @promote-proposal="emit('promoteProposal', $event)"
      @refresh-project="emit('refreshProject')"
    />
  </div>
</template>

<style scoped>
.financial-sections {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
</style>
