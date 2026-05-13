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

export function daysPastDue(dateStr: string | null): number {
  if (!dateStr) return 0
  const now = new Date()
  const today = new Date(now.toLocaleDateString('en-US', { timeZone: TZ }))
  const due = parseLocalDate(dateStr)
  const diff = today.getTime() - due.getTime()
  return diff > 0 ? Math.floor(diff / (1000 * 60 * 60 * 24)) : 0
}

export function todayStr(): string {
  const now = new Date()
  const parts = now.toLocaleDateString('en-US', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
  const [m, d, y] = parts.split('/')
  return `${y}-${m}-${d}`
}

export function addDaysStr(dateStr: string, days: number): string {
  const d = parseLocalDate(dateStr)
  d.setDate(d.getDate() + days)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function nextMondayStr(fromDateStr?: string): string {
  const base = fromDateStr ? parseLocalDate(fromDateStr) : parseLocalDate(todayStr())
  const dayOfWeek = base.getDay()  // 0=Sun, 1=Mon, ..., 6=Sat
  const daysUntil = ((1 - dayOfWeek + 7) % 7) || 7  // always future Monday
  base.setDate(base.getDate() + daysUntil)
  const y = base.getFullYear()
  const m = String(base.getMonth() + 1).padStart(2, '0')
  const d = String(base.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function isoWeekRange(fromDateStr?: string): { start: string; end: string } {
  const base = fromDateStr ? parseLocalDate(fromDateStr) : parseLocalDate(todayStr())
  const dayOfWeek = base.getDay() || 7  // treat Sun as 7
  const monday = new Date(base)
  monday.setDate(base.getDate() - (dayOfWeek - 1))
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  const fmt = (d: Date) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  return { start: fmt(monday), end: fmt(sunday) }
}
