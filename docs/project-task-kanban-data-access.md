# Project Task Data Access (project Kanban board)

Module: `frontend/src/api/projectTasks.ts`

Purpose: the single data-access layer the project-level Kanban board (inside the
conductor project view) uses to load a project's tasks and persist status/order
changes. It deliberately **does not** build UI — the board and drag-and-drop
consume these functions.

## Statuses

The task status set matches the canonical columns already defined server-side in
`app/routers/kanban.py` (`TASK_COLUMNS`) and the `Task.status` union in
`frontend/src/types/index.ts`:

| status        | label       | column order |
|---------------|-------------|--------------|
| `todo`        | To Do       | 0            |
| `in_progress` | In Progress | 1            |
| `blocked`     | Blocked     | 2            |
| `done`        | Done        | 3            |
| `canceled`    | Canceled    | 4            |

`projectTasks.ts` re-exports `TASK_STATUSES`, `TASK_STATUS_LABELS`, and a
`TaskStatus` type so the board and any future callers share one source of truth.

## API contract

| Function | Signature | Backend endpoint |
|----------|-----------|------------------|
| `listTasks` | `listTasks(projectId: string): Promise<Task[]>` | `GET /api/projects/{projectId}/tasks` |
| `updateTaskStatus` | `updateTaskStatus(projectId, taskId, newStatus, newPosition): Promise<void>` | `POST /api/kanban/tasks/move` |

- **`listTasks`** calls the existing project-scoped list endpoint and returns
  tasks sorted for the board: by status column (canonical order), then
  pinned-first, then `sort_order`, then `created_at`. Unknown statuses sort last
  so nothing is ever hidden.
- **`updateTaskStatus`** delegates to the existing `POST /api/kanban/tasks/move`,
  which sets the task's status, places it at the requested `sort_order` slot,
  and reindexes the source + destination columns so `sort_order` stays dense
  (0..n). `projectId` is kept in the signature because the board is
  project-scoped; the move endpoint is keyed on `task_id`, and the board only
  drags tasks already belonging to that project, so no extra server check is
  needed. Throws on unknown status (before any network call) and on API failure
  — the caller owns optimistic-UI rollback.

## Persistence

No backend change or DB migration was required:

- Task `status` and `sort_order` already live on `project_tasks`.
- The Kanban move endpoint already persists a cross-column move plus
  within-column position and keeps ordering dense.
- The project-scoped list endpoint already filters to a single project and
  excludes subtasks (`parent_id IS NULL`).

## Tests

`frontend/src/__tests__/projectTasks.test.ts` covers:

- the exact status set and labels;
- `isTaskStatus` narrowing;
- `sortTasksForBoard` (status order, pin-first, unknown-status-last,
  input immutability);
- `listTasks` contract (endpoint called, result sorted);
- `updateTaskStatus` contract (move payload, unknown-status rejection).
