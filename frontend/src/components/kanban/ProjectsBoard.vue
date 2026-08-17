<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { KanbanBoard, KanbanCard, KanbanColumn } from '../../types'
import { getBoard, moveCard } from '../../api/kanban'
import { useToast } from '../../composables/useToast'
import { parseLocalDate, formatDateShort } from '../../utils/dates'
import {
  PROJECT_SORT_OPTIONS,
  projectMatchesSearch,
  sortProjects,
  type ProjectSortKey,
} from '../../utils/boardSort'
import { useCollapsibleColumns } from '../../composables/useCollapsibleColumns'

const router = useRouter()
const toast = useToast()

const { isCollapsed, toggleColumn } = useCollapsibleColumns()

const board = ref<KanbanBoard | null>(null)
const loading = ref(false)

// --- Filters ---
const searchQuery = ref('')
const clientFilter = ref<string>('all')
const pmFilter = ref<string>('all')
const hideCompleteArchive = ref(false)

// --- Per-column sort (view only — never mutates stored board_order) ---
const columnSort = ref<Record<string, ProjectSortKey>>({})

// Drag state
const dragging = ref<KanbanCard | null>(null)
const dragOverStatus = ref<string | null>(null)

/** Distinct client and PM names present on the board, for filter dropdowns. */
const clientOptions = computed<string[]>(() => {
  const set = new Set<string>()
  for (const col of board.value?.columns ?? []) {
    for (const c of col.projects) if (c.client_name) set.add(c.client_name)
  }
  return [...set].sort((a, b) => a.localeCompare(b))
})

const pmOptions = computed<string[]>(() => {
  const set = new Set<string>()
  for (const col of board.value?.columns ?? []) {
    for (const c of col.projects) if (c.pm_name) set.add(c.pm_name)
  }
  return [...set].sort((a, b) => a.localeCompare(b))
})

/** Columns after applying the hide-complete/archive toggle. */
const visibleColumns = computed<KanbanColumn[]>(() => {
  const cols = board.value?.columns ?? []
  if (!hideCompleteArchive.value) return cols
  return cols.filter((c) => c.status !== 'complete' && c.status !== 'archive')
})

/** Columns with cards filtered (search/client/pm) and sorted per-column. */
const columns = computed<KanbanColumn[]>(() =>
  visibleColumns.value.map((col) => {
    const filtered = col.projects.filter((c) => {
      if (!projectMatchesSearch(c, searchQuery.value)) return false
      if (clientFilter.value !== 'all' && c.client_name !== clientFilter.value) return false
      if (pmFilter.value !== 'all' && c.pm_name !== pmFilter.value) return false
      return true
    })
    const key = columnSort.value[col.status] ?? 'manual'
    return { ...col, projects: sortProjects(filtered, key) }
  }),
)

function columnSortKey(col: KanbanColumn): ProjectSortKey {
  return columnSort.value[col.status] ?? 'manual'
}

function setColumnSort(status: string, key: ProjectSortKey) {
  columnSort.value = { ...columnSort.value, [status]: key }
}

const activeFilterCount = computed(() => {
  let n = 0
  if (searchQuery.value.trim()) n++
  if (clientFilter.value !== 'all') n++
  if (pmFilter.value !== 'all') n++
  if (hideCompleteArchive.value) n++
  return n
})

function clearFilters() {
  searchQuery.value = ''
  clientFilter.value = 'all'
  pmFilter.value = 'all'
  hideCompleteArchive.value = false
}

function cardCount(col: KanbanColumn): number {
  return col.projects.length
}

function deadlineInfo(card: KanbanCard) {
  const dl = card.next_task_deadline
  if (!dl) return null
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const due = parseLocalDate(dl)
  const diffDays = Math.round((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  if (diffDays < 0) return { label: `${Math.abs(diffDays)}d overdue`, severity: 'overdue' as const }
  if (diffDays <= 14) return { label: `Due in ${diffDays}d`, severity: 'soon' as const }
  return { label: formatDateShort(dl), severity: 'normal' as const }
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000) {
    return '$' + (value / 1000).toFixed(value % 1000 === 0 ? 0 : 1) + 'k'
  }
  return '$' + value.toFixed(0)
}

function initials(name: string | null): string {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?'
}

function navigateToProject(card: KanbanCard) {
  router.push(`/projects/${card.project_number || card.id}`)
}

async function load() {
  loading.value = true
  try {
    board.value = await getBoard()
  } catch (e) {
    toast.error('Failed to load board', e instanceof Error ? e.message : undefined)
  } finally {
    loading.value = false
  }
}

// --- Drag & drop ---
// Track where the pointer is over a column so we can place a card at an exact
// position instead of always appending to the end.
const dragOverCardId = ref<string | null>(null)
const dragOverHalf = ref<'top' | 'bottom'>('top')

function onDragStart(card: KanbanCard) {
  dragging.value = card
}
function onDragEnd() {
  dragging.value = null
  dragOverStatus.value = null
  dragOverCardId.value = null
}

function onDragEnter(status: string) {
  dragOverStatus.value = status
  // Entering a new column resets the hovered card so a drop in the empty space
  // appends to that column rather than reusing the previous column's anchor.
  dragOverCardId.value = null
}

/** Record which card the pointer is over and whether it's the top or bottom half. */
function onCardDragOver(status: string, card: KanbanCard, event: DragEvent) {
  dragOverStatus.value = status
  const el = event.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  dragOverCardId.value = card.id
  dragOverHalf.value = event.clientY < rect.top + rect.height / 2 ? 'top' : 'bottom'
}

/**
 * Compute the board_order that places the dragged card at the current drop
 * point (index among the column's other cards). In manual order the displayed
 * order == board_order, so this is exact; for a non-manual sort it anchors to
 * the board_order of the card at the drop point, and the drop snaps the column
 * to manual so the card lands where it was dropped.
 */
function computeTargetBoardOrder(col: KanbanColumn, dragged: KanbanCard): number {
  const hoveredId = dragOverCardId.value
  const hoveredHalf = dragOverHalf.value
  const others = col.projects.filter((p) => p.id !== dragged.id)
  let insertIndex = others.length
  if (hoveredId) {
    const hi = others.findIndex((p) => p.id === hoveredId)
    if (hi >= 0) insertIndex = hoveredHalf === 'top' ? hi : hi + 1
  }
  const anchor = others[insertIndex]
  if (anchor) return anchor.board_order
  return others.length
}

async function onDrop(status: string) {
  const card = dragging.value
  if (!card) return

  const targetCol = columns.value.find((c) => c.status === status)
  // Capture the drop position from the hover state BEFORE clearing it.
  const targetBoardOrder = targetCol ? computeTargetBoardOrder(targetCol, card) : 0

  dragOverStatus.value = null
  dragOverCardId.value = null

  // A drag-and-drop is an explicit manual position → snap the column to manual.
  setColumnSort(status, 'manual')

  try {
    board.value = await moveCard({
      project_id: card.id,
      status,
      board_order: targetBoardOrder,
    })
    toast.success('Moved', `${card.project_name} → ${status}`)
  } catch (e) {
    toast.error('Move failed', e instanceof Error ? e.message : undefined)
  } finally {
    dragging.value = null
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading && !board" class="kanban-loading">
    <i class="pi pi-spin pi-spinner" /> Loading board…
  </div>

  <div v-else class="kanban-board-wrap">
    <!-- Filter toolbar -->
    <div class="kanban-toolbar">
      <div class="toolbar-search">
        <i class="pi pi-search" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search projects, clients, PMs…"
        />
        <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''">
          <i class="pi pi-times" />
        </button>
      </div>

      <div class="toolbar-filters">
        <select v-model="clientFilter" class="toolbar-select" title="Filter by client">
          <option value="all">All clients</option>
          <option v-for="name in clientOptions" :key="name" :value="name">{{ name }}</option>
        </select>

        <select v-model="pmFilter" class="toolbar-select" title="Filter by project manager">
          <option value="all">All PMs</option>
          <option v-for="name in pmOptions" :key="name" :value="name">{{ name }}</option>
        </select>

        <label class="toolbar-toggle" title="Hide complete and archive columns">
          <input v-model="hideCompleteArchive" type="checkbox" />
          Hide done/archive
        </label>

        <button
          v-if="activeFilterCount > 0"
          class="toolbar-clear"
          @click="clearFilters"
        >
          Clear ({{ activeFilterCount }})
        </button>
      </div>
    </div>

    <div class="kanban-board">
    <div
      v-for="col in columns"
      :key="col.status"
      class="kanban-column"
      :class="{
        'drag-over': dragOverStatus === col.status,
        collapsed: isCollapsed(col.status, col.projects.length),
      }"
      :title="isCollapsed(col.status, col.projects.length) ? `Expand ${col.label}` : undefined"
      @dragover.prevent
      @dragenter.prevent="onDragEnter(col.status)"
      @drop.prevent="onDrop(col.status)"
      @click="toggleColumn(col.status)"
    >
      <div class="kanban-column-header">
        <span class="kanban-dot" :class="col.status"></span>
        <span class="kanban-column-label">{{ col.label }}</span>
        <span class="kanban-count">{{ cardCount(col) }}</span>
        <div v-if="!isCollapsed(col.status, col.projects.length)" class="kanban-sort">
          <select
            class="kanban-sort-select"
            :value="columnSortKey(col)"
            title="Sort this column"
            @click.stop
            @change="setColumnSort(col.status, ($event.target as HTMLSelectElement).value as ProjectSortKey)"
          >
            <option
              v-for="opt in PROJECT_SORT_OPTIONS"
              :key="opt.key"
              :value="opt.key"
            >{{ opt.label }}</option>
          </select>
        </div>
      </div>

      <div v-if="!isCollapsed(col.status, col.projects.length)" class="kanban-column-body">
        <div
          v-for="card in col.projects"
          :key="card.id"
          class="kanban-card"
          :class="{
            dragging: dragging?.id === card.id,
            'drop-top': dragOverStatus === col.status && dragOverCardId === card.id && dragOverHalf === 'top',
            'drop-bottom': dragOverStatus === col.status && dragOverCardId === card.id && dragOverHalf === 'bottom',
          }"
          draggable="true"
          @dragstart="onDragStart(card)"
          @dragend="onDragEnd"
          @dragover.prevent="onCardDragOver(col.status, card, $event)"
          @click="navigateToProject(card)"
        >
          <div class="card-title-row">
            <span class="card-title">{{ card.project_name }}</span>
            <span v-if="card.job_code" class="card-job">{{ card.job_code }}</span>
          </div>

          <div class="card-meta">
            <span v-if="card.client_name" class="card-client">{{ card.client_name }}</span>
            <span v-if="card.location" class="card-location">{{ card.location }}</span>
          </div>

          <div class="card-footer">
            <span v-if="deadlineInfo(card)" class="deadline-badge" :class="deadlineInfo(card)!.severity">
              {{ deadlineInfo(card)!.label }}
            </span>
            <div class="card-right">
              <span v-if="card.total_outstanding > 0" class="card-outstanding">
                {{ formatCurrency(card.total_outstanding) }}
              </span>
              <span
                v-if="card.pm_name"
                class="pm-avatar"
                :class="{ 'has-image': card.pm_avatar_url }"
                :title="card.pm_name"
              >
                <img v-if="card.pm_avatar_url" :src="card.pm_avatar_url" :alt="initials(card.pm_name)" />
                <span v-else>{{ initials(card.pm_name) }}</span>
              </span>
            </div>
          </div>
        </div>

        <div v-if="col.projects.length === 0" class="kanban-empty">No projects</div>
      </div>
    </div>
    </div>
  </div>
</template>

<style scoped>
.kanban-loading {
  padding: 3rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

/* --- Filter toolbar --- */
.kanban-toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.toolbar-search {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1 1 260px;
  min-width: 200px;
}
.toolbar-search .pi {
  position: absolute;
  left: 0.625rem;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  pointer-events: none;
}
.toolbar-search input {
  width: 100%;
  padding: 0.4375rem 2rem 0.4375rem 1.875rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
}
.toolbar-search input:focus {
  outline: none;
  border-color: var(--p-primary-color);
}
.search-clear {
  position: absolute;
  right: 0.375rem;
  background: none;
  border: none;
  color: var(--p-text-muted-color);
  cursor: pointer;
  padding: 0.25rem;
  font-size: 0.75rem;
}
.search-clear:hover {
  color: var(--p-text-color);
}
.toolbar-filters {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.toolbar-select {
  padding: 0.4375rem 0.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: 0.8125rem;
  max-width: 200px;
}
.toolbar-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--p-text-color);
  cursor: pointer;
  white-space: nowrap;
}
.toolbar-toggle input {
  accent-color: var(--p-primary-color);
}
.toolbar-clear {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.375rem 0.625rem;
  font-size: 0.75rem;
  color: var(--p-primary-color);
  cursor: pointer;
  white-space: nowrap;
}
.toolbar-clear:hover {
  background: var(--p-content-hover-background);
}

.kanban-board {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  overflow-x: auto;
  padding-bottom: 1rem;
}

.kanban-column {
  /* Stretch columns to fill the available width — no narrow cap. */
  flex: 1 1 0;
  min-width: 240px;
  background: var(--p-surface-100);
  border-radius: 0.625rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 180px);
  transition: background 0.15s, outline 0.15s;
}
.app-dark .kanban-column {
  background: var(--p-surface-900);
}
.kanban-column.drag-over {
  background: var(--p-primary-100);
  outline: 2px dashed var(--p-primary-color);
}

/* Collapsed empty column → thin vertical strip (Hermes-style) */
.kanban-column.collapsed {
  flex: 0 0 44px;
  min-width: 44px;
  cursor: pointer;
  justify-content: center;
  align-items: center;
  transition: flex-basis 0.15s ease, min-width 0.15s ease;
}
.kanban-column.collapsed .kanban-column-header {
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 0.25rem;
}
.kanban-column.collapsed .kanban-column-label {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.kanban-column.collapsed .kanban-count {
  margin-left: 0;
}
.kanban-column.collapsed:hover {
  background: var(--p-surface-200);
}
.app-dark .kanban-column.collapsed:hover {
  background: var(--p-surface-800);
}

.kanban-column-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.25rem 0.75rem;
}

.kanban-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--p-surface-400);
}
.kanban-dot.lead { background: var(--p-amber-500); }
.kanban-dot.proposal { background: var(--p-cyan-500); }
.kanban-dot.contract { background: var(--p-blue-500); }
.kanban-dot.active { background: var(--p-green-600); }
.kanban-dot.complete { background: var(--p-primary-color); }
.kanban-dot.archive { background: var(--p-surface-500); }

.kanban-column-label {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-color);
  text-transform: capitalize;
}

.kanban-count {
  margin-left: auto;
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 1rem;
  padding: 0.125rem 0.5rem;
}
.kanban-sort {
  margin-left: 0.375rem;
  display: flex;
  align-items: center;
}
.kanban-sort-select {
  border: 1px solid transparent;
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: 0.6875rem;
  padding: 0.125rem 0.25rem;
  border-radius: 0.375rem;
  cursor: pointer;
  max-width: 150px;
}
.kanban-sort-select:hover,
.kanban-sort-select:focus {
  border-color: var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  outline: none;
}

.kanban-column-body {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  overflow-y: auto;
  min-height: 60px;
}

.kanban-card {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 0.75rem;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.15s, transform 0.15s;
}
.kanban-card:hover {
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
}
.kanban-card.dragging {
  opacity: 0.5;
  transform: rotate(2deg);
}
.kanban-card.drop-top {
  box-shadow: 0 -3px 0 0 var(--p-primary-color);
}
.kanban-card.drop-bottom {
  box-shadow: 0 3px 0 0 var(--p-primary-color);
}

.card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}
.card-title {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-color);
  line-height: 1.3;
  word-break: break-word;
}
.card-job {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
  margin-top: 0.125rem;
}

.card-meta {
  margin-top: 0.375rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}
.card-client {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.card-location {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.card-footer {
  margin-top: 0.625rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.card-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
}

.deadline-badge {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
  white-space: nowrap;
}
.deadline-badge.overdue {
  background: var(--p-red-50, #fef2f2);
  color: var(--p-red-600, #dc2626);
}
.deadline-badge.soon {
  background: var(--p-amber-50, #fffbeb);
  color: var(--p-amber-600, #d97706);
}
.deadline-badge.normal {
  color: var(--p-text-muted-color);
}

.card-outstanding {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--p-red-600);
}

.pm-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--p-surface-200);
  color: var(--p-surface-600);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6rem;
  font-weight: 600;
  flex-shrink: 0;
  overflow: hidden;
}
.pm-avatar.has-image {
  background: transparent;
}
.pm-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.kanban-empty {
  padding: 1rem;
  text-align: center;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  border: 1px dashed var(--p-content-border-color);
  border-radius: 0.5rem;
}
</style>
