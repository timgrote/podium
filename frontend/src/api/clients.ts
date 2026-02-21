import type { Client } from '../types'
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
