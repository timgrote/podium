import type { Contact, ContactNote } from '../types'
import { apiFetch } from './client'

export function getContacts(clientId?: string): Promise<Contact[]> {
  const params = clientId ? `?client_id=${encodeURIComponent(clientId)}` : ''
  return apiFetch(`/contacts${params}`)
}

export function createContact(data: {
  name: string
  email?: string
  phone?: string
  role?: string
  client_id?: string
}): Promise<Contact> {
  return apiFetch('/contacts', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export interface VcfImportEntry {
  name: string
  email: string | null
  phone: string | null
  role: string | null
  notes: string | null
  company_name: string | null
  company_new: boolean
  client_id: string | null
  action: 'create' | 'update'
  existing_id: string | null
}

export interface VcfImportResult {
  contacts: VcfImportEntry[]
  summary: { create: number; update: number; total: number; new_companies: number }
  committed: boolean
}

export function importContacts(file: File, commit: boolean): Promise<VcfImportResult> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch(`/contacts/import?commit=${commit}`, {
    method: 'POST',
    body: form,
  })
}

export function getContactNotes(contactId: string): Promise<ContactNote[]> {
  return apiFetch(`/contacts/${contactId}/notes`)
}

export function addContactNote(
  contactId: string,
  data: { content: string; author_id?: string },
): Promise<ContactNote> {
  return apiFetch(`/contacts/${contactId}/notes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateContact(
  id: string,
  data: Record<string, unknown>,
): Promise<Contact> {
  return apiFetch(`/contacts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function getContactProjects(contactId: string): Promise<{ id: string; project_name: string; job_code: string | null; status: string }[]> {
  return apiFetch(`/contacts/${contactId}/projects`)
}

export function deleteContact(id: string): Promise<{ success: boolean }> {
  return apiFetch(`/contacts/${id}`, { method: 'DELETE' })
}

export function deleteContactNote(
  noteId: string,
): Promise<{ success: boolean }> {
  return apiFetch(`/contacts/notes/${noteId}`, { method: 'DELETE' })
}
