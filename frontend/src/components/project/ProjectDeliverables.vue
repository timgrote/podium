<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Deliverable } from '../../types'
import { getDeliverables, createDeliverable, updateDeliverable, deleteDeliverable } from '../../api/deliverables'
import { useToast } from '../../composables/useToast'
import { formatDate, isOverdue } from '../../utils/dates'

const props = defineProps<{
  project: { id: string }
}>()

const emit = defineEmits<{
  refreshProject: []
}>()

const toast = useToast()

const deliverables = ref<Deliverable[]>([])
const loading = ref(false)
const showNewForm = ref(false)
const newName = ref('')
const newDeadline = ref('')
const saving = ref(false)

const statusColors: Record<string, string> = {
  not_started: 'gray',
  in_progress: 'blue',
  sent: 'amber',
  accepted: 'green',
}

const statusLabels: Record<string, string> = {
  not_started: 'Not Started',
  in_progress: 'In Progress',
  sent: 'Sent',
  accepted: 'Accepted',
}

watch(() => props.project.id, async () => {
  await loadDeliverables()
}, { immediate: true })

async function loadDeliverables() {
  loading.value = true
  try {
    deliverables.value = await getDeliverables(props.project.id)
  } catch (e) {
    console.error('Failed to load deliverables:', e)
  } finally {
    loading.value = false
  }
}

async function submitNew() {
  if (!newName.value.trim()) return
  saving.value = true
  try {
    await createDeliverable(props.project.id, {
      name: newName.value,
      deadline: newDeadline.value || undefined,
    })
    newName.value = ''
    newDeadline.value = ''
    showNewForm.value = false
    toast.success('Deliverable created')
    await loadDeliverables()
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  } finally {
    saving.value = false
  }
}

function cancelNew() {
  newName.value = ''
  newDeadline.value = ''
  showNewForm.value = false
}

async function cycleStatus(deliverable: Deliverable) {
  const order = ['not_started', 'in_progress', 'sent', 'accepted']
  const idx = order.indexOf(deliverable.status)
  const next = order[(idx + 1) % order.length]
  try {
    await updateDeliverable(deliverable.id, { status: next })
    await loadDeliverables()
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  }
}

async function setProgress(deliverable: Deliverable, event: Event) {
  const input = event.target as HTMLInputElement
  const val = Math.max(0, Math.min(100, parseInt(input.value) || 0))
  try {
    await updateDeliverable(deliverable.id, { progress_percent: val })
    await loadDeliverables()
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  }
}

async function setDeadline(deliverable: Deliverable, event: Event) {
  const input = event.target as HTMLInputElement
  const val = input.value || null
  try {
    await updateDeliverable(deliverable.id, { deadline: val || undefined })
    await loadDeliverables()
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  }
}

async function remove(deliverable: Deliverable) {
  try {
    await deleteDeliverable(deliverable.id)
    toast.success('Deliverable deleted')
    await loadDeliverables()
    emit('refreshProject')
  } catch (e) {
    toast.error(String(e))
  }
}

defineExpose({ loadDeliverables })
</script>

<template>
  <div class="deliverables-section">
    <div class="section-header">
      <h4>Deliverables</h4>
      <button v-if="!showNewForm" class="btn-icon" title="Add deliverable" @click="showNewForm = true">
        <i class="pi pi-plus" />
      </button>
    </div>

    <!-- Inline new deliverable form -->
    <div v-if="showNewForm" class="new-deliverable-form">
      <input v-model="newName" type="text" placeholder="Deliverable name" class="new-del-input" />
      <input v-model="newDeadline" type="date" class="new-del-date" />
      <div class="new-del-actions">
        <button class="btn btn-sm" @click="cancelNew">Cancel</button>
        <button class="btn btn-sm btn-primary" :disabled="saving || !newName.trim()" @click="submitNew">
          {{ saving ? 'Creating...' : 'Create' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="empty">Loading deliverables...</div>
    <div v-else-if="deliverables.length === 0 && !showNewForm" class="empty">No deliverables</div>

    <div v-else class="deliverables-list">
      <div v-for="del in deliverables" :key="del.id" class="deliverable-item">
        <span class="del-status clickable" :class="'status-' + statusColors[del.status]" :title="'Click to cycle status'" @click="cycleStatus(del)">
          <i v-if="del.status === 'accepted'" class="pi pi-check" />
          <i v-else-if="del.status === 'sent'" class="pi pi-send" />
          <i v-else-if="del.status === 'in_progress'" class="pi pi-spinner" />
          <i v-else class="pi pi-circle" />
        </span>
        <span class="del-status-label" :class="'status-text-' + statusColors[del.status]">{{ statusLabels[del.status] }}</span>

        <span class="del-name">{{ del.name }}</span>

        <span class="del-progress">
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            :value="del.progress_percent"
            class="progress-slider"
            @change="setProgress(del, $event)"
          />
          <span class="progress-text">{{ del.progress_percent }}%</span>
        </span>

        <span class="del-deadline" :class="{ overdue: isOverdue(del.deadline) && del.status !== 'accepted' }">
          <span v-if="del.deadline">{{ formatDate(del.deadline) }}</span>
          <span v-else class="no-date-hint"><i class="pi pi-calendar" /></span>
          <input
            type="date"
            class="inline-date-input"
            :value="del.deadline || ''"
            @change="setDeadline(del, $event)"
          />
        </span>

        <span v-if="del.sent_at" class="del-sent-date" title="Sent date">
          <i class="pi pi-send" /> {{ formatDate(del.sent_at) }}
        </span>
        <span v-else class="del-sent-date"></span>

        <button class="btn-remove" title="Delete" @click="remove(del)">
          <i class="pi pi-trash" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.deliverables-section {
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.section-header h4 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
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

.new-deliverable-form {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  margin-bottom: 0.75rem;
  background: var(--p-content-hover-background);
}

.new-del-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
}

.new-del-date {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
}

.new-del-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.deliverables-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.deliverable-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.25rem;
  font-size: 0.8125rem;
  border-radius: 0.25rem;
}

.deliverable-item:hover {
  background: var(--p-content-hover-background);
}

.del-status {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  cursor: pointer;
  font-size: 0.625rem;
  transition: all 0.15s;
}

.del-status .pi {
  font-size: 0.625rem;
}

.del-status.status-gray {
  background: var(--p-surface-200);
  color: var(--p-surface-600);
}

.del-status.status-blue {
  background: var(--p-blue-100);
  color: var(--p-blue-600);
}

.del-status.status-amber {
  background: var(--p-amber-100);
  color: var(--p-amber-700);
}

.del-status.status-green {
  background: var(--p-green-100);
  color: var(--p-green-600);
}

.del-status-label {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  flex-shrink: 0;
  width: 5.5rem;
}

.del-status-label.status-text-gray { color: var(--p-surface-500); }
.del-status-label.status-text-blue { color: var(--p-blue-600); }
.del-status-label.status-text-amber { color: var(--p-amber-700); }
.del-status-label.status-text-green { color: var(--p-green-600); }

.del-name {
  flex: 1;
  min-width: 0;
  font-weight: 500;
}

.del-progress {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  width: 7rem;
  flex-shrink: 0;
}

.progress-slider {
  width: 80px;
  height: 4px;
  cursor: pointer;
  accent-color: var(--p-primary-color);
}

.progress-text {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  width: 2rem;
  text-align: right;
  flex-shrink: 0;
}

.del-deadline {
  width: 5rem;
  flex-shrink: 0;
  position: relative;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
}

.del-deadline:hover {
  color: var(--p-primary-color);
}

.del-deadline.overdue {
  color: var(--p-red-600);
  font-weight: 600;
}

.del-sent-date {
  width: 5rem;
  flex-shrink: 0;
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.inline-date-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  width: 100%;
  cursor: pointer;
  font-size: 0.75rem;
}

.no-date-hint {
  color: var(--p-surface-400);
  font-size: 0.75rem;
}

.no-date-hint:hover {
  color: var(--p-primary-color);
}

.btn-remove {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--p-text-muted-color);
  border-radius: 0.25rem;
  font-size: 0.75rem;
  flex-shrink: 0;
}

.btn-remove:hover {
  color: var(--p-red-600);
  background: var(--p-red-50);
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
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
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

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
