<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ProjectSummary } from '../../types'
import type { ActivityItem } from '../../api/activityLog'

const props = defineProps<{
  item: ActivityItem
  projects: ProjectSummary[]
}>()

const emit = defineEmits<{
  assigned: [data: { project_id: string; remember: boolean; pattern: string }]
  cancel: []
}>()

const search = ref('')
const remember = ref(true)

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return props.projects.slice(0, 10)
  return props.projects.filter(
    (p) =>
      (p.project_name || '').toLowerCase().includes(q) ||
      (p.job_code || '').toLowerCase().includes(q),
  ).slice(0, 10)
})

function extractPattern(sourcePath: string): string {
  // Extract a meaningful path fragment for mapping
  // e.g., "D:\Projects\TBG\HeronLakes\file.dwg" -> "TBG/HeronLakes"
  const normalized = sourcePath.replace(/\\/g, '/')
  const parts = normalized.split('/')
  // Find the last 2-3 directory segments before the filename
  const dirs = parts.slice(0, -1)
  if (dirs.length >= 2) {
    return dirs.slice(-2).join('/')
  }
  return dirs[dirs.length - 1] || normalized
}

function assign(projectId: string) {
  const pattern = props.item.source_path ? extractPattern(props.item.source_path) : ''
  emit('assigned', {
    project_id: projectId,
    remember: remember.value,
    pattern,
  })
}
</script>

<template>
  <div class="assign-popover" @click.stop>
    <input
      v-model="search"
      type="text"
      placeholder="Search projects..."
      class="assign-search"
      autofocus
    />
    <div class="assign-list">
      <div
        v-for="p in filtered"
        :key="p.id"
        class="assign-option"
        @click="assign(p.id)"
      >
        <span class="assign-name">{{ p.project_name }}</span>
        <span v-if="p.job_code" class="assign-code">{{ p.job_code }}</span>
      </div>
      <div v-if="filtered.length === 0" class="assign-empty">No projects found</div>
    </div>
    <label class="assign-remember">
      <input v-model="remember" type="checkbox" />
      Remember this path
    </label>
    <button class="assign-cancel" @click="emit('cancel')">Cancel</button>
  </div>
</template>

<style scoped>
.assign-popover {
  position: absolute;
  right: 0;
  top: 100%;
  z-index: 10;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  padding: 0.5rem;
  width: 280px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.assign-search {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.25rem;
  font-size: 0.8125rem;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  width: 100%;
}

.assign-list {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.assign-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.8125rem;
}

.assign-option:hover {
  background: var(--p-content-hover-background);
}

.assign-name { font-weight: 500; }
.assign-code { font-size: 0.75rem; color: var(--p-text-muted-color); }

.assign-empty {
  padding: 0.5rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  text-align: center;
}

.assign-remember {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  padding: 0.25rem 0;
  cursor: pointer;
}

.assign-remember input { cursor: pointer; }

.assign-cancel {
  background: none;
  border: none;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  cursor: pointer;
  text-align: left;
  padding: 0.25rem 0;
}

.assign-cancel:hover { color: var(--p-text-color); }
</style>
