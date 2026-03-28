# Task Search and Sort in Project View

## Problem

Viewing a project with many tasks is overwhelming. There's no way to find a specific task or reorder the list by meaningful columns.

## Solution

Add a search bar and sortable column headers to the active tasks section of `ProjectTasks.vue`, following the existing patterns from the projects list.

## Scope

- Active tasks only. Completed tasks section is unaffected.
- Client-side filtering and sorting — no API changes.
- Subtasks are included in search/sort results when their parent matches, but subtasks themselves are not independently surfaced by search.

## Search Bar

- Positioned above the task list, below the "Add task" controls.
- Matches the `ProjectList.vue` search bar pattern: input with `pi-search` icon, clear button on non-empty input.
- Filters active tasks by case-insensitive substring match on:
  - `title`
  - Assignee `first_name` and `last_name`
- Immediate filtering (no debounce needed — client-side, small dataset).

## Sortable Column Headers

Replace the current unstyled task list with a header row containing three sortable columns:

| Column | Field | Default direction | Null handling |
|--------|-------|-------------------|---------------|
| Name | `title` | asc | N/A (always present) |
| Due Date | `due_date` | desc | Nulls sort to end |
| Assignee | First assignee's `first_name` | asc | Unassigned sort to end |

Click a column header to sort by that field. Click again to toggle asc/desc. Active sort column shows `pi-sort-up` or `pi-sort-down` icon, matching the projects list pattern.

Default sort on page load: current behavior (sort_order, created_at from API).

## Implementation

### New composable: `useProjectTasks.ts`

Handles search and sort state for project tasks. Accepts a reactive array of tasks and returns:

- `searchQuery` — ref<string>
- `sortField` — ref<'title' | 'due_date' | 'assignee' | null>
- `sortOrder` — ref<'asc' | 'desc'>
- `toggleSort(field)` — function
- `filteredTasks` — computed array (search-filtered, then sorted active tasks)

Sort logic follows `useProjects.ts`:
- String fields: `localeCompare()`
- Date fields: `new Date().getTime()` comparison
- Assignee: compare `first_name` of first assignee via `localeCompare()`
- Nulls always sort to end regardless of direction

### Changes to `ProjectTasks.vue`

- Import and use `useProjectTasks` composable
- Add search bar markup above task list (copy pattern from `ProjectList.vue`)
- Add column header row with sortable columns
- Replace `activeTasks` iteration with `filteredTasks` from composable
- Completed tasks section unchanged

### Styling

- Reuse existing CSS variables and patterns from `ProjectList.vue`
- Column header row: flex layout matching the task item row structure
- `.sortable` class with cursor pointer and hover state
- Search bar uses same `.search-bar` styles

## What This Does NOT Include

- Search/sort on completed tasks
- Server-side sorting or pagination
- Status or priority column sorting (can be added later)
- Persistent sort preferences
