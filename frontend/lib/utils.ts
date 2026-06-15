// STATUS: COMPLETE
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getScoreColor(score: number): string {
  if (score >= 300) return 'text-green-600 bg-green-50'
  if (score >= 200) return 'text-amber-600 bg-amber-50'
  return 'text-red-600 bg-red-50'
}

export function getTrendColor(score: number): string {
  if (score >= 70) return 'text-green-600'
  if (score >= 40) return 'text-amber-600'
  return 'text-slate-400'
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return '—'
  return new Date(date).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function formatDuration(started: string, finished: string | null): string {
  if (!finished) return '—'
  const ms = new Date(finished).getTime() - new Date(started).getTime()
  if (ms < 1000) return `${ms}ms`
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

/** Jobs stuck as "running" with no finish time (legacy double-insert rows). */
export const STALE_JOB_HOURS = 2

export function isJobStale(job: {
  status: string | null
  started_at: string | null
  finished_at: string | null
}): boolean {
  if (job.status?.toLowerCase() !== 'running' || job.finished_at || !job.started_at) {
    return false
  }
  const ageMs = Date.now() - new Date(job.started_at).getTime()
  return ageMs > STALE_JOB_HOURS * 60 * 60 * 1000
}

export function resolveJobDisplayStatus(job: {
  status: string | null
  started_at: string | null
  finished_at: string | null
}): string {
  if (isJobStale(job)) return 'stale'
  return job.status?.toLowerCase() ?? 'unknown'
}

export function formatJobDuration(
  started: string | null,
  finished: string | null,
  displayStatus: string
): string {
  if (!started) return '—'
  if (finished) return formatDuration(started, finished)
  if (displayStatus === 'running') {
    const ms = Date.now() - new Date(started).getTime()
    const seconds = Math.floor(ms / 1000)
    if (seconds < 60) return `${seconds}s (running)`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s (running)`
  }
  return '—'
}

export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
