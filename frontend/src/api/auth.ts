import { apiFetch } from './client'
import type { Employee } from '../types'

export interface ApiKey {
  id: string
  name: string
  created_at: string | null
  last_used_at: string | null
  expires_at: string | null
}

export interface ApiKeyWithRaw extends ApiKey {
  raw_key: string
}

export function login(email: string, password: string): Promise<Employee> {
  return apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function signup(email: string, password: string): Promise<Employee> {
  return apiFetch('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function logout(): Promise<void> {
  return apiFetch('/auth/logout', { method: 'POST' })
}

export function fetchMe(): Promise<Employee> {
  return apiFetch('/auth/me')
}

export function getUserSettings(): Promise<Record<string, string>> {
  return apiFetch('/auth/settings')
}

export function updateUserSettings(data: Record<string, string>): Promise<Record<string, string>> {
  return apiFetch('/auth/settings', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function uploadAvatar(file: File): Promise<Employee> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch('/auth/avatar', {
    method: 'POST',
    body: form,
  })
}

export function getApiKeys(): Promise<ApiKey[]> {
  return apiFetch('/auth/api-keys')
}

export function createApiKey(name: string): Promise<ApiKeyWithRaw> {
  return apiFetch('/auth/api-keys', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function deleteApiKey(id: string): Promise<void> {
  return apiFetch(`/auth/api-keys/${id}`, { method: 'DELETE' })
}
