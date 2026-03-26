<script setup lang="ts">
import { ref } from 'vue'
import type { ProjectSummary } from '../../types'
import { generateDoc, exportProposalPdf, sendProposal } from '../../api/proposals'
import { useToast } from '../../composables/useToast'

const props = defineProps<{
  project: ProjectSummary
}>()

const emit = defineEmits<{
  createProposal: [projectId: string]
  editProposal: [proposalId: string]
  deleteProposal: [proposalId: string]
  promoteProposal: [proposalId: string]
  refreshProject: []
}>()

const toast = useToast()
const proposalBusy = ref<Record<string, string>>({})

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', minimumFractionDigits: 2,
  }).format(value)
}

async function genProposalDoc(proposalId: string) {
  proposalBusy.value[proposalId] = 'gen'
  try {
    await generateDoc(proposalId)
    toast.success('Google Doc generated')
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  } finally {
    delete proposalBusy.value[proposalId]
  }
}

async function exportPdf(proposalId: string) {
  proposalBusy.value[proposalId] = 'pdf'
  try {
    await exportProposalPdf(proposalId)
    toast.success('PDF exported')
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  } finally {
    delete proposalBusy.value[proposalId]
  }
}

async function sendProposalEmail(proposalId: string) {
  proposalBusy.value[proposalId] = 'send'
  try {
    const result = await sendProposal(proposalId)
    toast.success(`Proposal sent to ${result.sent_to?.join(', ') || 'client'}`)
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  } finally {
    delete proposalBusy.value[proposalId]
  }
}

function hasGoogleDoc(proposal: { data_path: string | null }): boolean {
  return !!proposal.data_path && proposal.data_path.includes('google.com')
}
</script>

<template>
  <div class="section">
    <div class="section-header">
      <h4>Proposals</h4>
      <button class="btn btn-sm btn-primary" @click="emit('createProposal', project.id)">
        <i class="pi pi-plus" /> Add
      </button>
    </div>
    <div v-if="project.proposals.length === 0" class="empty">No proposals</div>
    <div v-for="proposal in project.proposals" :key="proposal.id" class="sub-card">
      <div class="sub-card-header">
        <span class="sub-card-title">{{ formatCurrency(proposal.total_fee) }}</span>
        <span
          class="status-pill"
          :class="{ sent: proposal.status === 'sent', accepted: proposal.status === 'accepted' }"
        >
          {{ proposal.status }}
        </span>
        <a
          v-if="hasGoogleDoc(proposal)"
          class="doc-link"
          :href="proposal.data_path!"
          target="_blank"
          title="Open Google Doc"
        >
          <i class="pi pi-file-edit" /> Google Doc
        </a>
        <div class="sub-card-actions">
          <button
            v-if="!hasGoogleDoc(proposal)"
            class="btn-icon"
            title="Generate Google Doc"
            :disabled="!!proposalBusy[proposal.id]"
            @click="genProposalDoc(proposal.id)"
          >
            <i class="pi" :class="proposalBusy[proposal.id] === 'gen' ? 'pi-spin pi-spinner' : 'pi-file'" />
          </button>
          <a
            v-if="hasGoogleDoc(proposal)"
            class="btn-icon"
            title="Open Google Doc"
            :href="proposal.data_path!"
            target="_blank"
          >
            <i class="pi pi-external-link" />
          </a>
          <button
            v-if="hasGoogleDoc(proposal) && !proposal.pdf_path"
            class="btn-icon"
            title="Export PDF"
            :disabled="!!proposalBusy[proposal.id]"
            @click="exportPdf(proposal.id)"
          >
            <i class="pi" :class="proposalBusy[proposal.id] === 'pdf' ? 'pi-spin pi-spinner' : 'pi-file-pdf'" />
          </button>
          <a
            v-if="proposal.pdf_path"
            class="btn-icon"
            title="View PDF"
            :href="proposal.pdf_path"
            target="_blank"
          >
            <i class="pi pi-file-pdf" />
          </a>
          <button
            v-if="hasGoogleDoc(proposal) && proposal.status !== 'sent' && proposal.status !== 'accepted'"
            class="btn-icon"
            title="Send to Client"
            :disabled="!!proposalBusy[proposal.id]"
            @click="sendProposalEmail(proposal.id)"
          >
            <i class="pi" :class="proposalBusy[proposal.id] === 'send' ? 'pi-spin pi-spinner' : 'pi-send'" />
          </button>
          <button
            v-if="proposal.status === 'accepted'"
            class="btn-icon"
            title="Promote to Contract"
            @click="emit('promoteProposal', proposal.id)"
          >
            <i class="pi pi-arrow-up" />
          </button>
          <button class="btn-icon" title="Edit" @click="emit('editProposal', proposal.id)">
            <i class="pi pi-pencil" />
          </button>
          <button class="btn-icon" title="Delete" @click="emit('deleteProposal', proposal.id)">
            <i class="pi pi-trash" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
.section-header h4 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
}
.sub-card {
  background: var(--p-content-hover-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
}
.sub-card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.sub-card-title { font-weight: 600; font-size: 0.875rem; }
.sub-card-amount { font-weight: 500; font-size: 0.875rem; color: var(--p-text-muted-color); }
.sub-card-date { font-size: 0.75rem; color: var(--p-text-muted-color); }
.sub-card-actions { margin-left: auto; display: flex; gap: 0.25rem; }
.status-pill {
  font-size: 0.625rem; text-transform: uppercase; letter-spacing: 0.05em;
  padding: 0.125rem 0.5rem; border-radius: 9999px;
  background: var(--p-content-hover-background); color: var(--p-text-muted-color); font-weight: 600;
}
.status-pill.sent { background: var(--p-blue-100); color: var(--p-blue-700); }
.status-pill.paid, .status-pill.accepted { background: var(--p-green-100); color: var(--p-green-700); }
.btn-icon {
  background: none; border: none; cursor: pointer; padding: 0.25rem;
  color: var(--p-text-muted-color); border-radius: 0.25rem; font-size: 0.875rem;
}
.btn-icon-green { color: var(--p-green-600); }
.btn-icon-green:hover { color: var(--p-green-700); }
.btn-icon:hover { background: var(--p-content-hover-background); color: var(--p-text-color); }
.btn { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.375rem 0.75rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.75rem; font-weight: 500; color: var(--p-text-color); }
.btn:hover { background: var(--p-content-hover-background); }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.empty { font-size: 0.8125rem; color: var(--p-text-muted-color); font-style: italic; }
.doc-link {
  font-size: 0.75rem; color: var(--p-primary-color); text-decoration: none;
  display: inline-flex; align-items: center; gap: 0.25rem;
  margin-left: auto; white-space: nowrap;
}
.doc-link:hover { text-decoration: underline; }
</style>
