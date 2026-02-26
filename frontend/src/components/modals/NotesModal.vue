<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from '../../composables/useToast'
import { useAuth } from '../../composables/useAuth'
import { getProjectNotes, addProjectNote, deleteProjectNote } from '../../api/projects'
import { uploadImage } from '../../api/tasks'
import type { ProjectNote } from '../../types'
import RichText from '../RichText.vue'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  projectId: string
}>()

const toast = useToast()
const { user } = useAuth()
const notes = ref<ProjectNote[]>([])
const loading = ref(false)
const newNote = ref('')
const saving = ref(false)
const imageUploading = ref(false)

watch(visible, async (val) => {
  if (!val || !props.projectId) return
  await loadNotes()
})

async function loadNotes() {
  loading.value = true
  try {
    notes.value = await getProjectNotes(props.projectId)
  } catch (e) {
    console.error('Failed to load notes:', e)
  } finally {
    loading.value = false
  }
}

async function addNote() {
  if (!newNote.value.trim()) return
  saving.value = true
  try {
    await addProjectNote(props.projectId, { content: newNote.value, author_id: user.value?.id })
    newNote.value = ''
    toast.success('Note added')
    await loadNotes()
  } catch (e) {
    toast.error(String(e))
  } finally {
    saving.value = false
  }
}

async function removeNote(noteId: string) {
  try {
    await deleteProjectNote(noteId)
    toast.success('Note deleted')
    await loadNotes()
  } catch (e) {
    toast.error(String(e))
  }
}

async function handleNotePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.files
  if (!items?.length) return
  const imageFile = Array.from(items).find(f => f.type.startsWith('image/'))
  if (!imageFile) return

  event.preventDefault()
  imageUploading.value = true
  try {
    const { url } = await uploadImage(imageFile)
    const textarea = event.target as HTMLTextAreaElement
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const before = newNote.value.slice(0, start)
    const after = newNote.value.slice(end)
    newNote.value = before + `![image](${url})` + after
  } catch (e) {
    toast.error('Image upload failed: ' + String(e))
  } finally {
    imageUploading.value = false
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    header="Project Notes"
    :modal="true"
    :style="{ width: '500px' }"
  >
    <div class="notes-container">
      <div class="add-note">
        <textarea v-model="newNote" rows="2" placeholder="Add a note..." @paste="handleNotePaste" />
        <small v-if="imageUploading" class="upload-indicator">Uploading image...</small>
        <button class="btn btn-primary btn-sm" :disabled="saving" @click="addNote">
          {{ saving ? 'Adding...' : 'Add Note' }}
        </button>
      </div>

      <div v-if="loading" class="loading">Loading notes...</div>
      <div v-else-if="notes.length === 0" class="empty">No notes yet.</div>
      <div v-else class="notes-list">
        <div v-for="note in notes" :key="note.id" class="note">
          <div class="note-header">
            <img v-if="note.author_avatar_url" :src="note.author_avatar_url" class="note-avatar" />
            <span class="note-author">{{ note.author_name || 'Unknown' }}</span>
            <span class="note-date">{{ formatDate(note.created_at) }}</span>
            <button class="btn-remove" @click="removeNote(note.id)">&times;</button>
          </div>
          <RichText :content="note.content" class="note-content" />
        </div>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.notes-container { display: flex; flex-direction: column; gap: 1rem; }
.add-note { display: flex; flex-direction: column; gap: 0.5rem; }
.add-note textarea { padding: 0.5rem 0.75rem; border: 1px solid var(--p-form-field-border-color); border-radius: 0.375rem; font-size: 0.875rem; resize: vertical; background: var(--p-form-field-background); color: var(--p-text-color); }
.notes-list { display: flex; flex-direction: column; gap: 0.75rem; max-height: 400px; overflow-y: auto; }
.note { border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; padding: 0.75rem; }
.note-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.375rem; }
.note-avatar { width: 20px; height: 20px; border-radius: 50%; object-fit: cover; }
.note-author { font-weight: 600; font-size: 0.8125rem; }
.note-date { font-size: 0.75rem; color: var(--p-text-muted-color); }
.note-content { font-size: 0.875rem; color: var(--p-text-muted-color); white-space: pre-wrap; }
.btn-remove { background: none; border: none; color: var(--p-red-600); cursor: pointer; font-size: 1rem; margin-left: auto; padding: 0 0.25rem; }
.empty { text-align: center; color: var(--p-text-muted-color); font-size: 0.875rem; padding: 1rem; }
.loading { text-align: center; color: var(--p-text-muted-color); padding: 1rem; }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; color: var(--p-text-color); }
.btn-sm { padding: 0.375rem 0.75rem; font-size: 0.8125rem; }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.upload-indicator { color: var(--p-primary-color); font-size: 0.75rem; font-style: italic; }
</style>
