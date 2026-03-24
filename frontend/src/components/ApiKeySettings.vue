<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import { getApiKeys, createApiKey, deleteApiKey } from '../api/auth'
import type { ApiKey, ApiKeyWithRaw } from '../api/auth'
import { useToast } from '../composables/useToast'

const toast = useToast()

const keys = ref<ApiKey[]>([])
const loading = ref(false)

const showCreateDialog = ref(false)
const newKeyName = ref('')
const creating = ref(false)

const newlyCreatedKey = ref<ApiKeyWithRaw | null>(null)
const showRevealDialog = ref(false)

const deleteTarget = ref<ApiKey | null>(null)
const showDeleteDialog = ref(false)
const deleting = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    keys.value = await getApiKeys()
  } catch (e) {
    toast.error(String(e))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  newKeyName.value = ''
  showCreateDialog.value = true
}

async function submitCreate() {
  if (!newKeyName.value.trim()) return
  creating.value = true
  try {
    const created = await createApiKey(newKeyName.value.trim())
    newlyCreatedKey.value = created
    showCreateDialog.value = false
    showRevealDialog.value = true
    await load()
  } catch (e) {
    toast.error(String(e))
  } finally {
    creating.value = false
  }
}

function closeReveal() {
  showRevealDialog.value = false
  newlyCreatedKey.value = null
}

async function copyKey() {
  if (!newlyCreatedKey.value) return
  try {
    await navigator.clipboard.writeText(newlyCreatedKey.value.raw_key)
    toast.success('API key copied to clipboard')
  } catch {
    toast.error('Failed to copy to clipboard')
  }
}

function openDelete(key: ApiKey) {
  deleteTarget.value = key
  showDeleteDialog.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteApiKey(deleteTarget.value.id)
    showDeleteDialog.value = false
    deleteTarget.value = null
    await load()
    toast.success('API key deleted')
  } catch (e) {
    toast.error(String(e))
  } finally {
    deleting.value = false
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
</script>

<template>
  <div class="api-key-settings">
    <div class="section-header">
      <div>
        <h2>API Keys</h2>
        <p class="section-desc">Use API keys to authenticate programmatic access to this account.</p>
      </div>
      <button class="btn btn-primary" @click="openCreate">
        <i class="pi pi-plus" />
        New Key
      </button>
    </div>

    <div v-if="loading" class="empty-state">Loading...</div>
    <div v-else-if="keys.length === 0" class="empty-state">No API keys yet.</div>
    <table v-else class="keys-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Created</th>
          <th>Last Used</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="key in keys" :key="key.id">
          <td class="key-name">{{ key.name }}</td>
          <td>{{ formatDate(key.created_at) }}</td>
          <td>{{ formatDate(key.last_used_at) }}</td>
          <td class="actions-cell">
            <button class="btn btn-danger-ghost" @click="openDelete(key)">
              <i class="pi pi-trash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Create dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      header="Create API Key"
      :modal="true"
      :style="{ width: '420px' }"
    >
      <div class="field">
        <label for="key-name">Key Name</label>
        <input
          id="key-name"
          v-model="newKeyName"
          type="text"
          placeholder="e.g. n8n integration"
          @keyup.enter="submitCreate"
        />
      </div>
      <template #footer>
        <button class="btn" @click="showCreateDialog = false">Cancel</button>
        <button
          class="btn btn-primary"
          :disabled="creating || !newKeyName.trim()"
          @click="submitCreate"
        >
          {{ creating ? 'Creating...' : 'Create' }}
        </button>
      </template>
    </Dialog>

    <!-- Reveal dialog — raw key shown only once -->
    <Dialog
      v-model:visible="showRevealDialog"
      header="API Key Created"
      :modal="true"
      :closable="false"
      :style="{ width: '520px' }"
    >
      <p class="reveal-intro">
        Copy your new API key now. <strong>It will not be shown again.</strong>
      </p>
      <div class="key-display">
        <code class="raw-key">{{ newlyCreatedKey?.raw_key }}</code>
        <button class="btn btn-copy" @click="copyKey">
          <i class="pi pi-copy" />
          Copy
        </button>
      </div>
      <template #footer>
        <button class="btn btn-primary" @click="closeReveal">Done</button>
      </template>
    </Dialog>

    <!-- Delete confirm dialog -->
    <Dialog
      v-model:visible="showDeleteDialog"
      header="Delete API Key"
      :modal="true"
      :style="{ width: '400px' }"
    >
      <p>Delete key <strong>{{ deleteTarget?.name }}</strong>?</p>
      <p class="warning">Any integrations using this key will stop working immediately.</p>
      <template #footer>
        <button class="btn" @click="showDeleteDialog = false">Cancel</button>
        <button class="btn btn-danger" :disabled="deleting" @click="confirmDelete">
          {{ deleting ? 'Deleting...' : 'Delete' }}
        </button>
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.api-key-settings {
  margin-top: 2rem;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.section-header h2 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 0.25rem;
  color: var(--p-text-color);
}

.section-desc {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  margin: 0;
}

.empty-state {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  padding: 1rem 0;
}

.keys-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.keys-table th {
  text-align: left;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.keys-table td {
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
  color: var(--p-text-color);
}

.key-name {
  font-weight: 500;
}

.actions-cell {
  text-align: right;
  width: 3rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.field label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.field input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
}

.reveal-intro {
  font-size: 0.875rem;
  margin: 0 0 0.75rem;
  color: var(--p-text-color);
}

.key-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--p-surface-100, #f4f4f5);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
}

.raw-key {
  flex: 1;
  font-family: monospace;
  font-size: 0.8125rem;
  word-break: break-all;
  color: var(--p-text-color);
  background: none;
}

.btn {
  padding: 0.5rem 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.875rem;
  margin-left: 0.5rem;
  color: var(--p-text-color);
}

.btn-primary {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.btn-primary:hover {
  background: var(--p-primary-hover-color);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-copy {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  margin-left: 0;
  flex-shrink: 0;
  font-size: 0.8125rem;
}

.btn-danger {
  background: var(--p-red-600);
  color: #fff;
  border-color: var(--p-red-600);
}

.btn-danger:hover {
  background: var(--p-red-700);
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger-ghost {
  background: none;
  border: none;
  color: var(--p-text-muted-color);
  padding: 0.25rem 0.5rem;
  margin-left: 0;
  cursor: pointer;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.btn-danger-ghost:hover {
  background: var(--p-red-100, rgba(220, 38, 38, 0.1));
  color: var(--p-red-600);
}

.warning {
  color: var(--p-red-600);
  font-size: 0.8125rem;
  margin: 0.25rem 0 0;
}

p {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
}
</style>
