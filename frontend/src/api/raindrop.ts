import { apiFetch } from './client'

export interface RaindropSummary {
  total_sessions: number
  unique_users: number
  total_work_hours: number
  total_work_hours_prev: number
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
  unique_count: number
  unique_count_prev: number
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

export interface RaindropTrial {
  name: string
  email: string
  created: string | null
  expiry: string | null
  days_remaining?: number
  days_since_expiry?: number
}

export interface RaindropTrials {
  active: RaindropTrial[]
  expired_recent: RaindropTrial[]
  active_count: number
  expired_recent_count: number
  active_trials_prev: number
  licensed_active_count: number
  licensed_active_prev: number
  available: boolean
}

export function getRaindropTrials(days: number): Promise<RaindropTrials> {
  return apiFetch(`/raindrop/trials?days=${days}`)
}

export interface RaindropLeaderboard {
  user_stats: UserStat[]
  period: { start: string; end: string }
}

export function getRaindropLeaderboard(): Promise<RaindropLeaderboard> {
  return apiFetch('/raindrop/leaderboard')
}

export interface RaindropYearly {
  labels: string[]
  licensed_users: number[]
  active_trials: number[]
}

export function getRaindropYearly(): Promise<RaindropYearly> {
  return apiFetch('/raindrop/yearly')
}
