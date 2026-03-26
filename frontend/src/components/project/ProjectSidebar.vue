<script setup lang="ts">
import { computed } from 'vue'

export type Section = 'tasks' | 'notes' | 'time' | 'contracts' | 'invoices' | 'proposals' | 'team'

const props = defineProps<{
  activeSection: Section
  taskCount?: number
  notesCount?: number
  teamCount?: number
  totalHours?: number
  contractCount?: number
  invoiceCount?: number
  proposalCount?: number
  folderHref?: string | null
}>()

const emit = defineEmits<{
  'update:activeSection': [section: Section]
}>()

interface NavItem {
  id: Section | 'documents'
  label: string
  count?: number | string
  external?: boolean
  href?: string
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const groups = computed<NavGroup[]>(() => [
  {
    label: 'Work',
    items: [
      { id: 'tasks', label: 'Tasks', count: props.taskCount || undefined },
      { id: 'notes', label: 'Notes', count: props.notesCount || undefined },
      { id: 'time', label: 'Time', count: props.totalHours ? `${Number(props.totalHours).toFixed(1)}h` : undefined },
    ],
  },
  {
    label: 'Financial',
    items: [
      { id: 'contracts', label: 'Contracts', count: props.contractCount || undefined },
      { id: 'invoices', label: 'Invoices', count: props.invoiceCount || undefined },
      { id: 'proposals', label: 'Proposals', count: props.proposalCount || undefined },
    ],
  },
  {
    label: 'People & Files',
    items: [
      { id: 'team', label: 'Team', count: props.teamCount || undefined },
      ...(props.folderHref ? [{ id: 'documents' as const, label: 'Documents', external: true, href: props.folderHref }] : []),
    ],
  },
])
</script>

<template>
  <nav class="project-sidebar">
    <div v-for="group in groups" :key="group.label" class="nav-group">
      <div class="group-label">{{ group.label }}</div>
      <template v-for="item in group.items" :key="item.id">
        <a
          v-if="item.external"
          :href="item.href"
          class="nav-item"
          title="Open project folder"
        >
          <i class="pi pi-folder-open" />
          <span>{{ item.label }}</span>
        </a>
        <button
          v-else
          class="nav-item"
          :class="{ active: activeSection === item.id }"
          @click="emit('update:activeSection', item.id as Section)"
        >
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.count" class="nav-count">{{ item.count }}</span>
        </button>
      </template>
    </div>
  </nav>
</template>

<style scoped>
.project-sidebar {
  width: 180px;
  flex-shrink: 0;
  border-right: 1px solid var(--p-content-border-color);
  padding: 1rem 0;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.nav-group {
  display: flex;
  flex-direction: column;
}

.group-label {
  font-size: 0.5625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--p-text-muted-color);
  padding: 0 1rem 0.375rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4375rem 1rem;
  background: none;
  border: none;
  border-left: 2px solid transparent;
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
  text-align: left;
  width: 100%;
  text-decoration: none;
  transition: all 0.1s;
}

.nav-item:hover {
  color: var(--p-text-color);
  background: var(--p-content-hover-background);
}

.nav-item.active {
  color: var(--p-text-color);
  border-left-color: var(--p-primary-color);
  background: var(--p-content-hover-background);
  font-weight: 500;
}

.nav-label {
  flex: 1;
}

.nav-count {
  font-size: 0.6875rem;
  color: var(--p-text-muted-color);
}

.nav-item.active .nav-count {
  color: var(--p-primary-color);
}
</style>
