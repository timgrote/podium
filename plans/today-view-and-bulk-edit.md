# Plan: Today View, Bulk Edit, and Stale Task Hygiene

*Drafted 2026-05-12 with Tim. Goal: make the My Tasks page actually useful and stop the task list from becoming a graveyard.*

This plan is self-contained — open the podium repo in a fresh session and hand this file to the agent.

---

## Progress (resume here)

**Shipped to prod 2026-05-12:**

- ✅ Part 0 — doc fixes (already done before this plan landed; `tie-conductor` / `165.232.148.72` in CLAUDE.md)
- ✅ Part 7 step 2 — Backend filter params + bulk PATCH + done-today + is_stale (commit `35324ba`)
  - `GET /api/tasks/my` and `/api/projects/{id}/tasks`: `due_before`, `due_after`, `stale`, `status` csv, `assignee`, `no_due_date`
  - `PATCH /api/tasks/bulk` — all-or-nothing, allowed fields: `due_date`, `status`, `assignee_ids`, `priority`
  - `GET /api/tasks/done-today?employee_id=&today=YYYY-MM-DD` (client passes local date; no TZ migration needed)
  - `is_stale` computed on task responses (true if `updated_at < now-30d` and status not done/archived/canceled)
  - 12 pytest tests in `tests/test_my_tasks_v2.py`
  - Side fixes: `schema.sql` had `idx_clients_email` referencing dropped column (renamed to accounting_email in migration 016); and `projects.pm_id` missing (added in migration 011 but never synced to schema.sql). Both fixed; all tests in the repo were broken before this.
- ✅ Part 7 step 3 — My Tasks three-section layout + filter chips (commit `c71a9ef`)
  - Done today / Up Next (or active filter) / Later sections
  - Up Next has adaptive fill: 3-day window extends to 14d if <3 tasks would show
  - Filter chips: Up Next | This Week | Overdue | No due date | Stale, each with live counts, plus Projects multi-select chip
  - Search spans all sections; Later is project-grouped, collapsed by default
  - New API helpers: `getDoneToday`, `bulkUpdateTasks` (helper ready for step 5)
  - New date helpers in `frontend/src/utils/dates.ts`: `addDaysStr`, `nextMondayStr`, `isoWeekRange`

**Defaults chosen on Tim's behalf (revisit when convenient):**
- "Push to next week" = next Monday
- Week in Review visible to everyone, filterable to "my projects"
- No WIP limit on Up Next
- Archived lives forever (no hard-delete)
- 30-day stale / 90-day auto-archive, org-wide

**Known incidental:** `/home/tim/repos/package.json` and `/home/tim/repos/podium/package.json` are deliberate 0-byte sentinel stubs (along with sibling `.env`/`.npmrc`/`.yarnrc` files dated Apr 13) blocking npm/vite from walking the directory tree. They break local `npm run dev` because 0 bytes isn't valid JSON; should be `{}`. Tim doesn't run local dev so this is unblocked. Fix later if you ever want vite dev server back.

**Next up (in order):**
4. Inline row chips: `→ Tomorrow`, `→ Next Mon`, 📅 date picker on hover
5. Bulk selection (checkboxes, shift-click) + floating bottom action bar
6. Stale filter chip is wired on My Tasks; weekly review surface still pending
7. Week in Review page (`/review/week`)
8. End-of-day digest at 5pm local
9. `archived` status + 90-day auto-archive job (feature-flagged)

---

## Context (read first)

- Frontend: SvelteKit (or Vue — see `frontend/`); API client in `frontend/src/api/client.ts` uses relative `/api`.
- Backend: FastAPI, Postgres. Task model in `app/`; routes under `app/routes/tasks.py` and `app/routes/projects.py` (verify on entry).
- Live API: `http://tie-conductor` (Tailscale `100.64.170.40`). My-Tasks UI is at `http://tie-conductor/my-tasks`.
- "Mine" means tasks with the current user in `assignees`. Tasks without assignees do **not** appear on /my-tasks even if they're on a user's personal project. The bulk-edit and filter work in this plan must always scope by assignee, never by project.

## Problems we're solving

1. **No filters on My Tasks.** Only search. So you can't say "show me what actually matters this week."
2. **No bulk edit.** Pushing 20+ overdue tasks to next week takes 20+ clicks.
3. **No decay.** Tasks created six months ago sit next to tasks created yesterday with equal weight. The list loses trust, then loses use.
4. **No feedback loop.** Closing a task disappears it. There's no sense of "look what got done today."
5. **Tasks aren't "next actions."** A lot of TIE work is recurring obligations (invoicing, follow-ups) that don't fit the GTD next-action mold.

---

## Part 0 — Fix the deployment docs (do this first, it's 5 minutes)

The current docs in this repo point at the wrong droplet. The live Conductor responds at `tie-conductor` (Tailscale `100.64.170.40`); `24.144.82.75` / `100.105.238.37` are stale and unreachable.

Edits required:

- `CLAUDE.md` line 69: change `ssh root@100.105.238.37 "cd /var/www/conductor && bash scripts/deploy.sh"` → `ssh root@tie-conductor "cd /var/www/conductor && bash scripts/deploy.sh"`
- `CLAUDE.md` line 74: change `**Droplet:** `24.144.82.75` (public), `100.105.238.37` (Tailscale: `tie-conductor`)` → reflect the real droplet. Before editing, run `ssh tie-conductor 'curl -s ifconfig.me; tailscale ip -4'` to capture the truth, then write the correct public + Tailscale IPs.
- `DEPLOYMENT.md`: grep for any other references to the old IPs and update or remove.

Add a short note in `CLAUDE.md` near the droplet block:

> The Tailscale name `tie-conductor` is the source of truth. If IPs change, only update DNS / Tailscale — do not pin IPs in this file.

---

## Part 1 — My Tasks page redesign

### Three sections, top to bottom

1. **Done today** (collapsible, default open)
   - Tasks where `completed_at >= today 00:00 (local)` and `assignees` includes current user.
   - Sorted most-recent-first.
   - Visible win pile — when you click a task in "Up Next," it animates down into here. That's the feedback loop.
   - Empty state: "Nothing checked off yet today."

2. **Up Next** (the action list)
   - Default filter: `due_date <= today + 3 days` AND `status != done` AND assignee = me.
   - **Adaptive fill:** if Up Next has fewer than 3 tasks, extend the window forward until at least 3 show, or until 14 days out — whichever comes first. Rationale: if today is light because you punted everything, you should see next week peeking through, not stare at an empty page.
   - Sort: `due_date asc, priority desc, created_at asc`.

3. **Later** (collapsed by default)
   - Everything else open and assigned to me.
   - Lets users stop pretending it doesn't exist without forcing them to triage it constantly.

### Filter chips (above Up Next)

- **Up Next** (default — the today+3 window with adaptive fill)
- **This week** — `due_date` within current ISO week
- **Overdue only** — `due_date < today AND status != done`
- **No due date** — orphan tasks
- **By project** — multi-select chips
- **Stale** — `updated_at < today - 30 days AND status != done` (links to the weekly review)

Keep existing search behavior.

---

## Part 2 — Bulk reschedule UX

### Primary surface: Task screen (My Tasks)

Project view gets the same component, but My Tasks is the primary triage surface. Same React/Svelte component, two mount points.

### Selection model

- Checkbox column on each row, hidden by default; appears on hover or once any task is checked.
- **Shift-click** for range select within the visible filtered list.
- "Select all in Up Next" / "Select all overdue" header actions.
- Floating bulk-action bar slides up from the bottom once 1+ tasks are selected (Gmail pattern). Counts: "N selected."

### Bulk actions in the bar

| Action | Behavior |
|---|---|
| **Push to tomorrow** | Sets `due_date = today + 1`. |
| **Push to next week** | Sets `due_date = next Monday`. |
| **Reschedule…** | Opens date picker for arbitrary date. |
| **Reassign…** | Opens assignee picker (multi-select). |
| **Mark done** | Bulk complete. |
| **Delete** | With confirm. |

Tim's decision pending on: two named buttons (Tomorrow, Next Week) vs three (Today, Tomorrow, Next Week). Recommendation: two buttons + Reschedule picker. "Today" is rarely the desired bulk action — it would just un-reschedule. Keep the bar lean.

### One-click row actions (no selection needed)

On every row, three small chips visible on hover:

- `→ Tomorrow`
- `→ Next Mon`
- `📅` (open date picker)

Inline rescheduling for the 80% case where you're working one task at a time.

### Backend: bulk PATCH endpoint

```
PATCH /api/tasks/bulk
Body: { "task_ids": ["task-x", ...], "patch": { "due_date": "2026-05-19" } }
Response: 200 + array of updated tasks
```

Single transaction. Reject if any `task_id` doesn't exist or the user lacks permission. All-or-nothing semantics.

Allowed fields in `patch`: `due_date`, `status`, `assignee_ids`, `priority`. Reject anything else.

---

## Part 3 — Stale task hygiene

### Auto-stale flag (computed, query-time)

- `is_stale = true` when `updated_at < now() - interval '30 days' AND status NOT IN ('done', 'archived')`.
- Returned on every task serialization. Not stored.
- Drives the **Stale** filter chip and the Week-in-Review.

### Auto-archive (Phase 2, behind a feature flag)

- Job runs nightly: tasks with `updated_at < now() - interval '90 days' AND status NOT IN ('done', 'archived')` → set `status = 'archived'`.
- Archived tasks are restorable to `todo` from the UI.
- Distinct from `done` so we can tell "this died" from "this got finished."

---

## Part 4 — Week in Review page

New top-level route: `/review/week` (or a tab under My Tasks — pick one and commit).

### Sections

1. **What got done this week**
   - All tasks where `completed_at` within current ISO week, grouped by assignee.
   - Counts per person at the top — "Tim: 12 done, Ally: 7 done, Matara: 4 done."
   - Healthy social pressure without a leaderboard.

2. **What's stale**
   - List of `is_stale` tasks across the org (or filtered to my projects — pick a default; let users toggle).
   - Each row has two one-click buttons: **Push to Monday** | **Archive**.
   - Plus a `📅` for arbitrary date.
   - Goal: blow through 30+ stale tasks in under 5 minutes during a Friday review.

3. **Still open this week**
   - `due_date` within current week, not done. Sorted by assignee, then due date.

4. **Coming up next week**
   - Read-only preview. Helps the Monday kickoff.

### Weekly review prompt

Sunday night or Monday morning, send each active user a digest email/notification:

- "You have N stale tasks. [Review them →]"
- Links to /review/week with Stale tab open.

---

## Part 5 — Daily "what did I do" loop

Mostly covered by "Done today" at the top of My Tasks. Also add:

- **End-of-day digest** at 5pm local (configurable): "You closed N tasks today: [list]. M still open for today. [Push remaining to tomorrow?]"
- One-button "Push remaining to tomorrow" in the digest — links to a pre-confirmed bulk PATCH.

---

## Part 6 — Schema / API changes

Most of this is frontend-only. Backend additions:

1. **Query params** on `GET /projects/{id}/tasks` and a new `GET /tasks/mine`:
   - `?due_before=YYYY-MM-DD`
   - `?due_after=YYYY-MM-DD`
   - `?stale=true`
   - `?status=todo,in_progress`
   - `?assignee=emp-xxx` (or `me`)

2. **Bulk PATCH endpoint:** see Part 2.

3. **New status value:** `archived`. Distinct from `done`. Migration: add to enum / check constraint, no existing rows change.

4. **Computed `is_stale`** on task serialization (boolean).

5. **`GET /tasks/done-today?assignee=me`** — fast endpoint for the "Done today" section. Just `completed_at >= today 00:00 (user TZ)`.

6. **User timezone:** verify the user model has a `timezone` field (default `America/Denver` for Tim). All "today"/"this week" computations must use it. Add if missing.

---

## Part 7 — Build order

Each step ships independently.

1. **Part 0 — Doc fixes.** 5 minutes.
2. **Backend filter params + bulk PATCH endpoint.** Smallest, unblocks everything else.
3. **My Tasks: three-section layout + filter chips.** Biggest visible win.
4. **Inline row chips for `→ Tomorrow` / `→ Next Mon`.**
5. **Bulk selection + bottom action bar.**
6. **Stale flag + Stale filter.**
7. **Week in Review page.**
8. **End-of-day digest.**
9. **Archived status + 90-day auto-archive (feature-flagged).**

---

## Open questions

- **WIP limit on Up Next?** Cap at 5? Useful pressure, but invoicing alone can be 3 tasks. Try without; revisit after a week.
- **Who sees the Week in Review by default — everyone, or just PMs?**
- **Archive vs delete:** Live forever in `archived`, or hard delete after 1 year?
- **"Push to next week" = next Monday vs today + 7?** Default to next Monday; expose a setting if it bothers people.
- **Per-user vs org-wide stale threshold?** Probably per-org config, default 30/90.

## Test plan (rough)

- Backend: unit tests on the bulk PATCH (all-or-nothing semantics, permission rejection, field allowlist). Integration test on filter params.
- Frontend: component tests on the three-section layout adaptive fill (0, 1, 3, 10 task cases). Cypress test on bulk select → push to next week → verify all rows now show next Monday.
- Manual: from Tim's account, load /my-tasks with the new layout and confirm overdue count drops to expected (0 today after a triage session).

## Out of scope (for this plan)

- Notifications system overhaul.
- Mobile-specific touch interactions (revisit after web ships).
- Recurring task semantics — important, separate plan.
- Permission model changes — keep existing.
