<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue'
import type { ProjectSummary, ProjectNote } from '../../types'
import { getProjectNotes, addProjectNote, updateProjectNote, deleteProjectNote } from '../../api/projects'
import { uploadImage } from '../../api/tasks'
import { useToast } from '../../composables/useToast'
import { useAuth } from '../../composables/useAuth'
import { formatDateTime } from '../../utils/dates'
import MarkdownRenderer from '../MarkdownRenderer.vue'

const props = defineProps<{ project: ProjectSummary }>()

const toast = useToast()
const { user } = useAuth()

const notes = ref<ProjectNote[]>([])
const notesLoading = ref(false)
const newNote = ref('')
const noteSaving = ref(false)
const noteImageUploading = ref(false)
const noteSearch = ref('')
const editingNoteId = ref<string | null>(null)
const editNoteContent = ref('')
const newNoteTab = ref<'edit' | 'preview'>('edit')
const editNoteTab = ref<'edit' | 'preview'>('edit')

const filteredNotes = computed(() => {
  const sorted = [...notes.value].sort((a, b) => {
    const da = a.created_at ? new Date(a.created_at).getTime() : 0
    const db = b.created_at ? new Date(b.created_at).getTime() : 0
    return db - da
  })
  if (!noteSearch.value.trim()) return sorted
  const q = noteSearch.value.toLowerCase()
  return sorted.filter(n => n.content.toLowerCase().includes(q))
})

async function loadNotes() {
  notesLoading.value = true
  try {
    notes.value = await getProjectNotes(props.project.id)
  } catch (e) {
    console.error('Failed to load notes:', e)
  } finally {
    notesLoading.value = false
  }
}

async function submitNote() {
  if (!newNote.value.trim()) return
  noteSaving.value = true
  try {
    await addProjectNote(props.project.id, { content: newNote.value, author_id: user.value?.id })
    newNote.value = ''
    sessionStorage.removeItem(draftKey())
    toast.success('Note added')
    await loadNotes()
  } catch (e) {
    toast.error(String(e))
  } finally {
    noteSaving.value = false
  }
}

function cancelNewNote() {
  newNote.value = ''
  sessionStorage.removeItem(draftKey())
}

function startEditNote(note: ProjectNote) {
  editingNoteId.value = note.id
  editNoteContent.value = note.content
}

function cancelEditNote() {
  editingNoteId.value = null
  editNoteContent.value = ''
  sessionStorage.removeItem(editKey())
}

async function saveEditNote(noteId: string) {
  if (!editNoteContent.value.trim()) return
  try {
    await updateProjectNote(noteId, { content: editNoteContent.value })
    editingNoteId.value = null
    editNoteContent.value = ''
    sessionStorage.removeItem(editKey())
    toast.success('Note updated')
    await loadNotes()
  } catch (e) {
    toast.error(String(e))
  }
}

async function copyNoteLink(noteId: string) {
  const url = `${window.location.origin}${window.location.pathname}?section=notes#note-${noteId}`
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url)
    } else {
      const ta = document.createElement('textarea')
      ta.value = url
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      if (!ok) throw new Error('execCommand failed')
    }
    toast.success('Note link copied')
  } catch {
    toast.error('Failed to copy link')
  }
}

function scrollToHashedNote() {
  const hash = window.location.hash
  if (!hash.startsWith('#note-')) return
  nextTick(() => {
    const el = document.getElementById(hash.slice(1))
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('highlight')
    setTimeout(() => el.classList.remove('highlight'), 2000)
  })
}

async function removeNote(noteId: string) {
  if (!confirm('Delete this note?')) return
  try {
    await deleteProjectNote(noteId)
    toast.success('Note deleted')
    await loadNotes()
  } catch (e) {
    toast.error(String(e))
  }
}

async function handlePasteImage(event: ClipboardEvent, targetRef: typeof newNote) {
  const items = event.clipboardData?.files
  if (!items?.length) return
  const imageFile = Array.from(items).find(f => f.type.startsWith('image/'))
  if (!imageFile) return

  event.preventDefault()
  noteImageUploading.value = true
  try {
    const { url } = await uploadImage(imageFile)
    const textarea = event.target as HTMLTextAreaElement
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const before = targetRef.value.slice(0, start)
    const after = targetRef.value.slice(end)
    targetRef.value = before + `![image](${url})` + after
  } catch (e) {
    toast.error('Image upload failed: ' + String(e))
  } finally {
    noteImageUploading.value = false
  }
}

function onNotePaste(event: ClipboardEvent) {
  handlePasteImage(event, newNote)
}

// Draft persistence via sessionStorage
function draftKey() { return `note-draft-${props.project.id}` }
function editKey() { return `note-edit-${props.project.id}` }

function restoreDrafts() {
  const draft = sessionStorage.getItem(draftKey())
  if (draft) newNote.value = draft

  const editDraft = sessionStorage.getItem(editKey())
  if (editDraft) {
    try {
      const { id, content } = JSON.parse(editDraft)
      editingNoteId.value = id
      editNoteContent.value = content
    } catch { /* ignore corrupt data */ }
  }
}

watch(newNote, (val) => {
  if (val) sessionStorage.setItem(draftKey(), val)
  else sessionStorage.removeItem(draftKey())
})

watch(editNoteContent, (val) => {
  if (editingNoteId.value && val) {
    sessionStorage.setItem(editKey(), JSON.stringify({ id: editingNoteId.value, content: val }))
  } else {
    sessionStorage.removeItem(editKey())
  }
})

watch(() => props.project.id, async () => {
  restoreDrafts()
  await loadNotes()
  scrollToHashedNote()
}, { immediate: true })

defineExpose({ notesCount: computed(() => notes.value.length), loadNotes })
</script>

<template>
  <div class="project-notes">
    <div class="add-note">
      <div class="editor-tabs">
        <button type="button" class="tab" :class="{ active: newNoteTab === 'edit' }" @click="newNoteTab = 'edit'">Edit</button>
        <button type="button" class="tab" :class="{ active: newNoteTab === 'preview' }" @click="newNoteTab = 'preview'">Preview</button>
      </div>
      <textarea v-if="newNoteTab === 'edit'" v-model="newNote" rows="7" placeholder="Add a note... (markdown supported)" class="note-input" @paste="onNotePaste" />
      <div v-else class="editor-preview" :class="{ empty: !newNote }">
        <MarkdownRenderer v-if="newNote" :content="newNote" />
        <span v-else class="preview-placeholder">Nothing to preview</span>
      </div>
      <small v-if="noteImageUploading" class="upload-indicator">Uploading image...</small>
      <div class="add-note-actions">
        <button class="btn btn-sm" :disabled="noteSaving || !newNote" @click="cancelNewNote">Cancel</button>
        <button class="btn btn-sm btn-primary" :disabled="noteSaving || !newNote.trim()" @click="submitNote">
          {{ noteSaving ? 'Adding...' : 'Add Note' }}
        </button>
      </div>
    </div>

    <div v-if="notes.length > 1" class="note-search">
      <i class="pi pi-search" />
      <input
        v-model="noteSearch"
        type="text"
        placeholder="Search notes..."
      />
      <button v-if="noteSearch" class="search-clear" @click="noteSearch = ''">
        <i class="pi pi-times" />
      </button>
    </div>

    <div v-if="notesLoading" class="empty">Loading notes...</div>
    <div v-else-if="filteredNotes.length === 0 && notes.length > 0" class="empty">No matching notes</div>
    <div v-else-if="notes.length === 0 && !notesLoading" class="empty">No notes yet</div>
    <div v-else class="notes-list">
      <div v-for="note in filteredNotes" :key="note.id" :id="`note-${note.id}`" class="note-card">
        <div class="note-header">
          <img v-if="note.author_avatar_url" :src="note.author_avatar_url" class="note-avatar" />
          <span class="note-author">{{ note.author_name || 'Unknown' }}</span>
          <span class="note-date">{{ formatDateTime(note.created_at) }}</span>
          <div class="note-actions">
            <button v-if="editingNoteId !== note.id" class="btn-edit-note" title="Edit note" @click="startEditNote(note)"><i class="pi pi-pencil" /></button>
            <button class="btn-link-note" title="Copy link to note" @click="copyNoteLink(note.id)"><i class="pi pi-link" /></button>
            <button class="btn-remove" title="Delete note" @click="removeNote(note.id)">&times;</button>
          </div>
        </div>
        <div v-if="editingNoteId === note.id" class="note-edit">
          <div class="editor-tabs">
            <button type="button" class="tab" :class="{ active: editNoteTab === 'edit' }" @click="editNoteTab = 'edit'">Edit</button>
            <button type="button" class="tab" :class="{ active: editNoteTab === 'preview' }" @click="editNoteTab = 'preview'">Preview</button>
          </div>
          <textarea v-if="editNoteTab === 'edit'" v-model="editNoteContent" rows="5" class="note-edit-textarea" />
          <div v-else class="editor-preview" :class="{ empty: !editNoteContent }">
            <MarkdownRenderer v-if="editNoteContent" :content="editNoteContent" />
            <span v-else class="preview-placeholder">Nothing to preview</span>
          </div>
          <div class="note-edit-actions">
            <button class="btn btn-sm btn-primary" @click="saveEditNote(note.id)">Save</button>
            <button class="btn btn-sm" @click="cancelEditNote">Cancel</button>
          </div>
        </div>
        <MarkdownRenderer v-else :content="note.content" class="note-body" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.add-note {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.note-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  resize: vertical;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-family: inherit;
  width: 100%;
  box-sizing: border-box;
}

.editor-tabs {
  display: flex;
  gap: 0.25rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.editor-tabs .tab {
  background: none;
  border: none;
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.editor-tabs .tab:hover {
  color: var(--p-text-color);
}

.editor-tabs .tab.active {
  color: var(--p-primary-color);
  border-bottom-color: var(--p-primary-color);
}

.editor-preview {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  overflow-y: auto;
  min-height: 9rem;
}

.editor-preview.empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-placeholder {
  color: var(--p-text-muted-color);
  font-style: italic;
  font-size: 0.75rem;
}

.add-note-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.upload-indicator { color: var(--p-primary-color); font-size: 0.75rem; font-style: italic; }

.note-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.375rem 0.75rem;
  margin-top: 0.75rem;
}

.note-search i {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.note-search input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 0.8125rem;
  background: transparent;
  color: var(--p-text-color);
}

.search-clear {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.125rem;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  display: flex;
  align-items: center;
}

.search-clear:hover {
  color: var(--p-text-color);
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.note-card {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.625rem;
}

.note-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.note-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  object-fit: cover;
}

.note-author {
  font-weight: 600;
  font-size: 0.75rem;
}

.note-date {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.note-body {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  white-space: pre-wrap;
}

.note-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0;
}

.btn-remove {
  background: none;
  border: none;
  color: var(--p-red-600);
  cursor: pointer;
  font-size: 1rem;
  padding: 0 0.25rem;
}

.btn-edit-note,
.btn-link-note {
  background: none;
  border: none;
  color: var(--p-text-muted-color);
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0.125rem 0.25rem;
}

.btn-edit-note:hover,
.btn-link-note:hover {
  color: var(--p-primary-color);
}

.btn-edit-note .pi,
.btn-link-note .pi {
  font-size: 0.6875rem;
}

.note-card.highlight {
  background: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 15%, transparent);
  transition: background 0.5s ease;
}

.note-edit {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.note-edit-textarea {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  resize: vertical;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  font-family: inherit;
  width: 100%;
  box-sizing: border-box;
}

.note-edit-actions {
  display: flex;
  gap: 0.5rem;
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

.empty {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}
</style>
