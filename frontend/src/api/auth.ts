import { apiFetch } from './client'
import type { Employee } from '../types'

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

export function uploadAvatar(file: File): Promise<Employee> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch('/auth/avatar', {
    method: 'POST',
    body: form,
  })
}
