import type { Employee } from '../types'
import { apiFetch } from './client'

export function getEmployees(): Promise<Employee[]> {
  return apiFetch('/employees')
}

export function updateEmployee(
  id: string,
  data: { first_name?: string; last_name?: string; email?: string },
): Promise<Employee> {
  return apiFetch(`/employees/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
