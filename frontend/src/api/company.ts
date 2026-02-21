import type { CompanySettings } from '../types'
import { apiFetch } from './client'

export function getCompanySettings(): Promise<CompanySettings> {
  return apiFetch('/company')
}

export function updateCompanySettings(
  data: Record<string, string>,
): Promise<CompanySettings> {
  return apiFetch('/company', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function uploadLogo(file: File): Promise<{ logo_url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch('/api/company/logo', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    let detail = `Logo upload failed (${res.status})`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch { /* non-JSON response */ }
    throw new Error(detail)
  }
  return res.json()
}
