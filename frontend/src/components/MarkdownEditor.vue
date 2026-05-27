<script setup lang="ts">
import { ref } from 'vue'
import MarkdownRenderer from './MarkdownRenderer.vue'

defineProps<{
  rows?: number
  placeholder?: string
  textareaClass?: string
}>()

defineEmits<{
  paste: [event: ClipboardEvent]
}>()

const content = defineModel<string | null>({ required: true })
const tab = ref<'edit' | 'preview'>('edit')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

defineExpose({ textarea: textareaRef })
</script>

<template>
  <div class="md-editor">
    <div class="md-tabs">
      <button type="button" class="md-tab" :class="{ active: tab === 'edit' }" @click="tab = 'edit'">Edit</button>
      <button type="button" class="md-tab" :class="{ active: tab === 'preview' }" @click="tab = 'preview'">Preview</button>
    </div>
    <textarea
      v-if="tab === 'edit'"
      ref="textareaRef"
      v-model="content"
      :rows="rows ?? 5"
      :placeholder="placeholder"
      :class="['md-textarea', textareaClass]"
      @paste="$emit('paste', $event)"
    />
    <div v-else class="md-preview" :class="{ empty: !content }">
      <MarkdownRenderer v-if="content" :content="content" />
      <span v-else class="md-placeholder">Nothing to preview</span>
    </div>
  </div>
</template>

<style scoped>
.md-editor {
  display: flex;
  flex-direction: column;
}

.md-tabs {
  display: flex;
  gap: 0.25rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.md-tab {
  background: none;
  border: none;
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.md-tab:hover { color: var(--p-text-color); }

.md-tab.active {
  color: var(--p-primary-color);
  border-bottom-color: var(--p-primary-color);
}

.md-textarea {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  resize: vertical;
  background: var(--p-form-field-background);
  color: var(--p-text-color);
  font-family: inherit;
  width: 100%;
  box-sizing: border-box;
  margin-top: 0.375rem;
}

.md-preview {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.375rem;
  background: var(--p-content-background);
  overflow-y: auto;
  min-height: 6rem;
  margin-top: 0.375rem;
}

.md-preview.empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.md-placeholder {
  color: var(--p-text-muted-color);
  font-style: italic;
  font-size: 0.75rem;
}
</style>
