// STATUS: COMPLETE
'use client'

import { useEffect, useState } from 'react'
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
import { BACKEND_URL, cn, formatDate, formatDuration } from '@/lib/utils'
import type { JobLog } from '@/lib/types'

export default function SchedulerPage() {
  const supabase = createClient()
  const [jobs, setJobs] = useState<JobLog[]>([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)

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
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [supabase])

  async function runKeywordExpansion() {
    setTriggering(true)
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/scheduler/trigger/keyword_expansion`,
        { method: 'POST' }
      )
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || 'Failed to trigger job')
      }
      toast.success('Keyword expansion started — watch the log below')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to trigger job')
    } finally {
      setTriggering(false)
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
        </div>
        <Button onClick={runKeywordExpansion} disabled={triggering}>
          <Play className="mr-2 h-4 w-4" />
          {triggering ? 'Starting...' : 'Run keyword expansion now'}
        </Button>
      </div>

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
                  No jobs have run yet. The scheduler will log activity here.
                </TableCell>
              </TableRow>
            ) : (
              jobs.map((job, index) => (
                <TableRow
                  key={job.id}
                  className={cn(index === 0 && 'bg-blue-50/60')}
                >
                  <TableCell className="font-medium">{job.job_name ?? '—'}</TableCell>
                  <TableCell>
                    <JobStatusChip status={job.status ?? 'unknown'} />
                  </TableCell>
                  <TableCell>{formatDate(job.started_at)}</TableCell>
                  <TableCell>{formatDate(job.finished_at)}</TableCell>
                  <TableCell>
                    {job.started_at
                      ? formatDuration(job.started_at, job.finished_at)
                      : '—'}
                  </TableCell>
                  <TableCell className="max-w-xs truncate text-sm text-slate-600">
                    {job.message ?? '—'}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
