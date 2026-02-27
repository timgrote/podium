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

export function deleteContact(id: string): Promise<{ success: boolean }> {
  return apiFetch(`/contacts/${id}`, { method: 'DELETE' })
}

export function deleteContactNote(
  noteId: string,
): Promise<{ success: boolean }> {
  return apiFetch(`/contacts/notes/${noteId}`, { method: 'DELETE' })
}
