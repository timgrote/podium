<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{
  content: string
  noteIndex?: Map<string, string>  // title (lowercase) -> id
}>()

const router = useRouter()

const md = new marked.Marked({ breaks: true, gfm: true })

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function processWikiLinks(text: string): string {
  return text.replace(/\[\[([^\]]+)\]\]/g, (_match, title: string) => {
    const trimmed = title.trim()
    const noteId = props.noteIndex?.get(trimmed.toLowerCase())
    if (noteId) {
      return `<a href="/wiki/${escapeHtml(noteId)}" class="wiki-link">${escapeHtml(trimmed)}</a>`
    }
    return `<span class="wiki-link-missing">${escapeHtml(trimmed)}</span>`
  })
}

const rendered = computed(() => {
  if (!props.content) return ''
  const withLinks = processWikiLinks(props.content)
  const html = md.parse(withLinks) as string
  return DOMPurify.sanitize(html, { ADD_ATTR: ['class'] })
})

function handleClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  const link = target.closest('a.wiki-link') as HTMLAnchorElement | null
  if (link) {
    e.preventDefault()
    const href = link.getAttribute('href')
    if (href) router.push(href)
  }
}
</script>

<template>
  <div class="markdown-body" v-html="rendered" @click="handleClick" />
</template>

<style scoped>
.markdown-body {
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--p-text-color);
  word-wrap: break-word;
}

.markdown-body :deep(h1) {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 1rem 0 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.markdown-body :deep(h2) {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 1rem 0 0.5rem;
}

.markdown-body :deep(h3) {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0.75rem 0 0.375rem;
}

.markdown-body :deep(p) {
  margin: 0.5rem 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}

.markdown-body :deep(li) {
  margin: 0.25rem 0;
}

.markdown-body :deep(code) {
  background: var(--p-surface-100);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.8125rem;
  font-family: monospace;
}

:root.p-dark .markdown-body :deep(code) {
  background: var(--p-surface-700);
}

.markdown-body :deep(pre) {
  background: var(--p-surface-100);
  padding: 0.75rem;
  border-radius: 0.375rem;
  overflow-x: auto;
  margin: 0.5rem 0;
}

:root.p-dark .markdown-body :deep(pre) {
  background: var(--p-surface-800);
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--p-primary-color);
  padding-left: 0.75rem;
  margin: 0.5rem 0;
  color: var(--p-text-muted-color);
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5rem 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--p-content-border-color);
  padding: 0.375rem 0.75rem;
  text-align: left;
  font-size: 0.8125rem;
}

.markdown-body :deep(th) {
  background: color-mix(in srgb, var(--p-content-background) 90%, var(--p-text-muted-color) 10%);
  font-weight: 600;
  color: var(--p-text-color);
}

.markdown-body :deep(.wiki-link) {
  color: var(--p-primary-color);
  text-decoration: none;
  border-bottom: 1px dashed var(--p-primary-color);
  cursor: pointer;
}

.markdown-body :deep(.wiki-link:hover) {
  border-bottom-style: solid;
}

.markdown-body :deep(.wiki-link-missing) {
  color: var(--p-red-500);
  border-bottom: 1px dashed var(--p-red-400);
}

.markdown-body :deep(a) {
  color: var(--p-primary-color);
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 0.375rem;
  margin: 0.5rem 0;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--p-content-border-color);
  margin: 1rem 0;
}
</style>
