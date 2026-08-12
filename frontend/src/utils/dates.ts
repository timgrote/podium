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

const fmt = (d: Date) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// First day of the month containing dateStr
export function monthStart(dateStr?: string): string {
  const d = parseLocalDate(dateStr || todayStr())
  return fmt(new Date(d.getFullYear(), d.getMonth(), 1))
}

// Last day of the month containing dateStr
export function monthEnd(dateStr?: string): string {
  const d = parseLocalDate(dateStr || todayStr())
  return fmt(new Date(d.getFullYear(), d.getMonth() + 1, 0))
}

// Number of days in the month containing dateStr
export function daysInMonth(dateStr?: string): number {
  const d = parseLocalDate(dateStr || todayStr())
  return new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate()
}

// Standard Monday-start month grid (6 weeks) as rows of date strings.
// Leading/trailing cells bleed into adjacent months so the grid is rectangular.
export function monthGrid(dateStr?: string): string[][] {
  const d = parseLocalDate(dateStr || todayStr())
  const first = new Date(d.getFullYear(), d.getMonth(), 1)
  const start = startOfWeek(fmt(first))
  const cells: string[] = []
  const startDate = parseLocalDate(start)
  for (let i = 0; i < 42; i++) {
    const c = new Date(startDate)
    c.setDate(startDate.getDate() + i)
    cells.push(fmt(c))
  }
  // split into 6 rows of 7
  const rows: string[][] = []
  for (let i = 0; i < 6; i++) rows.push(cells.slice(i * 7, i * 7 + 7))
  return rows
}

export function startOfWeek(dateStr?: string): string {
  return isoWeekRange(dateStr).start
}

export function addMonthsStr(dateStr: string, months: number): string {
  const d = parseLocalDate(dateStr)
  return fmt(new Date(d.getFullYear(), d.getMonth() + months, d.getDate()))
}

export function addDays(dateStr: string, days: number): string {
  return addDaysStr(dateStr, days)
}

// Human label for a column header: 'Mon' | 'Tue' ... from a date string
export function weekdayShort(dateStr: string): string {
  return parseLocalDate(dateStr).toLocaleDateString('en-US', { weekday: 'short' })
}

// Range of consecutive days from start, count days long.
export function dayRange(start: string, count: number): string[] {
  const out: string[] = []
  for (let i = 0; i < count; i++) out.push(addDaysStr(start, i))
  return out
}
