import type { Client, ClientNote } from '../types'
import { apiFetch } from './client'

export function getClients(q?: string): Promise<Client[]> {
  const params = q ? `?q=${encodeURIComponent(q)}` : ''
  return apiFetch(`/clients${params}`)
}

export function getClient(id: string): Promise<Client> {
  return apiFetch(`/clients/${id}`)
}

export function createClient(data: {
  name: string
  email?: string
  company?: string
  phone?: string
  address?: string
  notes?: string
}): Promise<Client> {
  return apiFetch('/clients', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateClient(
  id: string,
  data: Record<string, unknown>,
): Promise<Client> {
  return apiFetch(`/clients/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteClient(id: string): Promise<{ success: boolean }> {
  return apiFetch(`/clients/${id}`, { method: 'DELETE' })
}

export function getClientNotes(clientId: string): Promise<ClientNote[]> {
  return apiFetch(`/clients/${clientId}/notes`)
}

export function addClientNote(
  clientId: string,
  data: { content: string; author_id?: string },
): Promise<ClientNote> {
  return apiFetch(`/clients/${clientId}/notes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function deleteClientNote(
  noteId: string,
): Promise<{ success: boolean }> {
  return apiFetch(`/clients/notes/${noteId}`, { method: 'DELETE' })
}
