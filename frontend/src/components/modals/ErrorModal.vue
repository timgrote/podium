<script setup lang="ts">
import Dialog from 'primevue/dialog'

const visible = defineModel<boolean>('visible', { required: true })

defineProps<{
  message: string
}>()

function copyError(message: string) {
  navigator.clipboard.writeText(message)
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    header="Error"
    :modal="true"
    :style="{ width: '450px' }"
  >
    <div class="error-content">
      <i class="pi pi-exclamation-triangle error-icon" />
      <pre class="error-text">{{ message }}</pre>
    </div>
    <template #footer>
      <button class="btn" @click="copyError(message)">
        <i class="pi pi-copy" /> Copy
      </button>
      <button class="btn btn-primary" @click="visible = false">Close</button>
    </template>
  </Dialog>
</template>

<style scoped>
.error-content { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; }
.error-icon { font-size: 2rem; color: var(--p-red-600); }
.error-text { background: var(--p-red-50); border: 1px solid var(--p-red-200); border-radius: 0.375rem; padding: 0.75rem; font-size: 0.8125rem; color: var(--p-red-800); white-space: pre-wrap; word-break: break-all; width: 100%; max-height: 300px; overflow-y: auto; margin: 0; }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; display: inline-flex; align-items: center; gap: 0.25rem; color: var(--p-text-color); }
.btn-primary { background: var(--p-primary-color); color: #fff; border-color: var(--p-primary-color); }
.btn-primary:hover { background: var(--p-primary-hover-color); }
</style>
