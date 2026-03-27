<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Chart from 'primevue/chart'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import SelectButton from 'primevue/selectbutton'
import ProgressSpinner from 'primevue/progressspinner'
import { getRaindropAnalytics, getRaindropExceptions, getRaindropWarnings } from '../api/raindrop'
import type { RaindropAnalytics, RaindropExceptions, RaindropWarnings } from '../api/raindrop'

const days = ref(14)
const dayOptions = [
  { label: '7d', value: 7 },
  { label: '14d', value: 14 },
  { label: '30d', value: 30 },
]

const loading = ref(true)
const error = ref('')
const analytics = ref<RaindropAnalytics | null>(null)
const exceptions = ref<RaindropExceptions | null>(null)
const warnings = ref<RaindropWarnings | null>(null)
const expandedExceptionRows = ref<Record<string, boolean>>({})
const showAllExceptions = ref(false)

const visibleExceptions = computed(() => {
  if (!exceptions.value) return []
  const list = exceptions.value.exceptions
  return showAllExceptions.value ? list : list.slice(0, 5)
})

async function load() {
  loading.value = true
  error.value = ''
  showAllExceptions.value = false
  try {
    const [a, exc, warn] = await Promise.all([
      getRaindropAnalytics(days.value),
      getRaindropExceptions(days.value),
      getRaindropWarnings(days.value),
    ])
    analytics.value = a
    exceptions.value = exc
    warnings.value = warn
  } catch (err: any) {
    error.value = err.message || 'Failed to load analytics'
  } finally {
    loading.value = false
  }
}

function toggleException(idx: number) {
  expandedExceptionRows.value[idx] = !expandedExceptionRows.value[idx]
}

onMounted(load)
watch(days, load)

// Chart configs
const activeUsersChart = computed(() => {
  if (!analytics.value) return null
  const data = analytics.value.daily_active_users
  return {
    type: 'line' as const,
    data: {
      labels: data.map(d => formatDateShort(d.date)),
      datasets: [{
        label: 'Active Users',
        data: data.map(d => d.count),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
      },
    },
  }
})

const sessionsChart = computed(() => {
  if (!analytics.value) return null
  const data = analytics.value.daily_sessions
  return {
    type: 'bar' as const,
    data: {
      labels: data.map(d => formatDateShort(d.date)),
      datasets: [{
        label: 'Sessions',
        data: data.map(d => d.count),
        backgroundColor: 'rgba(99, 102, 241, 0.6)',
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  }
})

const hourlyChart = computed(() => {
  if (!analytics.value) return null
  const data = analytics.value.hourly_distribution
  return {
    type: 'bar' as const,
    data: {
      labels: data.map(d => `${d.hour}:00`),
      datasets: [{
        label: 'Sessions',
        data: data.map(d => d.count),
        backgroundColor: data.map(d =>
          d.count > 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(16, 185, 129, 0.15)'
        ),
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
    },
  }
})

const workHoursChart = computed(() => {
  if (!analytics.value) return null
  const data = analytics.value.daily_work_hours
  return {
    type: 'line' as const,
    data: {
      labels: data.map(d => formatDateShort(d.date)),
      datasets: [{
        label: 'Work Hours',
        data: data.map(d => d.hours),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  }
})

function formatDateShort(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatErrorTime(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}
</script>

<template>
  <div class="raindrop-analytics">
    <div class="page-header">
      <h1>Raindrop Analytics</h1>
      <SelectButton
        v-model="days"
        :options="dayOptions"
        optionLabel="label"
        optionValue="value"
        :allowEmpty="false"
      />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <i class="pi pi-exclamation-triangle"></i>
      <p>{{ error }}</p>
      <button class="retry-btn" @click="load">Retry</button>
    </div>

    <!-- Dashboard -->
    <template v-else-if="analytics">
      <!-- Exceptions Panel -->
      <div class="exceptions-panel" v-if="exceptions">
        <div class="exceptions-header" :class="{ 'has-exceptions': exceptions.count > 0 }">
          <div class="exceptions-title">
            <i class="pi" :class="exceptions.count > 0 ? 'pi-exclamation-circle' : 'pi-check-circle'"></i>
            <h2>Exceptions</h2>
            <span class="exception-badge" v-if="exceptions.count > 0">{{ exceptions.count }}</span>
          </div>
          <span class="exceptions-subtitle" v-if="exceptions.count === 0">No unhandled exceptions in the last {{ days }} days</span>
        </div>
        <div v-if="exceptions.count > 0" class="exceptions-list">
          <div
            v-for="(exc, i) in visibleExceptions"
            :key="i"
            class="exception-item"
            @click="toggleException(i)"
          >
            <div class="exception-summary">
              <span class="exception-time">{{ formatErrorTime(exc.timestamp) }}</span>
              <span class="exception-user">{{ exc.user }}</span>
              <span class="exception-machine">{{ exc.machine }}</span>
              <span class="exception-msg">{{ exc.message }}</span>
            </div>
            <div v-if="expandedExceptionRows[i]" class="exception-detail">
              <div v-if="exc.drawing" class="detail-row"><strong>Drawing:</strong> {{ exc.drawing }}</div>
              <div v-if="exc.app_version" class="detail-row"><strong>Version:</strong> {{ exc.app_version }}</div>
              <div v-if="exc.exception" class="detail-row">
                <strong>Exception:</strong>
                <template v-if="typeof exc.exception === 'object'">{{ exc.exception.Type }}: {{ exc.exception.Message }}</template>
                <template v-else>{{ exc.exception }}</template>
              </div>
              <pre v-if="exc.stack_trace" class="stack-trace">{{ exc.stack_trace }}</pre>
            </div>
          </div>
          <button
            v-if="exceptions.count > 5"
            class="show-all-btn"
            @click.stop="showAllExceptions = !showAllExceptions"
          >
            {{ showAllExceptions ? 'Show less' : `Show all ${exceptions.count} exceptions` }}
          </button>
        </div>
      </div>

      <!-- Stat Cards -->
      <div class="stats-bar">
        <div class="stat-card">
          <div class="stat-label">Sessions</div>
          <div class="stat-value">{{ analytics.summary.total_sessions }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Active Users</div>
          <div class="stat-value accent">{{ analytics.summary.unique_users }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Work Hours</div>
          <div class="stat-value">{{ analytics.summary.total_work_hours }}h</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Commands</div>
          <div class="stat-value">{{ analytics.summary.total_commands.toLocaleString() }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Raindrop Adoption</div>
          <div class="stat-value accent">{{ analytics.summary.raindrop_adoption_pct }}%</div>
        </div>
      </div>

      <!-- Active Users Chart -->
      <div class="chart-section">
        <h2>Active Users Over Time</h2>
        <div class="chart-container" v-if="activeUsersChart">
          <Chart type="line" :data="activeUsersChart.data" :options="activeUsersChart.options" />
        </div>
      </div>

      <!-- Two charts side by side -->
      <div class="chart-row">
        <div class="chart-section half">
          <h2>Daily Sessions</h2>
          <div class="chart-container" v-if="sessionsChart">
            <Chart type="bar" :data="sessionsChart.data" :options="sessionsChart.options" />
          </div>
        </div>
        <div class="chart-section half">
          <h2>Usage by Hour</h2>
          <div class="chart-container" v-if="hourlyChart">
            <Chart type="bar" :data="hourlyChart.data" :options="hourlyChart.options" />
          </div>
        </div>
      </div>

      <!-- Work Hours Chart -->
      <div class="chart-section">
        <h2>Daily Work Hours</h2>
        <div class="chart-container" v-if="workHoursChart">
          <Chart type="line" :data="workHoursChart.data" :options="workHoursChart.options" />
        </div>
      </div>

      <!-- Insights -->
      <div class="insights-section" v-if="analytics.insights.length">
        <h2>Insights</h2>
        <div class="insights-grid">
          <div class="insight-card" v-for="(insight, i) in analytics.insights" :key="i">
            <i class="pi pi-info-circle"></i>
            <span>{{ insight }}</span>
          </div>
        </div>
      </div>

      <!-- User Leaderboard -->
      <div class="table-section" v-if="analytics.user_stats.length">
        <h2>User Leaderboard</h2>
        <DataTable :value="analytics.user_stats" stripedRows size="small">
          <Column field="user" header="User">
            <template #body="{ data }">
              <span class="user-name">{{ data.user }}</span>
            </template>
          </Column>
          <Column field="sessions" header="Sessions" sortable />
          <Column field="work_hours" header="Hours" sortable>
            <template #body="{ data }">{{ data.work_hours }}h</template>
          </Column>
          <Column field="commands" header="Commands" sortable>
            <template #body="{ data }">{{ data.commands.toLocaleString() }}</template>
          </Column>
          <Column field="raindrop_commands" header="Raindrop Cmds" sortable>
            <template #body="{ data }">{{ data.raindrop_commands.toLocaleString() }}</template>
          </Column>
          <Column field="saves" header="Saves" sortable />
          <Column field="unique_drawings" header="Drawings" sortable />
        </DataTable>
      </div>

      <!-- Warnings -->
      <div class="table-section" v-if="warnings">
        <h2>Warnings <span class="warning-count" v-if="warnings.count">({{ warnings.count }})</span></h2>
        <div v-if="warnings.count === 0" class="empty-state">
          <i class="pi pi-check-circle"></i>
          <span>No warnings in the last {{ days }} days</span>
        </div>
        <DataTable v-else :value="warnings.warnings" stripedRows size="small" :paginator="warnings.count > 10" :rows="10">
          <Column field="timestamp" header="Time">
            <template #body="{ data }">{{ formatErrorTime(data.timestamp) }}</template>
          </Column>
          <Column field="user" header="User">
            <template #body="{ data }"><span class="user-name">{{ data.user }}</span></template>
          </Column>
          <Column field="drawing" header="Drawing" />
          <Column field="message" header="Message">
            <template #body="{ data }">
              <span class="error-message">{{ data.message }}</span>
            </template>
          </Column>
        </DataTable>
      </div>
    </template>
  </div>
</template>

<style scoped>
.raindrop-analytics {
  padding: 1.5rem;
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0;
}

/* Stat Cards */
.stats-bar {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--p-content-background);
  border-radius: 0.5rem;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-text-muted-color);
  margin-bottom: 0.25rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.stat-value.accent {
  color: var(--p-primary-color);
}

/* Exceptions Panel */
.exceptions-panel {
  background: var(--p-content-background);
  border-radius: 0.5rem;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-left: 4px solid var(--p-green-500);
}

.exceptions-panel:has(.has-exceptions) {
  border-left-color: var(--p-red-500);
}

.exceptions-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.exceptions-header.has-exceptions .exceptions-title i {
  color: var(--p-red-500);
}

.exceptions-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.exceptions-title i {
  font-size: 1.1rem;
  color: var(--p-green-500);
}

.exceptions-title h2 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0;
}

.exception-badge {
  background: var(--p-red-500);
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 999px;
}

.exceptions-subtitle {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.exceptions-list {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.exception-item {
  background: var(--p-surface-50);
  border-radius: 0.375rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background 0.15s;
}

.exception-item:hover {
  background: var(--p-surface-100);
}

:root.app-dark .exception-item {
  background: var(--p-surface-800);
}

:root.app-dark .exception-item:hover {
  background: var(--p-surface-700);
}

.exception-summary {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.85rem;
}

.exception-time {
  color: var(--p-text-muted-color);
  white-space: nowrap;
  min-width: 120px;
}

.exception-user {
  text-transform: capitalize;
  font-weight: 500;
  min-width: 60px;
}

.exception-machine {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
  min-width: 100px;
}

.exception-msg {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--p-red-600);
}

.show-all-btn {
  width: 100%;
  padding: 0.5rem;
  margin-top: 0.5rem;
  background: transparent;
  border: 1px solid var(--p-surface-300);
  border-radius: 0.375rem;
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
}

.show-all-btn:hover {
  background: var(--p-surface-100);
  color: var(--p-text-color);
}

:root.app-dark .show-all-btn:hover {
  background: var(--p-surface-700);
}

.exception-detail {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--p-surface-200);
  font-size: 0.8rem;
}

.detail-row {
  margin-bottom: 0.25rem;
  color: var(--p-text-color);
}

.stack-trace {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: var(--p-surface-900);
  color: var(--p-surface-100);
  border-radius: 0.25rem;
  font-size: 0.75rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Charts */
.chart-section {
  background: var(--p-content-background);
  border-radius: 0.5rem;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-section h2 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0 0 1rem 0;
}

.chart-container {
  height: 280px;
  position: relative;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.chart-section.half {
  margin-bottom: 1.5rem;
}

/* Insights */
.insights-section {
  margin-bottom: 1.5rem;
}

.insights-section h2 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0 0 0.75rem 0;
}

.insights-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.insight-card {
  background: var(--p-content-background);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--p-text-color);
}

.insight-card i {
  color: var(--p-primary-color);
  font-size: 0.875rem;
}

/* Tables */
.table-section {
  background: var(--p-content-background);
  border-radius: 0.5rem;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.table-section h2 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0 0 1rem 0;
}

.user-name {
  text-transform: capitalize;
  font-weight: 500;
}

.warning-count {
  font-weight: 400;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.error-message {
  font-size: 0.8rem;
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}

/* States */
.loading-state {
  display: flex;
  justify-content: center;
  padding: 4rem 0;
}

.error-state {
  text-align: center;
  padding: 4rem 0;
  color: var(--p-text-muted-color);
}

.error-state i {
  font-size: 2rem;
  color: var(--p-orange-500);
}

.retry-btn {
  margin-top: 1rem;
  padding: 0.5rem 1.5rem;
  border-radius: 0.375rem;
  border: 1px solid var(--p-primary-color);
  background: transparent;
  color: var(--p-primary-color);
  cursor: pointer;
}

.retry-btn:hover {
  background: var(--p-primary-color);
  color: white;
}

.empty-state {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.empty-state i {
  color: var(--p-green-500);
}

@media (max-width: 1024px) {
  .stats-bar {
    grid-template-columns: repeat(3, 1fr);
  }
  .chart-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-bar {
    grid-template-columns: repeat(2, 1fr);
  }
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
}
</style>
