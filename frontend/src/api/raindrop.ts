import { apiFetch } from './client'

export interface RaindropSummary {
  total_sessions: number
  unique_users: number
  total_work_hours: number
  total_commands: number
  raindrop_adoption_pct: number
  avg_session_minutes: number
  productivity_pct: number
  total_saves: number
  unique_drawings: number
}

export interface DailyActiveUsers {
  date: string
  count: number
  users: string[]
}

export interface DailyStat {
  date: string
  count?: number
  hours?: number
}

export interface HourlyStat {
  hour: number
  count: number
}

export interface UserStat {
  user: string
  sessions: number
  work_hours: number
  commands: number
  raindrop_commands: number
  saves: number
  unique_drawings: number
}

export interface RaindropAnalytics {
  period: { start: string; end: string }
  summary: RaindropSummary
  daily_active_users: DailyActiveUsers[]
  daily_sessions: DailyStat[]
  daily_work_hours: DailyStat[]
  hourly_distribution: HourlyStat[]
  user_stats: UserStat[]
  insights: string[]
}

export interface RaindropException {
  timestamp: string
  user: string
  machine: string
  message: string
  drawing: string
  app_version: string
  level: string
  exception: string | { Type: string; Message: string; StackTrace?: string }
  stack_trace: string
}

export interface RaindropExceptions {
  exceptions: RaindropException[]
  count: number
}

export interface RaindropWarning {
  timestamp: string
  user: string
  machine: string
  message: string
  drawing: string
  app_version: string
  level: string
}

export interface RaindropWarnings {
  warnings: RaindropWarning[]
  count: number
}

export function getRaindropAnalytics(days: number): Promise<RaindropAnalytics> {
  return apiFetch(`/raindrop/analytics?days=${days}`)
}

export function getRaindropExceptions(days: number): Promise<RaindropExceptions> {
  return apiFetch(`/raindrop/exceptions?days=${days}`)
}

export function getRaindropWarnings(days: number): Promise<RaindropWarnings> {
  return apiFetch(`/raindrop/warnings?days=${days}`)
}
