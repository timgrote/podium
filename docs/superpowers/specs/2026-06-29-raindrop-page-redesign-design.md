# Raindrop Analytics Page Redesign — Design

**Date:** 2026-06-29
**Author:** Tim (with Pi)
**Status:** Approved — building
**Builds on:** `2026-06-29-raindrop-trials-followup-design.md` (Trials panel, branch `raindrop-trials-followup`)

## Problem

The Raindrop Analytics page grew organically: exceptions are buried below the fold,
the stats bar sits in the middle, the leaderboard is tied to the 7/14/30-day picker,
and there's no quick way to grab an exception for triage. Tim wants the page reordered
around what he checks most, two new headline numbers (licensed + active-trial users),
a month-scoped leaderboard, and a one-click way to copy an exception log for pasting to
an agent.

## Goal

Reorder and extend the Raindrop Analytics page:

1. **Stats bar at top**, with two new cards: **Licensed Users** (active Yearly licenses)
   and **Active Trials** (active trial licenses), alongside the existing Loki stats.
2. **Exceptions pane** next, with a **Copy Log** button per exception that copies a
   formatted log entry (time, user/machine, version, drawing, message, full stack trace).
3. **Trials pane** next (the panel from the prior spec, moved into this position).
4. Below: charts, insights, and a **Leaderboard scoped to the current calendar month**,
   decoupled from the day selector.

Final order: **Stats → Exceptions → Trials → Charts → Insights → Leaderboard → Warnings.**

## Decisions (from Tim)

- Licensed Users = **active Yearly licenses only** (count, currently 7).
- The 7/14/30 **day selector stays** and continues to drive the charts and the Loki
  summary stats. The **leaderboard is always the current calendar month** (1st → today),
  independent of the selector.
- Exceptions: **Copy Log only** for now (no GitHub link yet — that's a later phase toward
  the agent-triage workflow).
- Lower layout order: charts → insights → leaderboard (then existing warnings table).

## Non-goals (YAGNI)

- No GitHub issue search/create yet.
- No filtering of orphan/duplicate trials (e.g. Ahmed Shawky's repeated trials) — tracked
  separately; the active-trials count will include them for now.
- No new caching; KeyGen and Loki fetched live as today.

## Verified facts

- KeyGen policies: **Trial** `42090eb8-6372-40b3-b6b9-fe5e6e6e058b`,
  **Yearly** `04745663-d270-44e0-a281-478bd6dae04e`. Active Yearly = 7 (live-tested).
- `aggregate_dashboard(entries, start_date, end_date)` returns a dict including
  `user_stats` (the leaderboard rows) and `period` — reusable for a month-scoped query.
- Existing exception objects carry: `timestamp, user, machine, message, drawing,
  app_version, level, exception (obj|str), stack_trace`.

## Architecture

### Backend

**`app/config.py`** — add `keygen_yearly_policy_id: str = "04745663-d270-44e0-a281-478bd6dae04e"`.

**`app/services/keygen_client.py`** — generalize the fetch so trials and licensed-count
share one code path:
- `fetch_licenses(policy_id: str) -> list[dict]` — the existing pagination/normalization,
  parameterized by policy. Returns `{name, email, created, expiry, status}` dicts.
- `fetch_trial_licenses()` — thin wrapper: `fetch_licenses(settings.keygen_trial_policy_id)`.
- `count_active_licenses(policy_id: str) -> int` — `fetch_licenses` then count `status == "ACTIVE"`.

**`app/routers/raindrop_analytics.py`**
- `GET /trials` — add `licensed_active_count` to the response
  (`count_active_licenses(settings.keygen_yearly_policy_id)`, or 0 when token unset).
- New `GET /leaderboard` — queries Loki for the current calendar month
  (`{app="raindrop"} |= "Drawing Closed"`, start = 1st of month 00:00:00, end = now),
  runs `aggregate_dashboard`, returns `{user_stats, period}`.

### Frontend

**`frontend/src/api/raindrop.ts`**
- Add `licensed_active_count: number` to `RaindropTrials`.
- Add `RaindropLeaderboard { user_stats: UserStat[]; period: { start: string; end: string } }`
  and `getRaindropLeaderboard(): Promise<RaindropLeaderboard>`.

**`frontend/src/views/RaindropAnalyticsView.vue`**
- State: `leaderboard` ref + `loadLeaderboard()`; load it in `onMounted` alongside the
  others. Leaderboard no longer reads `analytics.user_stats`.
- Generalize `copyEmail` into `copyToClipboard(text, label)`; add `formatExceptionLog(exc)`
  and `copyExceptionLog(exc)` (reuses the same success/error toast).
- Reorder the dashboard template to: **Stats bar → Exceptions → Trials → Charts →
  Insights → Leaderboard → Warnings.** Move the Trials panel out of its current
  top-of-page spot into the Trials position.
- Stats bar: prepend two cards — **Licensed Users** (`trials?.licensed_active_count`) and
  **Active Trials** (`trials?.active_count`), shown as `—` until the trials fetch resolves.
- Exceptions: add a **Copy Log** button in each expanded exception's detail
  (`@click.stop`), calling `copyExceptionLog(exc)`.
- Leaderboard: title "User Leaderboard (this month)", `:value="leaderboard.user_stats"`,
  gated on `leaderboard && leaderboard.user_stats.length`.

**Copy-log format** (plain text, for pasting to an agent):

```
Raindrop Exception
Time: <timestamp>
User: <user> (<machine>)
Version: <app_version>
Drawing: <drawing>
Level: <level>
Message: <message>
Exception: <Type>: <Message>

Stack trace:
<stack_trace>
```

(Empty fields are omitted.)

## Error handling

- KeyGen token unset → `licensed_active_count: 0`, `available: false` (already handled).
- Leaderboard Loki failure → `query_loki_range` returns `[]` → empty leaderboard, no crash.
- Copy buttons → success/error toast; clipboard `NotAllowedError` only occurs in headless
  automation, not real browsers on localhost/HTTPS.

## Testing

- **Backend unit:** `count_active_licenses` counts only ACTIVE (mocked KeyGen); `/trials`
  includes `licensed_active_count`; `/leaderboard` queries a current-month range
  (assert `start.day == 1`) and returns `{user_stats, period}`.
- **Manual/browser:** verify order Stats→Exceptions→Trials→Charts→Insights→Leaderboard,
  the two new stat cards show real numbers, Copy Log copies a formatted block, leaderboard
  header says "(this month)".

## Deployment

Same as the prior spec — prod still just needs `CONDUCTOR_KEYGEN_API_TOKEN`. No new env
vars (the Yearly policy id is a non-secret config default). No DB migration.
