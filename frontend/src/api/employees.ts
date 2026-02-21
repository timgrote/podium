import type { Employee } from '../types'
import { apiFetch } from './client'

export function getEmployees(): Promise<Employee[]> {
  return apiFetch('/employees')
}
