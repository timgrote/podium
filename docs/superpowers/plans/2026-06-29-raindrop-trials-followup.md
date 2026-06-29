# Raindrop Trials Follow-up List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Trials panel to the Raindrop Analytics page showing active trials and trials that expired in the last 30 days, with name, email, dates, and a copy-email button.

**Architecture:** A new `keygen_client` service paginates the KeyGen trial policy via `httpx` and returns normalized license dicts. A new `GET /api/raindrop/trials` endpoint splits them into active / expired-in-last-30-days (derived from `expiry` vs now) and adds day counts. The Vue Raindrop Analytics view gains an independently-loaded Trials panel with two PrimeVue tables.

**Tech Stack:** FastAPI, httpx, pydantic-settings (backend); Vue 3 + TypeScript + PrimeVue DataTable (frontend); pytest + Vitest.

## Global Constraints

- Python HTTP via `httpx` (matches `app/services/loki_client.py`), 15s timeout.
- Config uses `CONDUCTOR_` env prefix via pydantic-settings in `app/config.py`.
- KeyGen account ID `40280a53-8cd5-4b54-9813-04727b10810f` and trial policy ID `42090eb8-6372-40b3-b6b9-fe5e6e6e058b` are non-secret config defaults.
- KeyGen token is secret — only from `CONDUCTOR_KEYGEN_API_TOKEN`, never committed.
- KeyGen list endpoint: `GET https://api.keygen.sh/v1/accounts/{account}/licenses` with headers `Authorization: Bearer {token}`, `Accept: application/vnd.api+json`, query `policy`, `page[number]`, `page[size]`. Pagination REQUIRES `page[number]`.
- License `attributes`: `name`, `metadata.email`, `created`, `expiry`, `status`. Expiry/created are ISO-8601 UTC (`...Z`).
- "Expired recent" = expiry within the last 30 days, rolling. Active = expiry in the future.
- Soft deletes / DB rules: N/A — this feature stores nothing locally, no migration.
- Frontend: no `innerHTML`; use template syntax. Tests run from `frontend/` with `npm run test`; backend tests need `conductor_test` DB.

---

### Task 1: KeyGen client service

**Files:**
- Modify: `app/config.py` (add three settings)
- Create: `app/services/keygen_client.py`
- Test: `tests/test_keygen_client.py`

**Interfaces:**
- Consumes: `settings.keygen_api_token`, `settings.keygen_account_id`, `settings.keygen_trial_policy_id` from `app/config.py`.
- Produces: `fetch_trial_licenses() -> list[dict]` where each dict is `{"name": str, "email": str, "created": str|None, "expiry": str|None, "status": str|None}`. Returns `[]` if the token is unset or on any HTTP error (never raises).

- [ ] **Step 1: Add config settings**

In `app/config.py`, after the Loki block (`loki_api_key: str = ""`), add:

```python
    # KeyGen (Raindrop trial licenses)
    keygen_api_token: str = ""
    keygen_account_id: str = "40280a53-8cd5-4b54-9813-04727b10810f"
    keygen_trial_policy_id: str = "42090eb8-6372-40b3-b6b9-fe5e6e6e058b"
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_keygen_client.py`:

```python
import app.services.keygen_client as kc
from app.config import settings


def _page(licenses):
    return {"data": [
        {"id": lic["id"], "attributes": {
            "name": lic["name"],
            "metadata": {"email": lic["email"]},
            "created": lic["created"],
            "expiry": lic["expiry"],
            "status": lic["status"],
        }} for lic in licenses
    ]}


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self._payload


def test_returns_empty_when_token_unset(monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "")
    assert kc.fetch_trial_licenses() == []


def test_normalizes_and_paginates(monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")
    full = [{"id": str(i), "name": f"User {i}", "email": f"u{i}@x.com",
             "created": "2026-06-01T00:00:00.000Z", "expiry": "2026-07-01T00:00:00.000Z",
             "status": "ACTIVE"} for i in range(100)]
    tail = [{"id": "100", "name": "Last User", "email": "last@x.com",
             "created": "2026-06-02T00:00:00.000Z", "expiry": "2026-07-02T00:00:00.000Z",
             "status": "ACTIVE"}]
    pages = {1: _page(full), 2: _page(tail)}
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(params["page[number]"])
        return _FakeResp(pages[params["page[number]"]])

    monkeypatch.setattr(kc.httpx, "get", fake_get)
    result = kc.fetch_trial_licenses()
    assert len(result) == 101
    assert calls == [1, 2]            # paged until a short page
    assert result[0] == {"name": "User 0", "email": "u0@x.com",
                         "created": "2026-06-01T00:00:00.000Z",
                         "expiry": "2026-07-01T00:00:00.000Z", "status": "ACTIVE"}
    assert result[-1]["name"] == "Last User"


def test_returns_empty_on_http_error(monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(kc.httpx, "get", boom)
    assert kc.fetch_trial_licenses() == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_keygen_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.keygen_client'`

- [ ] **Step 4: Write minimal implementation**

Create `app/services/keygen_client.py`:

```python
import logging

import httpx

from ..config import settings

logger = logging.getLogger("conductor")

KEYGEN_BASE = "https://api.keygen.sh/v1"
PAGE_SIZE = 100


def fetch_trial_licenses() -> list[dict]:
    """Fetch all Raindrop trial licenses from KeyGen.

    Returns a list of normalized dicts ``{name, email, created, expiry, status}``.
    Returns ``[]`` if the token is unset or on any HTTP error (never raises).
    """
    token = settings.keygen_api_token
    if not token:
        logger.warning("CONDUCTOR_KEYGEN_API_TOKEN not set; skipping trial fetch")
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
                "policy": settings.keygen_trial_policy_id,
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
        logger.warning(f"KeyGen trial fetch failed: {e}")
        return []

    return results
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_keygen_client.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add app/config.py app/services/keygen_client.py tests/test_keygen_client.py
git commit -m "feat: add KeyGen client for Raindrop trial licenses"
```

---

### Task 2: Trials endpoint

**Files:**
- Modify: `app/routers/raindrop_analytics.py` (add import + `/trials` route)
- Test: `tests/test_raindrop_trials.py`

**Interfaces:**
- Consumes: `fetch_trial_licenses()` from Task 1; `settings.keygen_api_token`.
- Produces: `GET /api/raindrop/trials` returning
  `{"active": [{"name","email","created","expiry","days_remaining"}], "expired_recent": [{"name","email","created","expiry","days_since_expiry"}], "active_count": int, "expired_recent_count": int, "available": bool}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_raindrop_trials.py`:

```python
from datetime import datetime, timedelta, timezone

import app.routers.raindrop_analytics as ra
from app.config import settings


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def test_trials_unavailable_when_token_unset(client, monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "")
    monkeypatch.setattr(ra, "fetch_trial_licenses", lambda: [])
    r = client.get("/api/raindrop/trials")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert body["active"] == [] and body["expired_recent"] == []


def test_trials_split_active_and_recent_expired(client, monkeypatch):
    monkeypatch.setattr(settings, "keygen_api_token", "prod-test")
    now = datetime.now(timezone.utc)
    licenses = [
        {"name": "Active User", "email": "a@x.com", "created": _iso(now - timedelta(days=5)),
         "expiry": _iso(now + timedelta(days=20)), "status": "ACTIVE"},
        {"name": "Just Expired", "email": "b@x.com", "created": _iso(now - timedelta(days=40)),
         "expiry": _iso(now - timedelta(days=10)), "status": "EXPIRED"},
        {"name": "Long Expired", "email": "c@x.com", "created": _iso(now - timedelta(days=70)),
         "expiry": _iso(now - timedelta(days=40)), "status": "EXPIRED"},
    ]
    monkeypatch.setattr(ra, "fetch_trial_licenses", lambda: licenses)
    body = client.get("/api/raindrop/trials").json()

    assert body["available"] is True
    assert body["active_count"] == 1
    assert body["active"][0]["name"] == "Active User"
    assert body["active"][0]["days_remaining"] in (19, 20)

    assert body["expired_recent_count"] == 1          # 40-days-ago one is excluded
    assert body["expired_recent"][0]["name"] == "Just Expired"
    assert body["expired_recent"][0]["days_since_expiry"] in (9, 10)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_raindrop_trials.py -v`
Expected: FAIL — `/api/raindrop/trials` returns 404 (route not defined).

- [ ] **Step 3: Write minimal implementation**

In `app/routers/raindrop_analytics.py`, update the imports near the top. Change:

```python
from datetime import datetime, timedelta
```
to:
```python
from datetime import datetime, timedelta, timezone
```

And after the existing service import line, add:

```python
from ..config import settings
from ..services.keygen_client import fetch_trial_licenses
```

Add this helper after `_date_range`:

```python
def _parse_keygen_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
```

Add this route at the end of the file:

```python
@router.get("/trials")
def get_trials():
    """Active Raindrop trials + trials expired in the last 30 days (from KeyGen)."""
    if not settings.keygen_api_token:
        return {
            "active": [], "expired_recent": [],
            "active_count": 0, "expired_recent_count": 0, "available": False,
        }

    licenses = fetch_trial_licenses()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    active, expired = [], []

    for lic in licenses:
        expiry = _parse_keygen_dt(lic.get("expiry"))
        if expiry is None:
            continue
        base = {
            "name": lic["name"], "email": lic["email"],
            "created": lic.get("created"), "expiry": lic.get("expiry"),
        }
        if expiry > now:
            active.append({**base, "days_remaining": (expiry - now).days})
        elif expiry >= cutoff:
            expired.append({**base, "days_since_expiry": (now - expiry).days})

    active.sort(key=lambda x: x["days_remaining"])
    expired.sort(key=lambda x: x["days_since_expiry"])

    return {
        "active": active, "expired_recent": expired,
        "active_count": len(active), "expired_recent_count": len(expired),
        "available": True,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_raindrop_trials.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/routers/raindrop_analytics.py tests/test_raindrop_trials.py
git commit -m "feat: add /api/raindrop/trials endpoint"
```

---

### Task 3: Frontend API client

**Files:**
- Modify: `frontend/src/api/raindrop.ts` (add types + fetch function)

**Interfaces:**
- Consumes: `apiFetch` from `./client`; the `/raindrop/trials` response from Task 2.
- Produces: `RaindropTrial`, `RaindropTrials` types and `getRaindropTrials(): Promise<RaindropTrials>`.

- [ ] **Step 1: Add types and fetch function**

Append to `frontend/src/api/raindrop.ts` (after the existing `getRaindropWarnings` function):

```typescript
export interface RaindropTrial {
  name: string
  email: string
  created: string | null
  expiry: string | null
  days_remaining?: number
  days_since_expiry?: number
}

export interface RaindropTrials {
  active: RaindropTrial[]
  expired_recent: RaindropTrial[]
  active_count: number
  expired_recent_count: number
  available: boolean
}

export function getRaindropTrials(): Promise<RaindropTrials> {
  return apiFetch('/raindrop/trials')
}
```

- [ ] **Step 2: Verify it type-checks / builds**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: no new errors referencing `raindrop.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/raindrop.ts
git commit -m "feat: add getRaindropTrials API client"
```

---

### Task 4: Trials panel in the Raindrop Analytics view

**Files:**
- Modify: `frontend/src/views/RaindropAnalyticsView.vue` (script: imports/refs/loader/helpers; template: panel; style: panel CSS)

**Interfaces:**
- Consumes: `getRaindropTrials`, `RaindropTrials` from Task 3; `useToast` from `../composables/useToast`.
- Produces: a Trials panel rendered on the page, loaded independently of the analytics loader.

- [ ] **Step 1: Add imports and state to `<script setup>`**

In `frontend/src/views/RaindropAnalyticsView.vue`, change the import on line 8 to include `getRaindropTrials`:

```typescript
import { getRaindropAnalytics, getRaindropExceptions, getRaindropWarnings, getRaindropTrials } from '../api/raindrop'
```

Change the type import on line 9 to include `RaindropTrials`:

```typescript
import type { RaindropAnalytics, RaindropExceptions, RaindropWarnings, RaindropTrials } from '../api/raindrop'
```

Add the toast import below line 9:

```typescript
import { useToast } from '../composables/useToast'
```

After the `const warnings = ...` ref (line 22), add:

```typescript
const toast = useToast()
const trials = ref<RaindropTrials | null>(null)
const trialsLoading = ref(true)
const trialsError = ref('')
```

- [ ] **Step 2: Add the trials loader, copy + date helpers, and mount hook**

After the `load()` function (after line 50), add:

```typescript
async function loadTrials() {
  trialsLoading.value = true
  trialsError.value = ''
  try {
    trials.value = await getRaindropTrials()
  } catch (err: any) {
    trialsError.value = err.message || 'Failed to load trials'
  } finally {
    trialsLoading.value = false
  }
}

async function copyEmail(email: string) {
  try {
    await navigator.clipboard.writeText(email)
    toast.success('Copied', email)
  } catch {
    toast.error('Copy failed')
  }
}

function formatTrialDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}
```

Change the existing `onMounted(load)` line (line 56) to also load trials:

```typescript
onMounted(() => {
  load()
  loadTrials()
})
```

- [ ] **Step 3: Add the Trials panel to the template**

In `frontend/src/views/RaindropAnalyticsView.vue`, insert the following block immediately after the `</div>` that closes `page-header` (after line 186), before the `<!-- Loading -->` comment:

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

- [ ] **Step 4: Add panel styles**

In the `<style scoped>` block of `frontend/src/views/RaindropAnalyticsView.vue`, append:

```css
.trials-panel {
  background: var(--surface-card, #fff);
  border: 1px solid var(--surface-border, #e5e7eb);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}
.trials-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.trials-header h2 { margin: 0; font-size: 1.1rem; }
.trials-counts { color: var(--text-color-secondary, #6b7280); font-size: 0.85rem; margin-left: 0.25rem; }
.trials-state { color: var(--text-color-secondary, #6b7280); padding: 0.75rem 0; }
.email-cell { display: inline-flex; align-items: center; gap: 0.4rem; }
.copy-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-color-secondary, #6b7280);
  padding: 2px 4px;
  border-radius: 4px;
}
.copy-btn:hover { color: var(--primary-color, #3b82f6); background: var(--surface-hover, #f3f4f6); }
```

- [ ] **Step 5: Build to verify it compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors in `RaindropAnalyticsView.vue`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/RaindropAnalyticsView.vue
git commit -m "feat: add Trials panel to Raindrop Analytics view"
```

---

### Task 5: Live manual verification on local dev

**Files:** none (verification only)

**Interfaces:** Consumes the full stack from Tasks 1-4.

- [ ] **Step 1: Start the backend with the KeyGen token from KeePass**

The token must be in the backend process env. Pull it from KeePass and export it for the uvicorn process (value never printed to the terminal):

```bash
cd /home/tim/repos/podium
source .venv/bin/activate
export CONDUCTOR_KEYGEN_API_TOKEN="$(MASTER=$(grep -m1 '^KDBX_MASTER=' ~/.claude/.env | cut -d= -f2- | tr -d '\r' | sed "s/^[\"' ]*//; s/[\"' ]*\$//"); printf '%s\n' "$MASTER" | keepassxc-cli attachment-export -q --stdout /mnt/d/Vaults/Keepass/DevEnv.kdbx 'ai-env' '.env' 2>/dev/null | grep -iE '^[ ]*(export[ ]+)?KEYGEN_API=' | head -1 | sed 's/.*KEYGEN_API=//; s/^[\"'\'' ]*//; s/[\"'\'' ]*$//; s/\r$//')"
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

- [ ] **Step 2: Verify the endpoint returns live data**

In another terminal:

Run: `curl -s http://localhost:3000/api/raindrop/trials | python3 -c "import sys,json; d=json.load(sys.stdin); print('available:', d['available'], '| active:', d['active_count'], '| expired_recent:', d['expired_recent_count'])"`
Expected: `available: True` and a non-zero `active` count (real trials exist as of 2026-06-29).

- [ ] **Step 3: Verify the UI**

Start the frontend dev server (port 5173 per project rules) and use the Browser skill to load the Raindrop Analytics page:

Run: `cd frontend && npm run dev`
Then navigate to `http://localhost:5173`, log in (`qa_test@conductor.test` / `testtest` if needed), open the Raindrop Analytics page, and confirm:
- The Trials panel renders above the dashboard with active/expired counts.
- Active Trials table shows names, emails, dates, "Days Left".
- The copy-email button copies the address and shows a "Copied" toast.

- [ ] **Step 4: Run the full backend test suite**

Run: `pytest tests/test_keygen_client.py tests/test_raindrop_trials.py -v`
Expected: all pass.

---

## Deployment (after Tim's approval — do NOT auto-deploy)

Production `tie-conductor` needs the token in the service env. The panel shows "KeyGen not configured" until then. When Tim approves deploying:

- Add `Environment=CONDUCTOR_KEYGEN_API_TOKEN=<value from KEYGEN_API KeePass entry>` to `conductor-api.service` on the droplet (set directly on the box, never commit), then `systemctl daemon-reload && systemctl restart conductor-api`.
- Code itself auto-deploys on push to master via GitHub Actions.
