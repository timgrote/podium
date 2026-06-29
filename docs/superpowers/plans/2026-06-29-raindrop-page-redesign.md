# Raindrop Analytics Page Redesign Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Reorder the Raindrop Analytics page (Stats → Exceptions → Trials → Charts → Insights → Leaderboard), add Licensed Users + Active Trials stat cards, a Copy Log button on exceptions, and a current-month leaderboard.

**Architecture:** Generalize the KeyGen client to count active Yearly licenses; add `licensed_active_count` to `/trials` and a new `/leaderboard` (current month). Restructure `RaindropAnalyticsView.vue` template + add copy-log helpers.

**Tech Stack:** FastAPI, httpx, pydantic-settings; Vue 3 + TS + PrimeVue; pytest.

## Global Constraints

- Builds on branch `raindrop-trials-followup` (Trials feature already present).
- KeyGen Yearly policy id `04745663-d270-44e0-a281-478bd6dae04e` is a non-secret config default.
- Licensed Users = count of Yearly licenses with `status == "ACTIVE"`.
- Day selector keeps driving charts + Loki summary; leaderboard = current calendar month, independent.
- Copy-log is plain text, omitting empty fields; uses the existing toast.
- Frontend tests/build run from `frontend/`; backend tests need `conductor_test` DB.

---

### Task 1: KeyGen licensed-count + config

**Files:**
- Modify: `app/config.py`
- Modify: `app/services/keygen_client.py`
- Test: `tests/test_keygen_client.py`

**Interfaces:**
- Produces: `fetch_licenses(policy_id: str) -> list[dict]`; `fetch_trial_licenses() -> list[dict]` (unchanged signature); `count_active_licenses(policy_id: str) -> int`.

- [ ] **Step 1: Add Yearly policy config**

In `app/config.py`, under the KeyGen block, add after `keygen_trial_policy_id`:

```python
    keygen_yearly_policy_id: str = "04745663-d270-44e0-a281-478bd6dae04e"
```

- [ ] **Step 2: Write the failing test**

Append to `tests/test_keygen_client.py`:

```python
def test_count_active_licenses(monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")
    licenses = [
        {"id": "1", "name": "A", "email": "a@x.com", "created": "2026-01-01T00:00:00.000Z",
         "expiry": "2027-01-01T00:00:00.000Z", "status": "ACTIVE"},
        {"id": "2", "name": "B", "email": "b@x.com", "created": "2025-01-01T00:00:00.000Z",
         "expiry": "2026-01-01T00:00:00.000Z", "status": "EXPIRED"},
        {"id": "3", "name": "C", "email": "c@x.com", "created": "2026-01-01T00:00:00.000Z",
         "expiry": "2027-01-01T00:00:00.000Z", "status": "ACTIVE"},
    ]

    def fake_get(url, params=None, headers=None, timeout=None):
        return _FakeResp(_page(licenses))

    monkeypatch.setattr(kc.httpx, "get", fake_get)
    assert kc.count_active_licenses("any-policy") == 2


def test_count_active_licenses_empty_when_token_unset(monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "")
    assert kc.count_active_licenses("any-policy") == 0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_keygen_client.py::test_count_active_licenses -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'count_active_licenses'`.

- [ ] **Step 4: Refactor keygen_client and add the function**

In `app/services/keygen_client.py`, rename the body of `fetch_trial_licenses` into a generic `fetch_licenses(policy_id)`, keep `fetch_trial_licenses` as a wrapper, and add `count_active_licenses`. Replace the whole `fetch_trial_licenses` definition with:

```python
def fetch_licenses(policy_id: str) -> list[dict]:
    """Fetch all licenses under a policy from KeyGen.

    Returns normalized dicts ``{name, email, created, expiry, status}``.
    Returns ``[]`` if the token is unset or on any HTTP error (never raises).
    """
    token = settings.keygen_api_token
    if not token:
        logger.warning("CONDUCTOR_KEYGEN_API_TOKEN not set; skipping license fetch")
        return []

    url = f"{KEYGEN_BASE}/accounts/{settings.keygen_account_id}/licenses"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.api+json",
    }

    results: list[dict] = []
    page = 1
    try:
        while True:
            params = {
                "policy": policy_id,
                "page[number]": page,
                "page[size]": PAGE_SIZE,
            }
            resp = httpx.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            for lic in data:
                attrs = lic.get("attributes", {})
                results.append({
                    "name": attrs.get("name") or "",
                    "email": (attrs.get("metadata") or {}).get("email") or "",
                    "created": attrs.get("created"),
                    "expiry": attrs.get("expiry"),
                    "status": attrs.get("status"),
                })
            if len(data) < PAGE_SIZE:
                break
            page += 1
    except Exception as e:
        logger.warning(f"KeyGen license fetch failed: {e}")
        return []

    return results


def fetch_trial_licenses() -> list[dict]:
    """Fetch all Raindrop trial licenses (the trial policy)."""
    return fetch_licenses(settings.keygen_trial_policy_id)


def count_active_licenses(policy_id: str) -> int:
    """Count licenses under a policy whose status is ACTIVE."""
    return sum(1 for lic in fetch_licenses(policy_id) if lic.get("status") == "ACTIVE")
```

- [ ] **Step 5: Run all keygen_client tests**

Run: `pytest tests/test_keygen_client.py -v`
Expected: PASS (the original 3 still pass + 2 new).

- [ ] **Step 6: Commit**

```bash
git add app/config.py app/services/keygen_client.py tests/test_keygen_client.py
git commit -m "feat: add count_active_licenses for licensed-user count"
```

---

### Task 2: `licensed_active_count` on /trials + `/leaderboard` endpoint

**Files:**
- Modify: `app/routers/raindrop_analytics.py`
- Test: `tests/test_raindrop_trials.py`

**Interfaces:**
- Consumes: `count_active_licenses`, `fetch_trial_licenses`, `aggregate_dashboard`, `query_loki_range`.
- Produces: `/trials` response gains `licensed_active_count: int`; new `GET /leaderboard` → `{user_stats: list, period: dict}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_raindrop_trials.py`:

```python
def test_trials_includes_licensed_active_count(client, monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")
    monkeypatch.setattr(ra, "fetch_trial_licenses", lambda: [])
    monkeypatch.setattr(ra, "count_active_licenses", lambda policy_id: 7)
    body = client.get("/api/raindrop/trials").json()
    assert body["licensed_active_count"] == 7


def test_leaderboard_uses_current_month(client, monkeypatch):
    captured = {}

    def fake_query(logql, start, end, limit=5000):
        captured["start"] = start
        captured["end"] = end
        return []

    monkeypatch.setattr(ra, "query_loki_range", fake_query)
    r = client.get("/api/raindrop/leaderboard")
    assert r.status_code == 200
    body = r.json()
    assert "user_stats" in body and "period" in body
    assert captured["start"].day == 1            # first of the current month
    assert captured["start"].hour == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_raindrop_trials.py::test_trials_includes_licensed_active_count tests/test_raindrop_trials.py::test_leaderboard_uses_current_month -v`
Expected: first FAILs on missing `licensed_active_count`; second FAILs with 404.

- [ ] **Step 3: Import the new helpers**

In `app/routers/raindrop_analytics.py`, update the import lines:

```python
from ..services.keygen_client import count_active_licenses, fetch_trial_licenses
from ..services.loki_analytics import aggregate_dashboard, aggregate_errors, aggregate_events, query_loki_range
```

(The second line is unchanged but confirm `aggregate_dashboard` and `query_loki_range` are imported — they already are.)

- [ ] **Step 4: Add `licensed_active_count` to the trials response**

In the `get_trials` function, change the early-return (token unset) block to include the field:

```python
    if not settings.keygen_api_token:
        return {
            "active": [], "expired_recent": [],
            "active_count": 0, "expired_recent_count": 0,
            "licensed_active_count": 0, "available": False,
        }
```

And change the final `return` to add the licensed count (compute it just before the return):

```python
    licensed_active_count = count_active_licenses(settings.keygen_yearly_policy_id)

    return {
        "active": active, "expired_recent": expired,
        "active_count": len(active), "expired_recent_count": len(expired),
        "licensed_active_count": licensed_active_count, "available": True,
    }
```

- [ ] **Step 5: Add the `/leaderboard` endpoint**

Append to `app/routers/raindrop_analytics.py`:

```python
@router.get("/leaderboard")
def get_leaderboard():
    """User leaderboard for the current calendar month (independent of the day selector)."""
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59)
    logql = '{app="raindrop"} |= "Drawing Closed"'
    entries = query_loki_range(logql, start, end)
    dashboard = aggregate_dashboard(entries, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    return {"user_stats": dashboard["user_stats"], "period": dashboard["period"]}
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_raindrop_trials.py -v`
Expected: PASS (the original 2 + 2 new).

- [ ] **Step 7: Commit**

```bash
git add app/routers/raindrop_analytics.py tests/test_raindrop_trials.py
git commit -m "feat: add licensed_active_count to /trials and current-month /leaderboard"
```

---

### Task 3: Frontend API types

**Files:**
- Modify: `frontend/src/api/raindrop.ts`

**Interfaces:**
- Produces: `RaindropTrials.licensed_active_count`; `RaindropLeaderboard` type; `getRaindropLeaderboard()`.

- [ ] **Step 1: Add the licensed count field**

In `frontend/src/api/raindrop.ts`, add to the `RaindropTrials` interface:

```typescript
  licensed_active_count: number
```

- [ ] **Step 2: Add the leaderboard type + fetch**

Append after `getRaindropTrials`:

```typescript
export interface RaindropLeaderboard {
  user_stats: UserStat[]
  period: { start: string; end: string }
}

export function getRaindropLeaderboard(): Promise<RaindropLeaderboard> {
  return apiFetch('/raindrop/leaderboard')
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: no new errors referencing `raindrop.ts`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/raindrop.ts
git commit -m "feat: add leaderboard API + licensed_active_count type"
```

---

### Task 4: View — copy-log helpers + leaderboard state

**Files:**
- Modify: `frontend/src/views/RaindropAnalyticsView.vue` (script only)

**Interfaces:**
- Consumes: `getRaindropLeaderboard`, `RaindropLeaderboard`, `RaindropException`.
- Produces: `leaderboard` ref, `loadLeaderboard`, `copyToClipboard`, `formatExceptionLog`, `copyExceptionLog`.

- [ ] **Step 1: Add imports**

Change the api import line to add the leaderboard fn, and the type import to add the types:

```typescript
import { getRaindropAnalytics, getRaindropExceptions, getRaindropWarnings, getRaindropTrials, getRaindropLeaderboard } from '../api/raindrop'
import type { RaindropAnalytics, RaindropExceptions, RaindropWarnings, RaindropTrials, RaindropLeaderboard, RaindropException } from '../api/raindrop'
```

- [ ] **Step 2: Add leaderboard state**

After the `trials*` refs, add:

```typescript
const leaderboard = ref<RaindropLeaderboard | null>(null)
```

- [ ] **Step 3: Generalize copy + add exception-log helpers**

Replace the existing `copyEmail` function with a shared helper plus the email and exception wrappers:

```typescript
async function copyToClipboard(text: string, label: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('Copied', label)
  } catch {
    toast.error('Copy failed')
  }
}

function copyEmail(email: string) {
  return copyToClipboard(email, email)
}

function formatExceptionLog(exc: RaindropException): string {
  const ex = typeof exc.exception === 'object'
    ? `${exc.exception.Type}: ${exc.exception.Message}`
    : (exc.exception || '')
  return [
    'Raindrop Exception',
    `Time: ${exc.timestamp}`,
    `User: ${exc.user}${exc.machine ? ` (${exc.machine})` : ''}`,
    exc.app_version ? `Version: ${exc.app_version}` : '',
    exc.drawing ? `Drawing: ${exc.drawing}` : '',
    `Level: ${exc.level}`,
    `Message: ${exc.message}`,
    ex ? `Exception: ${ex}` : '',
    exc.stack_trace ? `\nStack trace:\n${exc.stack_trace}` : '',
  ].filter(Boolean).join('\n')
}

function copyExceptionLog(exc: RaindropException) {
  return copyToClipboard(formatExceptionLog(exc), 'Exception log')
}
```

- [ ] **Step 4: Add the leaderboard loader and call it on mount**

After `loadTrials`, add:

```typescript
async function loadLeaderboard() {
  try {
    leaderboard.value = await getRaindropLeaderboard()
  } catch {
    leaderboard.value = null
  }
}
```

Change the `onMounted` block to also load the leaderboard:

```typescript
onMounted(() => {
  load()
  loadTrials()
  loadLeaderboard()
})
```

- [ ] **Step 5: Build to verify the script compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds (template still references the old leaderboard until Task 5, but `analytics.user_stats` still exists, so it compiles).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/RaindropAnalyticsView.vue
git commit -m "feat: add copy-log + leaderboard state to Raindrop view"
```

---

### Task 5: View — reorder template + new stat cards + Copy Log button + month leaderboard

**Files:**
- Modify: `frontend/src/views/RaindropAnalyticsView.vue` (template)

**Interfaces:** Consumes everything from Task 4.

- [ ] **Step 1: Remove the Trials panel from its current top-of-page position**

Delete the entire `<!-- Trials Panel -->` block (the `<div class="trials-panel">…</div>`) that currently sits between the `page-header` close and the `<!-- Loading -->` comment. It will be re-inserted in Step 4 inside the dashboard, after Exceptions. (Leave the `trials-panel` CSS in place.)

- [ ] **Step 2: Move the Stats bar to the top of the dashboard and add two cards**

In the `<template v-else-if="analytics">` block, move the `<!-- Stat Cards -->` `<div class="stats-bar">…</div>` so it is the FIRST child (before the Exceptions panel). Then, as the first two cards inside `stats-bar`, prepend:

```html
        <div class="stat-card">
          <div class="stat-label">Licensed Users</div>
          <div class="stat-value accent">{{ trials ? trials.licensed_active_count : '—' }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Active Trials</div>
          <div class="stat-value">{{ trials ? trials.active_count : '—' }}</div>
        </div>
```

- [ ] **Step 3: Add the Copy Log button to each exception**

In the `exception-detail` div, after the `<pre v-if="exc.stack_trace" …>` line and before the div closes, add:

```html
              <button class="copy-log-btn" @click.stop="copyExceptionLog(exc)">
                <i class="pi pi-copy"></i> Copy Log
              </button>
```

- [ ] **Step 4: Re-insert the Trials panel after the Exceptions panel**

Immediately after the Exceptions panel's closing `</div>` (the `exceptions-panel` div) and before the charts, insert the Trials panel block (identical to the one removed in Step 1):

```html
      <!-- Trials Panel -->
      <div class="trials-panel">
        <div class="trials-header">
          <i class="pi pi-id-card"></i>
          <h2>Trials</h2>
          <span class="trials-counts" v-if="trials && trials.available">
            {{ trials.active_count }} active · {{ trials.expired_recent_count }} expired (30d)
          </span>
        </div>

        <div v-if="trialsLoading" class="trials-state"><ProgressSpinner style="width:32px;height:32px" /></div>
        <div v-else-if="trialsError" class="trials-state">{{ trialsError }}</div>
        <div v-else-if="trials && !trials.available" class="trials-state">KeyGen not configured.</div>
        <template v-else-if="trials">
          <div class="table-section">
            <h3>Active Trials</h3>
            <p v-if="!trials.active.length" class="trials-state">No active trials.</p>
            <DataTable v-else :value="trials.active" stripedRows size="small"
                       :paginator="trials.active.length > 10" :rows="10" sortField="days_remaining" :sortOrder="1">
              <Column field="name" header="Name" sortable />
              <Column field="email" header="Email">
                <template #body="{ data }">
                  <span class="email-cell">{{ data.email }}
                    <button class="copy-btn" @click="copyEmail(data.email)" title="Copy email">
                      <i class="pi pi-copy"></i>
                    </button>
                  </span>
                </template>
              </Column>
              <Column field="created" header="Started" sortable>
                <template #body="{ data }">{{ formatTrialDate(data.created) }}</template>
              </Column>
              <Column field="expiry" header="Expires" sortable>
                <template #body="{ data }">{{ formatTrialDate(data.expiry) }}</template>
              </Column>
              <Column field="days_remaining" header="Days Left" sortable>
                <template #body="{ data }">{{ data.days_remaining }}d</template>
              </Column>
            </DataTable>
          </div>

          <div class="table-section">
            <h3>Recently Expired (last 30 days)</h3>
            <p v-if="!trials.expired_recent.length" class="trials-state">None expired in the last 30 days.</p>
            <DataTable v-else :value="trials.expired_recent" stripedRows size="small"
                       :paginator="trials.expired_recent.length > 10" :rows="10" sortField="days_since_expiry" :sortOrder="1">
              <Column field="name" header="Name" sortable />
              <Column field="email" header="Email">
                <template #body="{ data }">
                  <span class="email-cell">{{ data.email }}
                    <button class="copy-btn" @click="copyEmail(data.email)" title="Copy email">
                      <i class="pi pi-copy"></i>
                    </button>
                  </span>
                </template>
              </Column>
              <Column field="created" header="Started" sortable>
                <template #body="{ data }">{{ formatTrialDate(data.created) }}</template>
              </Column>
              <Column field="expiry" header="Expired On" sortable>
                <template #body="{ data }">{{ formatTrialDate(data.expiry) }}</template>
              </Column>
              <Column field="days_since_expiry" header="Days Ago" sortable>
                <template #body="{ data }">{{ data.days_since_expiry }}d ago</template>
              </Column>
            </DataTable>
          </div>
        </template>
      </div>
```

- [ ] **Step 5: Point the Leaderboard at the month data**

Replace the `<!-- User Leaderboard -->` block's wrapper condition, heading, and DataTable value:

```html
      <!-- User Leaderboard (current month) -->
      <div class="table-section" v-if="leaderboard && leaderboard.user_stats.length">
        <h2>User Leaderboard (this month)</h2>
        <DataTable :value="leaderboard.user_stats" stripedRows size="small">
```

(Leave the `<Column>` definitions inside unchanged.)

- [ ] **Step 6: Add Copy Log button styling**

In `<style scoped>`, append:

```css
.copy-log-btn {
  margin-top: 0.5rem;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border: 1px solid var(--surface-border, #e5e7eb);
  background: var(--surface-card, #fff);
  color: var(--text-color, #374151);
  font-size: 0.8rem;
  padding: 0.3rem 0.6rem;
  border-radius: 6px;
  cursor: pointer;
}
.copy-log-btn:hover { border-color: var(--primary-color, #3b82f6); color: var(--primary-color, #3b82f6); }
```

- [ ] **Step 7: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/RaindropAnalyticsView.vue
git commit -m "feat: reorder Raindrop page, add stat cards, Copy Log, month leaderboard"
```

---

### Task 6: Live browser verification

**Files:** none.

- [ ] **Step 1: Ensure backend (with KeyGen token) and frontend dev servers are running**

Backend on :3000 with `CONDUCTOR_KEYGEN_API_TOKEN` set (from KeePass, as in the prior plan), frontend on :5173.

- [ ] **Step 2: Verify the new endpoints**

Run: `curl -s http://localhost:3000/api/raindrop/trials | python3 -c "import sys,json; d=json.load(sys.stdin); print('licensed:', d['licensed_active_count'], '| active trials:', d['active_count'])"`
Expected: `licensed: 7` (or current), non-zero active trials.

Run: `curl -s http://localhost:3000/api/raindrop/leaderboard | python3 -c "import sys,json; d=json.load(sys.stdin); print('period:', d['period'], '| users:', len(d['user_stats']))"`
Expected: period start = 1st of current month; some users.

- [ ] **Step 3: Verify the UI with the Browser skill**

Load `http://localhost:5173/raindrop` (logged in). Confirm:
- Order is Stats → Exceptions → Trials → Charts → Insights → Leaderboard.
- Stats bar shows **Licensed Users** and **Active Trials** with real numbers.
- Expanding an exception shows a **Copy Log** button that copies a formatted block (toast "Copied").
- Leaderboard header reads "User Leaderboard (this month)".
- No console errors.

- [ ] **Step 4: Run the full backend suite**

Run: `pytest tests/test_keygen_client.py tests/test_raindrop_trials.py -v`
Expected: all pass.
