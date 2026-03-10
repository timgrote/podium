const TZ = 'America/Denver'

export function parseLocalDate(dateStr: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    const parts = dateStr.split('-').map(Number)
    return new Date(parts[0]!, parts[1]! - 1, parts[2]!)
  }
  return new Date(dateStr)
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  return parseLocalDate(dateStr).toLocaleDateString('en-US', { timeZone: TZ })
}

export function formatDateShort(dateStr: string | null): string {
  if (!dateStr) return '-'
  return parseLocalDate(dateStr).toLocaleDateString('en-US', { timeZone: TZ, month: 'short', day: 'numeric' })
}

export function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('en-US', { timeZone: TZ })
}

export function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false
  const now = new Date()
  const today = new Date(now.toLocaleDateString('en-US', { timeZone: TZ }))
  return parseLocalDate(dateStr) < today
}

export function todayStr(): string {
  const now = new Date()
  const parts = now.toLocaleDateString('en-US', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
  const [m, d, y] = parts.split('/')
  return `${y}-${m}-${d}`
}
