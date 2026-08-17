<script setup lang="ts">
import ProjectsBoard from '../components/kanban/ProjectsBoard.vue'
</script>

<template>
  <div class="kanban-page">
    <div class="kanban-header">
      <div class="header-left">
        <h1>Kanban</h1>
        <router-link class="board-toggle" to="/projects">
          <i class="pi pi-list" /> Back to Project List
        </router-link>
      </div>
    </div>
    <ProjectsBoard />
  </div>
</template>

<style scoped>
.kanban-page {
  /* Fill the main content area — no narrow cap. */
  width: 100%;
}

.kanban-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.kanban-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.board-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--p-primary-color);
  text-decoration: none;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
}
.board-toggle:hover {
  background: var(--p-content-hover-background);
}
</style>
