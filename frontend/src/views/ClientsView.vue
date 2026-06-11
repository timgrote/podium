<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Client, Contact } from '../types'
import { getClients } from '../api/clients'
import { getContacts, createContact, deleteContact, importContacts } from '../api/contacts'
import type { VcfImportResult } from '../api/contacts'
import { useClients } from '../composables/useClients'
import { useToast } from '../composables/useToast'
import ClientModal from '../components/modals/ClientModal.vue'
import ContactModal from '../components/modals/ContactModal.vue'

const toast = useToast()
const clients = ref<Client[]>([])
const contacts = ref<Contact[]>([])
const loadingClients = ref(true)
const loadingContacts = ref(true)
const selectedClientId = ref('')
const searchQuery = ref('')
const companySearch = ref('')

const activeTab = ref<'contacts' | 'companies'>('contacts')

const { load: reloadSharedClients } = useClients()

// Client modal
const showClientModal = ref(false)
const editingClientId = ref<string | null>(null)

// Contact modal
const showContactModal = ref(false)
const editingContactId = ref<string | null>(null)

const showAddContact = ref(false)
const addingContact = ref(false)
const newContact = ref({ name: '', email: '', phone: '', role: '' })

// VCF import
const importFile = ref<File | null>(null)
const importPreview = ref<VcfImportResult | null>(null)
const importing = ref(false)
const committing = ref(false)
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const filteredContacts = computed(() => {
  let list = contacts.value
  if (selectedClientId.value) {
    list = list.filter(c => c.client_id === selectedClientId.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(c =>
      c.name.toLowerCase().includes(q) ||
      (c.email && c.email.toLowerCase().includes(q)) ||
      (c.role && c.role.toLowerCase().includes(q))
    )
  }
  return list
})

const filteredClients = computed(() => {
  const q = companySearch.value.trim().toLowerCase()
  if (!q) return clients.value
  return clients.value.filter(c =>
    c.name.toLowerCase().includes(q) ||
    (c.accounting_email && c.accounting_email.toLowerCase().includes(q)) ||
    (c.phone && c.phone.toLowerCase().includes(q))
  )
})

function clientName(clientId: string | null): string {
  if (!clientId) return '—'
  const c = clients.value.find(cl => cl.id === clientId)
  return c ? c.name : '—'
}

async function loadClients() {
  try {
    clients.value = await getClients()
  } finally {
    loadingClients.value = false
  }
}

async function loadContacts() {
  try {
    contacts.value = await getContacts()
  } finally {
    loadingContacts.value = false
  }
}

function openCreateClient() {
  editingClientId.value = null
  showClientModal.value = true
}

function openEditClient(clientId: string) {
  editingClientId.value = clientId
  showClientModal.value = true
}

function openEditContact(contactId: string) {
  editingContactId.value = contactId
  showContactModal.value = true
}

async function removeContact(ct: Contact) {
  try {
    await deleteContact(ct.id)
    contacts.value = contacts.value.filter(c => c.id !== ct.id)
    toast.success('Contact removed')
  } catch {
    toast.error('Failed to remove contact')
  }
}

async function addContact() {
  if (!newContact.value.name.trim()) return
  addingContact.value = true
  try {
    const created = await createContact({
      name: newContact.value.name.trim(),
      email: newContact.value.email.trim() || undefined,
      phone: newContact.value.phone.trim() || undefined,
      role: newContact.value.role.trim() || undefined,
      client_id: selectedClientId.value || undefined,
    })
    contacts.value.push(created)
    newContact.value = { name: '', email: '', phone: '', role: '' }
    showAddContact.value = false
    toast.success('Contact added')
  } catch {
    toast.error('Failed to add contact')
  } finally {
    addingContact.value = false
  }
}

// --- VCF import ---

async function handleFile(file: File) {
  if (!file.name.toLowerCase().endsWith('.vcf')) {
    toast.error('Please drop a .vcf file')
    return
  }
  importFile.value = file
  importing.value = true
  importPreview.value = null
  try {
    importPreview.value = await importContacts(file, false)
  } catch (e: any) {
    toast.error(e?.detail || 'Could not read that file')
    importFile.value = null
  } finally {
    importing.value = false
  }
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
}

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) handleFile(file)
  if (fileInput.value) fileInput.value.value = ''
}

function cancelImport() {
  importFile.value = null
  importPreview.value = null
}

async function confirmImport() {
  if (!importFile.value) return
  committing.value = true
  try {
    const result = await importContacts(importFile.value, true)
    const { create, update, new_companies } = result.summary
    const parts = []
    if (create) parts.push(`${create} added`)
    if (update) parts.push(`${update} updated`)
    if (new_companies) parts.push(`${new_companies} compan${new_companies !== 1 ? 'ies' : 'y'} created`)
    toast.success(`Import complete: ${parts.join(', ') || 'no changes'}`)
    cancelImport()
    await Promise.all([loadContacts(), loadClients(), reloadSharedClients()])
  } catch (e: any) {
    toast.error(e?.detail || 'Import failed')
  } finally {
    committing.value = false
  }
}

async function handleClientSaved() {
  await Promise.all([loadClients(), loadContacts(), reloadSharedClients()])
}

async function handleContactSaved() {
  await loadContacts()
}

onMounted(async () => {
  await Promise.all([loadClients(), loadContacts()])
})
</script>

<template>
  <div class="clients-page">
    <div class="page-header">
      <h1>Companies &amp; Contacts</h1>
    </div>

    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'contacts' }" @click="activeTab = 'contacts'">
        Contacts <span v-if="contacts.length" class="tab-count">({{ contacts.length }})</span>
      </button>
      <button class="tab" :class="{ active: activeTab === 'companies' }" @click="activeTab = 'companies'">
        Companies <span v-if="clients.length" class="tab-count">({{ clients.length }})</span>
      </button>
    </div>

    <!-- Contacts Tab -->
    <section v-show="activeTab === 'contacts'" class="tab-content">
      <div class="section-header">
        <h2>Contacts</h2>
        <div class="header-actions">
          <button class="btn-add" @click="fileInput?.click()">
            <i class="pi pi-upload" />
            Import VCF
          </button>
          <button class="btn-add" @click="showAddContact = !showAddContact">
            <i :class="showAddContact ? 'pi pi-times' : 'pi pi-plus'" />
            {{ showAddContact ? 'Cancel' : 'Add Contact' }}
          </button>
        </div>
      </div>

      <input ref="fileInput" type="file" accept=".vcf,text/vcard" class="hidden-file" @change="onFileChange" />

      <!-- Drop zone -->
      <div
        class="drop-zone"
        :class="{ over: dragOver }"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
        @click="fileInput?.click()"
      >
        <i class="pi pi-id-card" />
        <span v-if="importing">Reading file…</span>
        <span v-else>Drop a <strong>.vcf</strong> file here, or click to browse</span>
      </div>

      <!-- Import preview -->
      <div v-if="importPreview" class="import-preview">
        <div class="import-preview-head">
          <span>
            <strong>{{ importPreview.summary.create }}</strong> new,
            <strong>{{ importPreview.summary.update }}</strong> to update
            ({{ importPreview.summary.total }} in file)<template v-if="importPreview.summary.new_companies">,
            <strong>{{ importPreview.summary.new_companies }}</strong> new compan{{ importPreview.summary.new_companies !== 1 ? 'ies' : 'y' }}</template>
          </span>
          <div class="header-actions">
            <button class="btn btn-sm" @click="cancelImport">Cancel</button>
            <button class="btn btn-sm btn-primary" :disabled="committing" @click="confirmImport">
              {{ committing ? 'Importing…' : `Import ${importPreview.summary.total}` }}
            </button>
          </div>
        </div>
        <table class="contacts-table">
          <thead>
            <tr>
              <th></th><th>Name</th><th>Email</th><th>Phone</th><th>Role</th><th>Company</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(e, i) in importPreview.contacts" :key="i">
              <td>
                <span class="action-badge" :class="e.action">{{ e.action === 'create' ? 'New' : 'Update' }}</span>
              </td>
              <td class="cell-name">{{ e.name }}</td>
              <td>{{ e.email || '' }}</td>
              <td>{{ e.phone || '' }}</td>
              <td>{{ e.role || '' }}</td>
              <td>
                {{ e.company_name || (e.client_id ? clientName(e.client_id) : '—') }}
                <span v-if="e.company_new" class="action-badge create">new</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Filters -->
      <div class="filters">
        <select v-model="selectedClientId" class="filter-select">
          <option value="">All Companies</option>
          <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <input
          v-model="searchQuery"
          type="text"
          class="filter-input"
          placeholder="Search contacts..."
        />
        <span class="result-count">{{ filteredContacts.length }} contact{{ filteredContacts.length !== 1 ? 's' : '' }}</span>
      </div>

      <!-- Add Contact Form -->
      <div v-if="showAddContact" class="add-contact-bar">
        <input v-model="newContact.name" type="text" placeholder="Name *" />
        <input v-model="newContact.email" type="email" placeholder="Email" />
        <input v-model="newContact.phone" type="text" placeholder="Phone" />
        <input v-model="newContact.role" type="text" placeholder="Role" />
        <button
          class="btn btn-sm btn-primary"
          :disabled="!newContact.name.trim() || addingContact"
          @click="addContact"
        >
          Add
        </button>
      </div>

      <div v-if="loadingContacts" class="loading">Loading contacts...</div>
      <div v-else-if="filteredContacts.length === 0" class="empty-state">No contacts found</div>
      <table v-else class="contacts-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Role</th>
            <th>Company</th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ct in filteredContacts" :key="ct.id">
            <td class="cell-name cell-clickable" @click="openEditContact(ct.id)">{{ ct.name }}</td>
            <td>{{ ct.email || '' }}</td>
            <td>{{ ct.phone || '' }}</td>
            <td><span v-if="ct.role" class="role-badge">{{ ct.role }}</span></td>
            <td class="cell-client" @click.stop="ct.client_id && openEditClient(ct.client_id)">{{ clientName(ct.client_id) }}</td>
            <td class="col-actions">
              <button class="btn-icon" title="Edit" @click="openEditContact(ct.id)"><i class="pi pi-pencil" /></button>
              <button class="btn-icon btn-icon-danger" title="Remove" @click="removeContact(ct)"><i class="pi pi-trash" /></button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Companies Tab -->
    <section v-show="activeTab === 'companies'" class="tab-content">
      <div class="section-header">
        <h2>Companies</h2>
        <button class="btn-add" @click="openCreateClient">
          <i class="pi pi-plus" />
          New Company
        </button>
      </div>

      <div class="filters">
        <input
          v-model="companySearch"
          type="text"
          class="filter-input"
          placeholder="Search companies..."
        />
        <span class="result-count">{{ filteredClients.length }} compan{{ filteredClients.length !== 1 ? 'ies' : 'y' }}</span>
      </div>

      <div v-if="loadingClients" class="loading">Loading companies...</div>
      <div v-else-if="filteredClients.length === 0" class="empty-state">No companies found</div>
      <div v-else class="client-grid">
        <div
          v-for="c in filteredClients"
          :key="c.id"
          class="client-card"
          @click="openEditClient(c.id)"
        >
          <div class="client-card-header">
            <span class="client-company">{{ c.name }}</span>
          </div>
          <div class="client-card-details">
            <span v-if="c.accounting_email" class="detail"><i class="pi pi-envelope" /> {{ c.accounting_email }}</span>
            <span v-if="c.phone" class="detail"><i class="pi pi-phone" /> {{ c.phone }}</span>
          </div>
        </div>
      </div>
    </section>

    <ClientModal
      v-model:visible="showClientModal"
      :client-id="editingClientId"
      @saved="handleClientSaved"
      @error="(msg: string) => toast.error(msg)"
    />

    <ContactModal
      v-model:visible="showContactModal"
      :contact-id="editingContactId"
      @saved="handleContactSaved"
      @error="(msg: string) => toast.error(msg)"
    />
  </div>
</template>

<style scoped>
.clients-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 1rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--p-content-border-color);
  margin-bottom: 1.5rem;
}

.tab {
  padding: 0.5rem 1rem;
  background: none;
  border: none;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
}

.tab.active {
  color: var(--p-text-color);
  border-bottom-color: var(--p-primary-color);
}

.tab-count {
  color: var(--p-text-muted-color);
  font-weight: 400;
}

.tab-content {
  display: block;
}

.section h2 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 0.75rem 0;
  color: var(--p-text-color);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.section-header h2 { margin: 0; font-size: 1rem; font-weight: 600; }

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: var(--p-text-muted-color);
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

/* Client Grid */
.client-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.75rem;
}

.client-card {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: all 0.15s;
}

.client-card:hover {
  border-color: var(--p-primary-color);
  background: var(--p-content-hover-background);
}

.client-card-header {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  margin-bottom: 0.5rem;
}

.client-company {
  font-weight: 600;
  font-size: 0.875rem;
}

.client-card-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.detail .pi {
  font-size: 0.625rem;
}

/* Filters */
.filters {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.filter-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  min-width: 180px;
}

.filter-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  flex: 1;
}

.result-count {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

/* VCF drop zone */
.hidden-file { display: none; }

.drop-zone {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  margin-bottom: 0.75rem;
  border: 1.5px dashed var(--p-content-border-color);
  border-radius: 0.5rem;
  color: var(--p-text-muted-color);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all 0.15s;
}

.drop-zone:hover, .drop-zone.over {
  border-color: var(--p-primary-color);
  background: var(--p-content-hover-background);
  color: var(--p-text-color);
}

.drop-zone .pi { font-size: 1rem; }

/* Import preview */
.import-preview {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 0.75rem;
  margin-bottom: 1rem;
  background: var(--p-content-hover-background);
}

.import-preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  font-size: 0.8125rem;
}

.action-badge {
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
}

.action-badge.create { background: var(--p-green-100, #dcfce7); color: var(--p-green-700, #15803d); }
.action-badge.update { background: var(--p-amber-100, #fef3c7); color: var(--p-amber-700, #b45309); }

/* Add Contact Bar */
.add-contact-bar {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr auto;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  padding: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-hover-background);
}

.add-contact-bar input {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
}

/* Contacts Table */
.contacts-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.contacts-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid var(--p-content-border-color);
}

.contacts-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
  color: var(--p-text-color);
}

.contacts-table tr:hover td {
  background: var(--p-content-hover-background);
}

.cell-name { font-weight: 500; }
.cell-clickable { cursor: pointer; }
.cell-clickable:hover { color: var(--p-primary-color); }
.cell-client { cursor: pointer; color: var(--p-primary-color); }
.cell-client:hover { text-decoration: underline; }

.col-actions {
  width: 80px;
  text-align: right;
}

.role-badge {
  font-size: 0.6875rem;
  background: var(--p-content-hover-background);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  color: var(--p-text-muted-color);
}

.btn-add {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.75rem;
  cursor: pointer;
}

.btn-add:hover { background: var(--p-content-hover-background); }
.btn-add .pi { font-size: 0.625rem; }

.btn-icon { background: none; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; cursor: pointer; padding: 0.25rem 0.5rem; color: var(--p-text-muted-color); font-size: 0.75rem; }
.btn-icon:hover { background: var(--p-content-hover-background); }
.btn-icon-danger:hover { color: var(--p-red-600); border-color: var(--p-red-300); }

.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; color: var(--p-text-color); }
.btn-sm { padding: 0.375rem 0.625rem; font-size: 0.8125rem; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
