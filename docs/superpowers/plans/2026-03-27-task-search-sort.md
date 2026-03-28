# Task Search and Sort Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a search bar and sortable column headers to the active tasks section of the project view.

**Architecture:** New `useProjectTasks` composable handles search filtering and sort state, returning a `filteredTasks` computed. `ProjectTasks.vue` gets a search bar and column header row above the active tasks list, using the same patterns as `ProjectList.vue`.

**Tech Stack:** Vue 3, TypeScript, PrimeVue icons

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `frontend/src/composables/useProjectTasks.ts` | Search filtering and sort logic for project tasks |
| Modify | `frontend/src/components/project/ProjectTasks.vue` | Add search bar, column headers, wire up composable |

---

### Task 1: Create `useProjectTasks` composable

**Files:**
- Create: `frontend/src/composables/useProjectTasks.ts`

- [ ] **Step 1: Create the composable**

```typescript
import { computed, ref, type Ref } from 'vue'
import type { Task } from '../types'

type SortField = 'title' | 'due_date' | 'assignee'

export function useProjectTasks(activeTasks: Ref<Task[]>) {
  const searchQuery = ref('')
  const sortField = ref<SortField | null>(null)
  const sortOrder = ref<'asc' | 'desc'>('asc')

  function toggleSort(field: SortField) {
    if (sortField.value === field) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortField.value = field
      sortOrder.value = field === 'due_date' ? 'desc' : 'asc'
    }
  }

  const filteredTasks = computed(() => {
    let result = activeTasks.value

    // Search filter
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      result = result.filter((t) => {
        if (t.title.toLowerCase().includes(q)) return true
        if (t.assignees?.some(a =>
          (a.first_name || '').toLowerCase().includes(q) ||
          (a.last_name || '').toLowerCase().includes(q)
        )) return true
        return false
      })
    }

    // Sort
    if (sortField.value) {
      const field = sortField.value
      const order = sortOrder.value === 'asc' ? 1 : -1
      result = [...result].sort((a, b) => {
        if (field === 'title') {
          return a.title.localeCompare(b.title) * order
        }
        if (field === 'due_date') {
          const aVal = a.due_date
          const bVal = b.due_date
          if (aVal == null && bVal == null) return 0
          if (aVal == null) return 1
          if (bVal == null) return -1
          return (new Date(aVal).getTime() - new Date(bVal).getTime()) * order
        }
        if (field === 'assignee') {
          const aName = a.assignees?.[0]?.first_name || null
          const bName = b.assignees?.[0]?.first_name || null
          if (aName == null && bName == null) return 0
          if (aName == null) return 1
          if (bName == null) return -1
          return aName.localeCompare(bName) * order
        }
        return 0
      })
    }

    return result
  })

  return {
    searchQuery,
    sortField,
    sortOrder,
    toggleSort,
    filteredTasks,
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/composables/useProjectTasks.ts
git commit -m "feat: add useProjectTasks composable for search and sort"
```

---

### Task 2: Add search bar and column headers to ProjectTasks.vue

**Files:**
- Modify: `frontend/src/components/project/ProjectTasks.vue`

- [ ] **Step 1: Import and wire up the composable**

In the `<script setup>` section, add the import after the existing imports (after line 11):

```typescript
import { useProjectTasks } from '../../composables/useProjectTasks'
```

After the `activeTasks` computed (after line 45), add:

```typescript
const { searchQuery, sortField, sortOrder, toggleSort, filteredTasks } = useProjectTasks(activeTasks)
```

- [ ] **Step 2: Add search bar template**

Insert between the new task form (after line 244, `</div>` closing `new-task-form`) and the loading state (line 246). This goes right before `<div v-if="tasksLoading"`:

```vue
    <!-- Task search -->
    <div v-if="!tasksLoading && activeTasks.length > 0" class="task-search-bar">
      <i class="pi pi-search" />
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search tasks..."
      />
      <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''">
        <i class="pi pi-times" />
      </button>
    </div>
```

- [ ] **Step 3: Add column headers template**

Insert right after the search bar, before the `<!-- Active tasks -->` comment (before line 250):

```vue
    <!-- Column headers -->
    <div v-if="!tasksLoading && activeTasks.length > 0" class="task-column-headers">
      <div class="col-checkbox"></div>
      <div class="col-name sortable" @click="toggleSort('title')">
        Name
        <i v-if="sortField === 'title'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
      <div class="col-assignee sortable" @click="toggleSort('assignee')">
        Assignee
        <i v-if="sortField === 'assignee'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
      <div class="col-status">Status</div>
      <div class="col-link"></div>
      <div class="col-due sortable" @click="toggleSort('due_date')">
        Due
        <i v-if="sortField === 'due_date'" class="pi" :class="sortOrder === 'asc' ? 'pi-sort-up' : 'pi-sort-down'" />
      </div>
    </div>
```

- [ ] **Step 4: Replace `activeTasks` with `filteredTasks` in the template**

Change line 250-251 from:

```vue
      <div v-if="activeTasks.length" class="tasks-list">
        <template v-for="task in activeTasks" :key="task.id">
```

To:

```vue
      <div v-if="filteredTasks.length" class="tasks-list">
        <template v-for="task in filteredTasks" :key="task.id">
```

Also add a "no results" message after the tasks-list div, before the completed section:

```vue
      <div v-if="activeTasks.length && !filteredTasks.length" class="empty">
        No tasks matching "{{ searchQuery }}"
      </div>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/project/ProjectTasks.vue
git commit -m "feat: add search bar and column headers to project tasks"
```

---

### Task 3: Add styles for search bar and column headers

**Files:**
- Modify: `frontend/src/components/project/ProjectTasks.vue`

- [ ] **Step 1: Add CSS to the `<style scoped>` section**

Append before the closing `</style>` tag:

```css
.task-search-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.5rem;
}

.task-search-bar i {
  color: var(--p-text-muted-color);
}

.task-search-bar input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 0.8125rem;
  background: transparent;
  color: var(--p-text-color);
}

.task-search-bar .search-clear {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.125rem;
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  display: flex;
  align-items: center;
}

.task-search-bar .search-clear:hover {
  color: var(--p-text-color);
}

.task-column-headers {
  display: flex;
  align-items: center;
  padding: 0.375rem 0.25rem;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.025em;
  gap: 0.5rem;
  border-bottom: 1px solid var(--p-content-border-color);
  margin-bottom: 0.25rem;
}

.task-column-headers .sortable {
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.task-column-headers .sortable:hover {
  color: var(--p-text-color);
}

.task-column-headers .sortable .pi {
  font-size: 0.5625rem;
}

.col-checkbox { width: 16px; flex-shrink: 0; }
.col-name { flex: 1; min-width: 0; }
.col-assignee { width: 4.5rem; flex-shrink: 0; }
.col-status { width: 5rem; flex-shrink: 0; }
.col-link { width: 1.25rem; flex-shrink: 0; }
.col-due { width: 5rem; flex-shrink: 0; text-align: right; justify-content: flex-end; }
```

- [ ] **Step 2: Verify in browser**

Run: `cd frontend && npm run dev`

Open the project view with tasks. Verify:
1. Search bar appears above the task list
2. Typing filters tasks by title and assignee name
3. Clear button appears when search has text
4. Column headers show Name, Assignee, Status, Due
5. Clicking Name/Assignee/Due sorts the list
6. Clicking again toggles asc/desc
7. Sort icon appears on active column
8. Completed tasks section is unaffected
9. "No tasks matching" message appears when search has no results

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/project/ProjectTasks.vue
git commit -m "feat: style task search bar and sortable column headers"
```
