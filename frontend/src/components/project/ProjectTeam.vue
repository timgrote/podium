<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { ProjectSummary, ProjectContact, Contact } from '../../types'
import { getProjectContacts, addProjectContact, removeProjectContact } from '../../api/projects'
import { getContacts, createContact } from '../../api/contacts'
import { useToast } from '../../composables/useToast'

const props = defineProps<{
  project: ProjectSummary
}>()

const toast = useToast()

const teamContacts = ref<ProjectContact[]>([])
const teamLoading = ref(false)
const showAddContact = ref(false)
const allContacts = ref<Contact[]>([])
const addContactId = ref('')
const addContactRole = ref('')
const addContactSaving = ref(false)
const showNewContactInline = ref(false)
const newContactName = ref('')
const newContactEmail = ref('')
const newContactRole = ref('')
const creatingNewContact = ref(false)

const ROLE_SUGGESTIONS = [
  'Project Manager',
  'Landscape Architect',
  'Civil Engineer',
  'Electrical Engineer',
  'Mechanical Engineer',
  'Structural Engineer',
  'Surveyor',
  'Environmental',
  'Reviewer',
]

const availableContacts = computed(() => {
  const linked = new Set(teamContacts.value.map(c => c.contact_id))
  return allContacts.value.filter(c => !linked.has(c.id))
})

watch(() => props.project.id, async () => {
  await loadTeam()
}, { immediate: true })

async function loadTeam() {
  teamLoading.value = true
  try {
    teamContacts.value = await getProjectContacts(props.project.id)
  } catch (e) {
    console.error('Failed to load team:', e)
  } finally {
    teamLoading.value = false
  }
}

async function openAddContact() {
  showAddContact.value = true
  addContactId.value = ''
  addContactRole.value = ''
  showNewContactInline.value = false
  try {
    allContacts.value = await getContacts(props.project.client_id || undefined)
  } catch (e) {
    console.error('Failed to load contacts:', e)
  }
}

async function submitAddContact() {
  if (!addContactId.value) return
  addContactSaving.value = true
  try {
    await addProjectContact(props.project.id, {
      contact_id: addContactId.value,
      role: addContactRole.value || undefined,
    })
    showAddContact.value = false
    toast.success('Contact added to team')
    await loadTeam()
  } catch (e) {
    toast.error(String(e))
  } finally {
    addContactSaving.value = false
  }
}

async function submitNewTeamContact() {
  if (!newContactName.value.trim()) return
  creatingNewContact.value = true
  try {
    const contact = await createContact({
      name: newContactName.value.trim(),
      email: newContactEmail.value.trim() || undefined,
      role: newContactRole.value || undefined,
      client_id: props.project.client_id || undefined,
    })
    await addProjectContact(props.project.id, {
      contact_id: contact.id,
      role: newContactRole.value || undefined,
    })
    showNewContactInline.value = false
    showAddContact.value = false
    newContactName.value = ''
    newContactEmail.value = ''
    newContactRole.value = ''
    toast.success('Contact created and added to team')
    await loadTeam()
  } catch (e) {
    toast.error(String(e))
  } finally {
    creatingNewContact.value = false
  }
}

async function removeTeamContact(contactId: string) {
  try {
    await removeProjectContact(props.project.id, contactId)
    toast.success('Contact removed from team')
    await loadTeam()
  } catch (e) {
    toast.error(String(e))
  }
}

defineExpose({ teamCount: computed(() => teamContacts.value.length) })
</script>

<template>
  <div class="section">
    <div class="section-header">
      <h4>Project Team</h4>
      <button class="btn-icon" :title="showAddContact ? 'Cancel' : 'Add contact'" @click="showAddContact ? (showAddContact = false) : openAddContact()">
        <i class="pi" :class="showAddContact ? 'pi-times' : 'pi-plus'" />
      </button>
    </div>

    <!-- Add contact form -->
    <div v-if="showAddContact" class="add-contact-form">
      <div class="add-contact-row">
        <select v-model="addContactId" class="contact-select">
          <option value="">-- Select contact --</option>
          <option v-for="c in availableContacts" :key="c.id" :value="c.id">
            {{ c.name }}{{ c.email ? ` (${c.email})` : '' }}
          </option>
        </select>
        <select v-model="addContactRole" class="role-select">
          <option value="">-- Role --</option>
          <option v-for="r in ROLE_SUGGESTIONS" :key="r" :value="r">{{ r }}</option>
        </select>
        <button class="btn btn-sm btn-primary" :disabled="!addContactId || addContactSaving" @click="submitAddContact">
          Add
        </button>
      </div>
      <div class="new-contact-toggle">
        <button class="btn-link" @click="showNewContactInline = !showNewContactInline">
          {{ showNewContactInline ? 'Cancel' : '+ New contact' }}
        </button>
      </div>
      <div v-if="showNewContactInline" class="add-contact-row">
        <input v-model="newContactName" type="text" placeholder="Name" class="contact-input" />
        <input v-model="newContactEmail" type="email" placeholder="Email" class="contact-input" />
        <select v-model="newContactRole" class="role-select">
          <option value="">-- Role --</option>
          <option v-for="r in ROLE_SUGGESTIONS" :key="r" :value="r">{{ r }}</option>
        </select>
        <button class="btn btn-sm btn-primary" :disabled="!newContactName.trim() || creatingNewContact" @click="submitNewTeamContact">
          Create & Add
        </button>
      </div>
    </div>

    <div v-if="teamLoading" class="empty">Loading team...</div>
    <div v-else-if="teamContacts.length === 0 && !showAddContact" class="empty">No team members</div>
    <div v-else class="team-list">
      <div v-for="tc in teamContacts" :key="tc.contact_id" class="team-member">
        <div class="team-member-info">
          <span class="team-member-name">{{ tc.name }}</span>
          <span v-if="tc.role" class="team-member-role">{{ tc.role }}</span>
        </div>
        <div class="team-member-details">
          <a v-if="tc.email" :href="'mailto:' + tc.email" class="team-detail">
            <i class="pi pi-envelope" /> {{ tc.email }}
          </a>
          <span v-if="tc.phone" class="team-detail">
            <i class="pi pi-phone" /> {{ tc.phone }}
          </span>
        </div>
        <button class="btn-remove" title="Remove from team" @click="removeTeamContact(tc.contact_id)">
          &times;
        </button>
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

.empty {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all 0.15s;
  color: var(--p-text-color);
}

.btn:hover {
  background: var(--p-content-hover-background);
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.btn-primary {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.btn-primary:hover {
  background: var(--p-primary-hover-color);
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--p-text-muted-color);
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.btn-icon:hover {
  background: var(--p-content-hover-background);
  color: var(--p-text-color);
}

.btn-remove {
  background: none;
  border: none;
  color: var(--p-red-600);
  cursor: pointer;
  font-size: 1rem;
  margin-left: auto;
  padding: 0 0.25rem;
}

/* Team */
.team-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.team-member {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.25rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.team-member:last-child {
  border-bottom: none;
}

.team-member-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.team-member-name {
  font-size: 0.8125rem;
  font-weight: 600;
}

.team-member-role {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background);
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  white-space: nowrap;
}

.team-member-details {
  display: flex;
  gap: 0.75rem;
  flex: 1;
  justify-content: flex-end;
}

.team-detail {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  display: flex;
  align-items: center;
  gap: 0.25rem;
  text-decoration: none;
}

.team-detail:hover {
  color: var(--p-primary-color);
}

.add-contact-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  margin-bottom: 0.75rem;
  background: var(--p-content-hover-background);
}

.add-contact-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.contact-select,
.role-select,
.contact-input {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
}

.contact-select { flex: 2; min-width: 0; }
.role-select { flex: 1; min-width: 0; }
.contact-input { flex: 1; min-width: 0; }

.new-contact-toggle {
  display: flex;
}

.btn-link {
  background: none;
  border: none;
  color: var(--p-primary-color);
  font-size: 0.75rem;
  cursor: pointer;
  padding: 0;
}

.btn-link:hover {
  text-decoration: underline;
}
</style>
