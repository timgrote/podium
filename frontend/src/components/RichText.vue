<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  content: string
}>()

type Segment = { type: 'text'; value: string }
  | { type: 'link'; value: string }
  | { type: 'image'; alt: string; url: string }

const segments = computed<Segment[]>(() => {
  if (!props.content) return []

  // Match markdown images ![alt](url) or bare URLs
  const pattern = /!\[([^\]]*)\]\(([^)]+)\)|(https?:\/\/[^\s<>"')\]]+)/g
  const result: Segment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(props.content)) !== null) {
    // Text before this match
    if (match.index > lastIndex) {
      result.push({ type: 'text', value: props.content.slice(lastIndex, match.index) })
    }

    if (match[1] !== undefined && match[2]) {
      // Markdown image: ![alt](url)
      result.push({ type: 'image', alt: match[1], url: match[2] })
    } else if (match[3]) {
      // Bare URL
      result.push({ type: 'link', value: match[3] })
    }

    lastIndex = match.index + match[0].length
  }

  // Remaining text
  if (lastIndex < props.content.length) {
    result.push({ type: 'text', value: props.content.slice(lastIndex) })
  }

  return result
})
</script>

<template>
  <div class="rich-text">
    <template v-for="(seg, i) in segments" :key="i">
      <span v-if="seg.type === 'text'">{{ seg.value }}</span>
      <a
        v-else-if="seg.type === 'link'"
        :href="seg.value"
        target="_blank"
        rel="noopener noreferrer"
        class="rich-link"
      >{{ seg.value }}</a>
      <img
        v-else-if="seg.type === 'image'"
        :src="seg.url"
        :alt="seg.alt"
        class="rich-image"
      />
    </template>
  </div>
</template>

<style scoped>
.rich-text {
  white-space: pre-wrap;
  word-break: break-word;
}
.rich-link {
  color: var(--p-primary-color);
  text-decoration: underline;
}
.rich-link:hover {
  text-decoration: none;
}
.rich-image {
  display: block;
  max-width: 100%;
  border-radius: 0.375rem;
  margin: 0.5rem 0;
}
</style>
