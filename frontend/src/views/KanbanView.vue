<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { KanbanBoard, KanbanCard, KanbanColumn } from '../types'
import { getBoard, moveCard } from '../api/kanban'
import { useToast } from '../composables/useToast'
import { parseLocalDate, formatDateShort } from '../utils/dates'

const router = useRouter()
const toast = useToast()

const board = ref<KanbanBoard | null>(null)
const loading = ref(false)

// Drag state
const dragging = ref<KanbanCard | null>(null)
const dragOverStatus = ref<string | null>(null)

const columns = computed<KanbanColumn[]>(() => board.value?.columns ?? [])

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
function onDragStart(card: KanbanCard) {
  dragging.value = card
}
function onDragEnd() {
  dragging.value = null
  dragOverStatus.value = null
}

function onDragEnter(status: string) {
  dragOverStatus.value = status
}

async function onDrop(status: string) {
  const card = dragging.value
  dragOverStatus.value = null
  if (!card) return

  // No-op: dropped back into its own column with no reorder target.
  if (card.status === status) {
    dragging.value = null
    return
  }

  const targetCol = columns.value.find((c) => c.status === status)
  const insertIndex = targetCol ? targetCol.projects.length : 0

  try {
    board.value = await moveCard({ project_id: card.id, status, board_order: insertIndex })
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
  <div class="kanban">
    <div class="kanban-header">
      <div class="header-left">
        <h1>Kanban</h1>
        <router-link class="board-toggle" to="/kanban/tasks">
          <i class="pi pi-check-square" /> Task Board
        </router-link>
      </div>
      <button class="btn-refresh" @click="load" :disabled="loading" title="Refresh board">
        <i class="pi pi-refresh" :class="{ spin: loading }" />
      </button>
    </div>

    <div v-if="loading && !board" class="kanban-loading">
      <i class="pi pi-spin pi-spinner" /> Loading board…
    </div>

    <div v-else class="kanban-board">
      <div
        v-for="col in columns"
        :key="col.status"
        class="kanban-column"
        :class="{ 'drag-over': dragOverStatus === col.status }"
        @dragover.prevent
        @dragenter.prevent="onDragEnter(col.status)"
        @drop.prevent="onDrop(col.status)"
      >
        <div class="kanban-column-header">
          <span class="kanban-dot" :class="col.status"></span>
          <span class="kanban-column-label">{{ col.label }}</span>
          <span class="kanban-count">{{ cardCount(col) }}</span>
        </div>

        <div class="kanban-column-body">
          <div
            v-for="card in col.projects"
            :key="card.id"
            class="kanban-card"
            :class="{ dragging: dragging?.id === card.id }"
            draggable="true"
            @dragstart="onDragStart(card)"
            @dragend="onDragEnd"
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
.kanban {
  max-width: 1400px;
  margin: 0 auto;
}

.kanban-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.kanban-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.board-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--p-primary-color);
  text-decoration: none;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
}
.board-toggle:hover {
  background: var(--p-content-hover-background);
}

.btn-refresh {
  background: none;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  color: var(--p-text-muted-color);
}
.btn-refresh:hover {
  background: var(--p-content-hover-background);
  color: var(--p-text-color);
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.kanban-loading {
  padding: 3rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

.kanban-board {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  overflow-x: auto;
  padding-bottom: 1rem;
}

.kanban-column {
  flex: 1 1 0;
  min-width: 240px;
  max-width: 280px;
  background: var(--p-surface-100);
  border-radius: 0.625rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 140px);
  transition: background 0.15s, outline 0.15s;
}
.app-dark .kanban-column {
  background: var(--p-surface-900);
}
.kanban-column.drag-over {
  background: var(--p-primary-100);
  outline: 2px dashed var(--p-primary-color);
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
