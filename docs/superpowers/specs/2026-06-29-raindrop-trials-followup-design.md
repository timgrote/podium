# Raindrop Trials Follow-up List — Design

**Date:** 2026-06-29
**Author:** Tim (with Pi)
**Status:** Awaiting review

## Problem

Raindrop trial licenses are issued through KeyGen. When a user starts a trial, the
desktop app collects their **name** and **email** and stores them on the trial
license (`attributes.name` and `attributes.metadata.email`). Today that data just
sits in KeyGen — there is no place to see who is on a trial or whose trial recently
lapsed. Tim wants a single view of **active trials** and **trials that expired in the
last 30 days**, with name, email, and dates, so he can optionally send follow-up
emails ("any questions?").

## Goal

Add a **Trials** panel to the existing Raindrop Analytics page in Podium that lists:

1. **Active trials** — trials whose `expiry` is in the future.
2. **Recently expired** — trials whose `expiry` falls within the last 30 days (rolling).

Each row shows: Name, Email, Started (created date), Expires/Expired date, and a
day count (days remaining for active; days since expiry for expired). Each row has a
**copy-email button**.

## Non-goals (YAGNI)

- No mailto links, no CSV export (Tim chose copy-email only).
- No server-side caching — fetch live from KeyGen on each load.
- No editing/managing trials from Podium (read-only view).
- No automated/scheduled follow-up emails — this is a manual reference list.
- No paid/full license reporting — trials only.

## Verified facts (live-tested against KeyGen, 2026-06-29)

- **KeyGen Cloud** (`api.keygen.sh`).
- **Account ID:** `40280a53-8cd5-4b54-9813-04727b10810f` (non-secret; baked into the
  Raindrop desktop binary — `src/raindrop/Activation/LicenseService.cs`).
- **Trial policy ID:** `42090eb8-6372-40b3-b6b9-fe5e6e6e058b` (non-secret; same source).
- **Token:** a `prod-` product token, stored as `KEYGEN_API` in the `.env` attachment
  on the `ai-env` KeePass entry (`/mnt/d/Vaults/Keepass/DevEnv.kdbx`). Secret —
  supplied to the server via env var, never committed.
- Listing trials: `GET /v1/accounts/{account}/licenses?policy={trialPolicy}&page[number]=N&page[size]=100`
  with headers `Authorization: Bearer {token}` and `Accept: application/vnd.api+json`.
  Pagination **requires** `page[number]` (not just `page[size]`).
- Each license `attributes` includes: `name`, `metadata.email`, `created`, `expiry`,
  `status` (`ACTIVE` / `EXPIRED` / `SUSPENDED` / `EXPIRING` / …). Trials run 30 days.

## Architecture

Mirrors the existing Raindrop analytics pattern: **service → `/api/raindrop/*`
router → panel in `RaindropAnalyticsView.vue`**.

```
RaindropAnalyticsView.vue (Trials panel)
        ↓  GET /api/raindrop/trials
app/routers/raindrop_analytics.py
        ↓
app/services/keygen_client.py  →  api.keygen.sh
```

### Backend

**`app/config.py`** — add:
- `keygen_api_token: str = ""`  (env: `CONDUCTOR_KEYGEN_API_TOKEN`) — secret.
- `keygen_account_id: str = "40280a53-8cd5-4b54-9813-04727b10810f"` — non-secret default.
- `keygen_trial_policy_id: str = "42090eb8-6372-40b3-b6b9-fe5e6e6e058b"` — non-secret default.

**`app/services/keygen_client.py`** (new) — one focused responsibility: talk to KeyGen.
- `fetch_trial_licenses() -> list[dict]`: pages through the trial policy
  (`page[size]=100`, incrementing `page[number]` until a short/empty page), using
  `httpx` (matching `app/services/loki_client.py`, with a `timeout`).
  Returns raw normalized dicts: `{name, email, created, expiry, status}`.
- Returns `[]` and logs a warning if the token is unset or the API errors (the panel
  degrades gracefully rather than 500-ing the page). Never raises into the request.

**`app/routers/raindrop_analytics.py`** — add `GET /trials`:
- Calls `fetch_trial_licenses()`, then splits/derives in Python (not from KeyGen
  `status`, to keep the 30-day rule authoritative):
  - `active` = `expiry > now`, sorted by soonest expiry first; each gets
    `days_remaining`.
  - `expired_recent` = `now - 30d <= expiry <= now`, sorted most-recently-expired
    first; each gets `days_since_expiry`.
- Response shape:
  ```json
  {
    "active":  [{"name","email","created","expiry","days_remaining"}],
    "expired_recent": [{"name","email","created","expiry","days_since_expiry"}],
    "active_count": N,
    "expired_recent_count": M,
    "available": true
  }
  ```
  `available: false` when the token is unset, so the UI can show "not configured"
  instead of an empty list.

### Frontend

**`frontend/src/api/raindrop.ts`** — add `RaindropTrial`, `RaindropTrials` types and
`getRaindropTrials(): Promise<RaindropTrials>`.

**`frontend/src/views/RaindropAnalyticsView.vue`** — add a **Trials panel** (its own
section, independent of the `days` period picker since trials aren't windowed by it):
- Header: "Trials" with active/expired counts.
- Two `DataTable`s (PrimeVue, matching existing tables): **Active Trials** and
  **Recently Expired (last 30 days)**.
- Columns: Name, Email, Started, Expires (active) / Expired (expired), Days.
- Email column body: the address plus a small copy-to-clipboard button
  (`pi-copy` icon) that writes the email to the clipboard and shows a toast/checkmark.
- Fetched on mount via its own loader (separate from the analytics loader so a KeyGen
  hiccup doesn't break the rest of the dashboard). Loading spinner + graceful
  "KeyGen not configured" / "no trials" empty states.

## Data flow

1. View mounts → calls `getRaindropTrials()`.
2. Router calls `keygen_client.fetch_trial_licenses()` → paginates KeyGen → normalized list.
3. Router derives `active` / `expired_recent` from `expiry` vs now, adds day counts.
4. View renders two tables; copy button copies the email.

## Error handling

- **Token unset:** service returns `[]`; router returns `available: false`; UI shows
  "KeyGen not configured." No crash.
- **KeyGen API error / timeout:** service logs a warning, returns `[]`; UI shows an
  error/empty state with a retry, rest of dashboard unaffected.
- **Malformed license (missing email/name):** normalize to empty string; still listed
  so Tim sees the trial exists.

## Testing

- **Unit (backend):** `fetch_trial_licenses` pagination (stops correctly), and the
  router's active/expired-30d split + day-count math, using a mocked KeyGen response
  (fixtures with ACTIVE, expired-10-days-ago, expired-40-days-ago, future-expiry).
  Assert the 40-days-ago one is excluded and the 10-days-ago one is included.
- **Manual:** load the Raindrop Analytics page on local dev (`:5173`), confirm the
  Trials panel renders real active trials and copy-email works. (Token must be set in
  the local backend env to see live data.)

## Deployment

- Production Podium (`tie-conductor`) needs `CONDUCTOR_KEYGEN_API_TOKEN` added to the
  `conductor-api.service` systemd `Environment=`. **Flag this to Tim before deploy** —
  without it the panel shows "not configured" in prod. Token value comes from the
  `KEYGEN_API` KeePass entry; set it on the box directly, never commit it.
- No DB migration (read-only external data; nothing stored locally).
