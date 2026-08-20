<script setup lang="ts">
import { ref } from 'vue'
import TasksBoard from '../components/kanban/TasksBoard.vue'
import TaskDetailModal from '../components/modals/TaskDetailModal.vue'

const taskModalVisible = ref(false)
const selectedTaskId = ref<string | null>(null)
const selectedProjectId = ref('')

function openTask(task: { id: string; project_id: string }) {
  selectedTaskId.value = task.id
  selectedProjectId.value = task.project_id
  taskModalVisible.value = true
}
</script>

<template>
  <div class="kanban">
    <div class="kanban-header">
      <div class="header-left">
        <h1>Task Board</h1>
        <router-link class="board-toggle" to="/my-tasks">
          <i class="pi pi-list" /> Back to Task List
        </router-link>
      </div>
    </div>
    <TasksBoard @open-task="openTask" />
    <TaskDetailModal
      v-model:visible="taskModalVisible"
      :task-id="selectedTaskId"
      :project-id="selectedProjectId"
    />
  </div>
</template>

<style scoped>
.kanban {
  max-width: 1400px;
  margin: 0 auto;
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
