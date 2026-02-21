<script setup lang="ts">
defineProps<{
  totalProjects: number
  totalInvoiced: number
  totalPaid: number
  totalOutstanding: number
}>()

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}
</script>

<template>
  <div class="stats-bar">
    <div class="stat-card">
      <div class="stat-label">Projects</div>
      <div class="stat-value">{{ totalProjects }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Invoiced</div>
      <div class="stat-value">{{ formatCurrency(totalInvoiced) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Paid</div>
      <div class="stat-value paid">{{ formatCurrency(totalPaid) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Outstanding</div>
      <div class="stat-value outstanding">{{ formatCurrency(totalOutstanding) }}</div>
    </div>
  </div>
</template>

<style scoped>
.stats-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
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
  color: var(--p-surface-500);
  margin-bottom: 0.25rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-surface-800);
}

.stat-value.paid {
  color: var(--p-green-600);
}

.stat-value.outstanding {
  color: var(--p-orange-600);
}

@media (max-width: 768px) {
  .stats-bar {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
