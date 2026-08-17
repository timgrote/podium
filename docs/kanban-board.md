# Kanban Views (Projects · Tasks · Invoices)

Conductor ships Kanban boards as **view modes** — you toggle between the existing
list view and a Kanban board on each page, or open a dedicated board route.

## The three boards

| Board | Where | Columns |
|-------|-------|---------|
| **Projects** | `/kanban` | Lead → Proposal → Contract → Active → Complete → Archive |
| **Tasks** | Toggle on **My Tasks** (`/my-tasks`) or `/kanban/tasks` | To Do → In Progress → Blocked → Done → Canceled |
| **Invoices** | Toggle on **Financial** (`/financial`) | Draft → Ready to Send → Sent → Partial → Paid |

## How it works

- **Drag a card** between columns to change its status. Cards reorder within a
  column by dragging to a target slot; `board_order` / `sort_order` stay dense
  (0..n) after every move.
- **Click a card**:
  - Projects & tasks → opens the project view.
  - Invoices → opens the invoice edit modal.
- **Projects board** (persisted) — cards live in the ordinary `projects` table;
  the board is a *calculated projection* grouped by the existing `status` column
  and ordered by the `board_order` column. No separate "Kanban table" is stored.
- **Tasks board** — `project_tasks` already had `status` + `sort_order`, so it
  needed **no DB migration**. The optional `assignee` filter makes the board
  respect the My Tasks page's "Just me" scope.
- **Invoice board** — built **client-side** from the already-loaded invoices
  (`GET /api/invoices` returns `sent_status`, `paid_status`, `total_due`,
  `data_path`). Moving a card calls the existing `updateInvoice` endpoint, so no
  backend change was needed.

## Main code changes

| File | Change |
|------|--------|
| `app/routers/kanban.py` *(new)* | Projects board (`GET /api/kanban`, `POST /api/kanban/move`) + task board (`GET /api/kanban/tasks` w/ `assignee` filter, `POST /api/kanban/tasks/move`) |
| `app/main.py` | Register kanban router at `/api/kanban` |
| `frontend/src/api/kanban.ts` *(new)* | `getBoard`, `moveCard`, `getTaskBoard(assignee)`, `moveTaskCard` |
| `frontend/src/views/KanbanView.vue` *(new)* | Projects board (route `/kanban`) |
| `frontend/src/components/kanban/TasksBoard.vue` *(new)* | Reusable task board (drag/drop, assignee filter) |
| `frontend/src/views/TasksKanbanView.vue` | Thin wrapper → `TasksBoard` (route `/kanban/tasks`) |
| `frontend/src/components/kanban/InvoiceBoard.vue` *(new)* | Invoice board (drag = `updateInvoice`) |
| `frontend/src/views/MyTasksView.vue` | List/Kanban toggle button + embedded `TasksBoard` |
| `frontend/src/views/FinancialView.vue` | List/Kanban toggle button + embedded `InvoiceBoard` |
| `frontend/src/router/index.ts` | `/kanban`, `/kanban/tasks` routes |
| `frontend/src/layouts/DashboardLayout.vue` | "Kanban" sidebar item |
| `frontend/src/types/index.ts` | `KanbanCard`, `KanbanTaskCard`, `InvoiceBoard` types |
| `frontend/src/components/modals/ProjectModal.vue` | Add missing `proposal` / `contract` status options |
| `tests/test_kanban.py` *(new)* | 12 tests (projects + tasks boards) |

## Database change (one migration)

`db/migrations/034_add_project_board_order.sql` adds a single column:

```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS board_order INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_projects_board ON projects(status, board_order);
```

- `board_order` = in-column ordering for **projects**. Tasks and invoices reuse
  existing columns (`sort_order`, `sent_status`, `paid_status`) — **no new schema**
  for those.
- Additive, `IF NOT EXISTS`, filename tracked by the deploy script. **Do not edit
  `baseline.sql`.**

## Verification (all green)

- `pytest tests/ -q` → **49 passed** (includes 12 kanban tests).
- `npm run build` (frontend) → passes.
- Live test server at **http://127.0.0.1:3001**:
  - Projects: 6 columns from local snapshot (lead 25 / proposal 1 / contract 9 /
    active 47 / complete 2 / archive 4).
  - Tasks: 318 top-level tasks; `assignee` filter verified (Tim → 131, bogus → 0).
  - Invoices: 63 across Draft/Ready/Sent/Partial/Paid.

## Deploy

Auto-deploys on push to `master` (GitHub Actions → `scripts/deploy.sh`). The
deploy script applies new migrations by filename, so `034_*.sql` runs on its own.

```
git add -A
git commit -m "feat(kanban): Kanban views for projects, tasks, and invoices"
git push origin master
```

Local test server: `bash scripts/start-local.sh` → **http://127.0.0.1:3001**
(`qa_test@conductor.test` / `testtest`). Note: the built SPA is served from
`frontend/dist` each request, but the FastAPI process must be restarted after a
backend (`.py`) change for new API routes — `--reload` handles this; if a stale
process holds the port, kill it before restarting.
