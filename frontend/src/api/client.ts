const BASE = '/api'

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE}${path}`
  const headers: Record<string, string> = {
    ...(typeof options.body === 'string' ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers as Record<string, string>),
  }
  const res = await fetch(url, {
    ...options,
    headers,
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      // ignore parse errors
    }

    if (res.status === 401 && !path.startsWith('/auth/')) {
      const { useAuth } = await import('../composables/useAuth')
      const { clearUser } = useAuth()
      clearUser()
      const { default: router } = await import('../router')
      if (router.currentRoute.value.path !== '/login') {
        router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    }

    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}
