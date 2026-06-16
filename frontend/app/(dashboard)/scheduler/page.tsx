// STATUS: COMPLETE
'use client'

import { useEffect, useMemo, useState } from 'react'
import { Play } from 'lucide-react'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import JobStatusChip from '@/components/JobStatusChip'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  BACKEND_URL,
  cn,
  formatDate,
  formatJobDuration,
  isJobStale,
  resolveJobDisplayStatus,
} from '@/lib/utils'
import type { JobLog } from '@/lib/types'

const PIPELINE_JOBS = [
  {
    id: 'pipeline_cycle',
    label: 'Full pipeline',
    description: 'm3 → m4 → m7 in one run (trends, Play Store, opportunities)',
    primary: true,
  },
  {
    id: 'keyword_expansion',
    label: 'Keyword expansion',
    description: 'm2 — expand seed keywords via AI',
  },
  {
    id: 'trend_analysis',
    label: 'Trend analysis',
    description: 'm3 — Google Trends scoring',
  },
  {
    id: 'playstore_intel',
    label: 'Play Store intel',
    description: 'm4 — competitor discovery',
  },
  {
    id: 'opportunity_scoring',
    label: 'Opportunity scoring',
    description: 'm7 — score app opportunities',
  },
] as const

type JobSchedule = { interval_minutes?: number; cron?: string }

type ScheduleInfo = {
  pipeline_chain_enabled?: boolean
  pipeline_interval_minutes?: number
  trend_analysis?: JobSchedule
  playstore_intel?: JobSchedule
  opportunity_scoring?: JobSchedule
}

function formatInterval(minutes: number | undefined): string {
  if (!minutes) return '—'
  if (minutes < 60) return `${minutes} min`
  const h = minutes / 60
  return Number.isInteger(h) ? `${h}h` : `${h.toFixed(1)}h`
}

type PipelineCounts = {
  keywords: number
  withTrendScore: number
  competitors: number
  opportunities: number
  communityInsights: number
}

export default function SchedulerPage() {
  const supabase = createClient()
  const [jobs, setJobs] = useState<JobLog[]>([])
  const [loading, setLoading] = useState(true)
  const [triggeringJob, setTriggeringJob] = useState<string | null>(null)
  const [pipeline, setPipeline] = useState<PipelineCounts | null>(null)
  const [schedule, setSchedule] = useState<ScheduleInfo | null>(null)

  async function loadSchedule() {
    try {
      const response = await fetch(`${BACKEND_URL}/api/scheduler/schedule`)
      if (response.ok) {
        setSchedule((await response.json()) as ScheduleInfo)
      }
    } catch {
      // Backend may be unreachable; schedule banner is optional
    }
  }

  async function loadPipelineCounts() {
    const [
      { count: keywords },
      { count: withTrendScore },
      { count: competitors },
      { count: opportunities },
      { count: communityInsights },
    ] = await Promise.all([
      supabase.from('keywords').select('*', { count: 'exact', head: true }),
      supabase
        .from('keywords')
        .select('*', { count: 'exact', head: true })
        .not('trend_score', 'is', null),
      supabase.from('competitors').select('*', { count: 'exact', head: true }),
      supabase.from('opportunities').select('*', { count: 'exact', head: true }),
      supabase.from('community_insights').select('*', { count: 'exact', head: true }),
    ])
    setPipeline({
      keywords: keywords ?? 0,
      withTrendScore: withTrendScore ?? 0,
      competitors: competitors ?? 0,
      opportunities: opportunities ?? 0,
      communityInsights: communityInsights ?? 0,
    })
  }

  useEffect(() => {
    async function loadJobs() {
      setLoading(true)
      const { data } = await supabase
        .from('job_log')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(50)

      setJobs((data ?? []) as JobLog[])
      setLoading(false)
      await Promise.all([loadPipelineCounts(), loadSchedule()])
    }

    loadJobs()

    const channel = supabase
      .channel('job_log_changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'job_log' },
        async () => {
          const { data } = await supabase
            .from('job_log')
            .select('*')
            .order('started_at', { ascending: false })
            .limit(50)

          setJobs((data ?? []) as JobLog[])
          await loadPipelineCounts()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [supabase])

  const activeJob = useMemo(
    () =>
      jobs.find(
        (job) =>
          job.status?.toLowerCase() === 'running' &&
          !job.finished_at &&
          !isJobStale(job)
      ),
    [jobs]
  )

  const staleCount = useMemo(
    () => jobs.filter((job) => isJobStale(job)).length,
    [jobs]
  )

  async function triggerJob(jobId: string, label: string) {
    setTriggeringJob(jobId)
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/scheduler/trigger/${jobId}`,
        { method: 'POST' }
      )
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || 'Failed to trigger job')
      }
      toast.success(`${label} started — watch the log below`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to trigger job')
    } finally {
      setTriggeringJob(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Scheduler Status</h1>
          <p className="mt-1 text-slate-600">
            Live job log with realtime updates from Supabase
          </p>
          {schedule?.pipeline_chain_enabled && (
            <p className="mt-2 text-sm text-slate-500">
              Auto pipeline (m3→m4→m7) every{' '}
              <strong>{formatInterval(schedule.pipeline_interval_minutes)}</strong>
              {' · '}Only one job runs at a time
            </p>
          )}
          {schedule && !schedule.pipeline_chain_enabled && (
            <p className="mt-2 text-sm text-slate-500">
              Auto: trends {formatInterval(schedule.trend_analysis?.interval_minutes)} · Play
              Store {formatInterval(schedule.playstore_intel?.interval_minutes)} · opportunities{' '}
              {formatInterval(schedule.opportunity_scoring?.interval_minutes)}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {PIPELINE_JOBS.map((job) => (
            <Button
              key={job.id}
              variant={'primary' in job && job.primary ? 'default' : 'outline'}
              onClick={() => triggerJob(job.id, job.label)}
              disabled={!!triggeringJob || !!activeJob}
              title={job.description}
            >
              <Play className="mr-2 h-4 w-4" />
              {triggeringJob === job.id ? 'Starting...' : job.label}
            </Button>
          ))}
        </div>
      </div>

      {pipeline && (
        <div className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 text-sm shadow-sm sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <p className="text-slate-500">Keywords</p>
            <p className="text-xl font-semibold text-slate-900">{pipeline.keywords}</p>
          </div>
          <div>
            <p className="text-slate-500">With trend score (m3)</p>
            <p className="text-xl font-semibold text-slate-900">{pipeline.withTrendScore}</p>
          </div>
          <div>
            <p className="text-slate-500">Competitors (m4)</p>
            <p className="text-xl font-semibold text-slate-900">{pipeline.competitors}</p>
          </div>
          <div>
            <p className="text-slate-500">Opportunities (m7)</p>
            <p className="text-xl font-semibold text-slate-900">{pipeline.opportunities}</p>
          </div>
          <div>
            <p className="text-slate-500">Community insights (m6)</p>
            <p className="text-xl font-semibold text-slate-900">{pipeline.communityInsights}</p>
          </div>
        </div>
      )}

      {pipeline && pipeline.withTrendScore === 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Pipeline is blocked at <strong>Trend analysis (m3)</strong>. Keywords exist but none have{' '}
          <code className="text-xs">trend_score</code> yet — run Trend analysis after deploying the
          latest backend. Google Trends often 429s on Render; the job can still AI-estimate a few
          keywords per run.
        </div>
      )}

      {pipeline && pipeline.communityInsights === 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          <strong>Community</strong> is empty until m6 runs with real Reddit API credentials on
          Render (<code className="text-xs">REDDIT_CLIENT_ID</code> /{' '}
          <code className="text-xs">REDDIT_CLIENT_SECRET</code>).
        </div>
      )}

      {activeJob && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          <span className="font-medium">{activeJob.job_name}</span> is running
          {activeJob.started_at
            ? ` (started ${formatDate(activeJob.started_at)})`
            : ''}
          . Other jobs are queued until it finishes.
        </div>
      )}

      {staleCount > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {staleCount} older log {staleCount === 1 ? 'entry' : 'entries'} marked{' '}
          <strong>Stale</strong> — these are legacy &quot;running&quot; rows from before
          logging was fixed (the job finished but the row was never updated). New runs
          update a single row to Success or Error.
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Job Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Finished</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Message</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-slate-500">
                  Loading job log...
                </TableCell>
              </TableRow>
            ) : jobs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-slate-500">
                  No jobs have run yet. Use the buttons above to start the pipeline.
                </TableCell>
              </TableRow>
            ) : (
              jobs.map((job, index) => {
                const displayStatus = resolveJobDisplayStatus(job)
                return (
                  <TableRow
                    key={job.id}
                    className={cn(
                      index === 0 && displayStatus === 'running' && 'bg-blue-50/60'
                    )}
                  >
                    <TableCell className="font-medium">
                      {job.job_name ?? '—'}
                    </TableCell>
                    <TableCell>
                      <JobStatusChip status={displayStatus} />
                    </TableCell>
                    <TableCell>{formatDate(job.started_at)}</TableCell>
                    <TableCell>{formatDate(job.finished_at)}</TableCell>
                    <TableCell>
                      {formatJobDuration(
                        job.started_at,
                        job.finished_at,
                        displayStatus
                      )}
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-sm text-slate-600">
                      {displayStatus === 'stale'
                        ? 'Interrupted or legacy log row (not still running)'
                        : (job.message ?? '—')}
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
