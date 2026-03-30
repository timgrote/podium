import type { WikiNote } from '../types'
import { apiFetch } from './client'

export function getWikiNotes(q?: string, category?: string): Promise<WikiNote[]> {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (category) params.set('category', category)
  const qs = params.toString()
  return apiFetch(`/wiki${qs ? '?' + qs : ''}`)
}

export function getWikiCategories(): Promise<string[]> {
  return apiFetch('/wiki/categories')
}

export function getWikiNote(id: string): Promise<WikiNote> {
  return apiFetch(`/wiki/${id}`)
}

export function createWikiNote(data: {
  title: string
  content?: string
  category?: string
  created_by?: string | null
}): Promise<WikiNote> {
  return apiFetch('/wiki', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateWikiNote(
  id: string,
  data: Record<string, unknown>,
): Promise<WikiNote> {
  return apiFetch(`/wiki/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteWikiNote(id: string): Promise<{ success: boolean }> {
  return apiFetch(`/wiki/${id}`, { method: 'DELETE' })
}
