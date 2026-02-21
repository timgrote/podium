<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'

const visible = defineModel<boolean>('visible', { required: true })

defineProps<{
  label: string
  action: () => Promise<void>
}>()

const emit = defineEmits<{
  error: [msg: string]
}>()

const deleting = ref(false)

async function confirm(action: () => Promise<void>) {
  deleting.value = true
  try {
    await action()
    visible.value = false
  } catch (e) {
    emit('error', String(e))
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    header="Confirm Delete"
    :modal="true"
    :style="{ width: '400px' }"
  >
    <p>Are you sure you want to delete {{ label }}?</p>
    <p class="warning">This action cannot be undone.</p>
    <template #footer>
      <button class="btn" @click="visible = false">Cancel</button>
      <button class="btn btn-danger" :disabled="deleting" @click="confirm(action)">
        {{ deleting ? 'Deleting...' : 'Delete' }}
      </button>
    </template>
  </Dialog>
</template>

<style scoped>
p { margin: 0 0 0.5rem; font-size: 0.875rem; }
.warning { color: var(--p-red-600); font-size: 0.8125rem; }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--p-content-border-color); border-radius: 0.375rem; background: var(--p-content-background); cursor: pointer; font-size: 0.875rem; margin-left: 0.5rem; color: var(--p-text-color); }
.btn-danger { background: var(--p-red-600); color: #fff; border-color: var(--p-red-600); }
.btn-danger:hover { background: var(--p-red-700); }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
