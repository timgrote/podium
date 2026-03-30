<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { WikiNote } from '../types'
import { getWikiNotes, getWikiCategories, getWikiNote, createWikiNote, updateWikiNote, deleteWikiNote } from '../api/wiki'
import { uploadImage } from '../api/tasks'
import { useToast } from '../composables/useToast'
import { useAuth } from '../composables/useAuth'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { user } = useAuth()

// State
const notes = ref<WikiNote[]>([])
const categories = ref<string[]>([])
const selectedNote = ref<WikiNote | null>(null)
const loading = ref(true)
const searchQuery = ref('')
const selectedCategory = ref('')

// Editor state
const editing = ref(false)
const creating = ref(false)
const editTitle = ref('')
const editContent = ref('')
const editCategory = ref('General')
const saving = ref(false)
const showPreview = ref(false)
const imageUploading = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | null = null

// Map of note title (lowercase) -> note id for wiki linking
const noteIndex = computed(() => {
  const map = new Map<string, string>()
  for (const n of notes.value) {
    map.set(n.title.toLowerCase(), n.id)
  }
  return map
})

const filteredNotes = computed(() => {
  return notes.value
})

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

async function loadNotes() {
  loading.value = true
  try {
    const [noteList, catList] = await Promise.all([
      getWikiNotes(searchQuery.value || undefined, selectedCategory.value || undefined),
      getWikiCategories(),
    ])
    notes.value = noteList
    categories.value = catList
  } catch (e) {
    toast.error('Failed to load notes: ' + String(e))
  } finally {
    loading.value = false
  }
}

async function selectNote(note: WikiNote) {
  try {
    selectedNote.value = await getWikiNote(note.id)
    editing.value = false
    creating.value = false
    router.replace(`/wiki/${note.id}`)
  } catch (e) {
    toast.error('Failed to load note: ' + String(e))
  }
}

function startCreate() {
  selectedNote.value = null
  editing.value = false
  creating.value = true
  editTitle.value = ''
  editContent.value = ''
  editCategory.value = selectedCategory.value || 'General'
  showPreview.value = false
}

function startEdit() {
  if (!selectedNote.value) return
  editing.value = true
  creating.value = false
  editTitle.value = selectedNote.value.title
  editContent.value = selectedNote.value.content
  editCategory.value = selectedNote.value.category
  showPreview.value = false
}

function cancelEdit() {
  editing.value = false
  creating.value = false
}

async function saveNote() {
  if (!editTitle.value.trim()) {
    toast.error('Title is required')
    return
  }
  saving.value = true
  try {
    if (creating.value) {
      const created = await createWikiNote({
        title: editTitle.value.trim(),
        content: editContent.value,
        category: editCategory.value.trim() || 'General',
        created_by: user.value?.id || null,
      })
      creating.value = false
      await loadNotes()
      await selectNote(created)
      toast.success('Note created')
    } else if (editing.value && selectedNote.value) {
      await updateWikiNote(selectedNote.value.id, {
        title: editTitle.value.trim(),
        content: editContent.value,
        category: editCategory.value.trim() || 'General',
        updated_by: user.value?.id || null,
      })
      editing.value = false
      selectedNote.value = await getWikiNote(selectedNote.value.id)
      await loadNotes()
      toast.success('Note saved')
    }
  } catch (e) {
    toast.error('Failed to save: ' + String(e))
  } finally {
    saving.value = false
  }
}

async function removeNote() {
  if (!selectedNote.value || !confirm('Delete this note?')) return
  try {
    await deleteWikiNote(selectedNote.value.id)
    selectedNote.value = null
    editing.value = false
    router.replace('/wiki')
    await loadNotes()
    toast.success('Note deleted')
  } catch (e) {
    toast.error('Failed to delete note: ' + String(e))
  }
}

async function handlePaste(event: ClipboardEvent) {
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
    const before = editContent.value.slice(0, start)
    const after = editContent.value.slice(end)
    editContent.value = before + `![image](${url})` + after
  } catch (e) {
    toast.error('Image upload failed: ' + String(e))
  } finally {
    imageUploading.value = false
  }
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadNotes(), 300)
}

watch(selectedCategory, () => loadNotes())

onMounted(async () => {
  await loadNotes()
  const noteId = route.params.noteId as string
  if (noteId) {
    const found = notes.value.find(n => n.id === noteId)
    if (found) {
      await selectNote(found)
    } else {
      toast.error('Note not found — it may have been deleted')
      router.replace('/wiki')
    }
  }
})

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <div class="wiki-page">
    <div class="page-header">
      <h1>Wiki</h1>
      <button class="btn-add" @click="startCreate">
        <i class="pi pi-plus" /> New Note
      </button>
    </div>

    <div class="wiki-layout">
      <!-- Left Panel: Note List -->
      <div class="wiki-sidebar">
        <div class="sidebar-filters">
          <div class="search-box">
            <i class="pi pi-search" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search notes..."
              @input="onSearchInput"
            />
            <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''; loadNotes()">
              <i class="pi pi-times" />
            </button>
          </div>
          <select v-model="selectedCategory" class="category-filter">
            <option value="">All Categories</option>
            <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>

        <div v-if="loading" class="empty-state">Loading...</div>
        <div v-else-if="notes.length === 0" class="empty-state">
          {{ searchQuery || selectedCategory ? 'No matching notes' : 'No notes yet — create one!' }}
        </div>
        <div v-else class="note-list">
          <div
            v-for="note in filteredNotes"
            :key="note.id"
            class="note-item"
            :class="{ active: selectedNote?.id === note.id }"
            @click="selectNote(note)"
          >
            <div class="note-item-title">{{ note.title }}</div>
            <div class="note-item-meta">
              <span class="category-badge">{{ note.category }}</span>
              <span class="note-date">{{ formatDate(note.updated_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Panel: Note Detail / Editor -->
      <div class="wiki-content">
        <!-- Creating new note -->
        <div v-if="creating" class="editor">
          <input v-model="editTitle" type="text" class="edit-title" placeholder="Note title..." />
          <div class="edit-category-row">
            <label>Category:</label>
            <input v-model="editCategory" type="text" class="edit-category" placeholder="General" list="wiki-categories" />
            <datalist id="wiki-categories">
              <option v-for="cat in categories" :key="cat" :value="cat" />
            </datalist>
          </div>
          <div class="editor-toolbar">
            <button class="toolbar-btn" :class="{ active: !showPreview }" @click="showPreview = false">Edit</button>
            <button class="toolbar-btn" :class="{ active: showPreview }" @click="showPreview = true">Preview</button>
            <small v-if="imageUploading" class="upload-indicator">Uploading image...</small>
          </div>
          <textarea
            v-if="!showPreview"
            v-model="editContent"
            class="edit-textarea"
            placeholder="Write your note in markdown..."
            rows="20"
            @paste="handlePaste"
          />
          <div v-else class="preview-panel">
            <MarkdownRenderer :content="editContent" :note-index="noteIndex" />
          </div>
          <div class="editor-actions">
            <button class="btn btn-primary" :disabled="saving" @click="saveNote">
              {{ saving ? 'Saving...' : 'Create Note' }}
            </button>
            <button class="btn" @click="cancelEdit">Cancel</button>
          </div>
        </div>

        <!-- Editing existing note -->
        <div v-else-if="editing && selectedNote" class="editor">
          <input v-model="editTitle" type="text" class="edit-title" placeholder="Note title..." />
          <div class="edit-category-row">
            <label>Category:</label>
            <input v-model="editCategory" type="text" class="edit-category" placeholder="General" list="wiki-categories" />
            <datalist id="wiki-categories">
              <option v-for="cat in categories" :key="cat" :value="cat" />
            </datalist>
          </div>
          <div class="editor-toolbar">
            <button class="toolbar-btn" :class="{ active: !showPreview }" @click="showPreview = false">Edit</button>
            <button class="toolbar-btn" :class="{ active: showPreview }" @click="showPreview = true">Preview</button>
            <small v-if="imageUploading" class="upload-indicator">Uploading image...</small>
          </div>
          <textarea
            v-if="!showPreview"
            v-model="editContent"
            class="edit-textarea"
            placeholder="Write your note in markdown..."
            rows="20"
            @paste="handlePaste"
          />
          <div v-else class="preview-panel">
            <MarkdownRenderer :content="editContent" :note-index="noteIndex" />
          </div>
          <div class="editor-actions">
            <button class="btn btn-primary" :disabled="saving" @click="saveNote">
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
            <button class="btn" @click="cancelEdit">Cancel</button>
          </div>
        </div>

        <!-- Viewing note -->
        <div v-else-if="selectedNote" class="note-view">
          <div class="note-view-header">
            <h2>{{ selectedNote.title }}</h2>
            <div class="note-view-actions">
              <button class="btn btn-sm" @click="startEdit"><i class="pi pi-pencil" /> Edit</button>
              <button class="btn btn-sm btn-danger" @click="removeNote"><i class="pi pi-trash" /> Delete</button>
            </div>
          </div>
          <div class="note-view-meta">
            <span class="category-badge">{{ selectedNote.category }}</span>
            <span v-if="selectedNote.created_by_name" class="meta-item">
              Created by {{ selectedNote.created_by_name }} on {{ formatDate(selectedNote.created_at) }}
            </span>
            <span v-if="selectedNote.updated_by_name && selectedNote.updated_by !== selectedNote.created_by" class="meta-item">
              &middot; Updated by {{ selectedNote.updated_by_name }} on {{ formatDate(selectedNote.updated_at) }}
            </span>
          </div>
          <div class="note-view-body">
            <MarkdownRenderer :content="selectedNote.content" :note-index="noteIndex" />
          </div>
        </div>

        <!-- Empty state -->
        <div v-else class="empty-content">
          <i class="pi pi-book" />
          <p>Select a note or create a new one</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wiki-page {
  max-width: 1200px;
  margin: 0 auto;
  height: calc(100vh - 2rem);
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.wiki-layout {
  display: flex;
  gap: 1rem;
  flex: 1;
  min-height: 0;
}

/* Left Sidebar */
.wiki-sidebar {
  width: 300px;
  min-width: 300px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sidebar-filters {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.375rem 0.75rem;
}

.search-box i { color: var(--p-text-muted-color); font-size: 0.75rem; }

.search-box input {
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
}

.search-clear:hover { color: var(--p-text-color); }

.category-filter {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
}

.note-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow-y: auto;
  flex: 1;
}

.note-item {
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s;
}

.note-item:hover {
  border-color: var(--p-primary-color);
  background: var(--p-content-hover-background);
}

.note-item.active {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}

.note-item-title {
  font-weight: 500;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.note-item-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.category-badge {
  font-size: 0.6875rem;
  background: var(--p-content-hover-background);
  padding: 0.0625rem 0.375rem;
  border-radius: 0.25rem;
  color: var(--p-text-muted-color);
}

.note-date {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

/* Right Content */
.wiki-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 1.5rem;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--p-text-muted-color);
  gap: 0.75rem;
}

.empty-content .pi { font-size: 2rem; }
.empty-content p { font-size: 0.875rem; }

.empty-state {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  font-style: italic;
  padding: 1rem 0;
}

/* Note View */
.note-view-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.note-view-header h2 {
  font-size: 1.375rem;
  font-weight: 600;
  margin: 0;
}

.note-view-actions {
  display: flex;
  gap: 0.5rem;
}

.note-view-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

/* Editor */
.editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.edit-title {
  font-size: 1.25rem;
  font-weight: 600;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  font-family: inherit;
}

.edit-category-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.edit-category-row label {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.edit-category {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  width: 200px;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  border-bottom: 1px solid var(--p-content-border-color);
  padding-bottom: 0.5rem;
}

.toolbar-btn {
  padding: 0.25rem 0.75rem;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  border-radius: 0.25rem;
}

.toolbar-btn:hover { background: var(--p-content-hover-background); }

.toolbar-btn.active {
  color: var(--p-primary-color);
  font-weight: 600;
}

.upload-indicator {
  color: var(--p-primary-color);
  font-size: 0.75rem;
  font-style: italic;
  margin-left: auto;
}

.edit-textarea {
  padding: 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  resize: vertical;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  font-family: monospace;
  line-height: 1.5;
  min-height: 400px;
}

.preview-panel {
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 1rem;
  min-height: 400px;
}

.editor-actions {
  display: flex;
  gap: 0.5rem;
}

/* Shared buttons */
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

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--p-text-color);
}

.btn:hover { background: var(--p-content-hover-background); }
.btn .pi { font-size: 0.75rem; }

.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn-sm .pi { font-size: 0.625rem; }

.btn-primary {
  background: var(--p-primary-color);
  color: #fff;
  border-color: var(--p-primary-color);
}

.btn-primary:hover { background: var(--p-primary-hover-color); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-danger {
  color: var(--p-red-600);
  border-color: var(--p-red-300);
}

.btn-danger:hover {
  background: color-mix(in srgb, var(--p-red-600) 10%, transparent);
}
</style>
