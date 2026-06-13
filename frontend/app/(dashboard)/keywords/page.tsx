// STATUS: COMPLETE
'use client'

import { useEffect, useMemo, useState } from 'react'
import { createClient } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn, formatDate, getTrendColor } from '@/lib/utils'
import type { Keyword, Niche } from '@/lib/types'

const PAGE_SIZE = 100

export default function KeywordsPage() {
  const supabase = createClient()
  const [keywords, setKeywords] = useState<Keyword[]>([])
  const [niches, setNiches] = useState<Niche[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [nicheFilter, setNicheFilter] = useState('all')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [page, setPage] = useState(0)
  const [totalCount, setTotalCount] = useState(0)

  useEffect(() => {
    async function loadNiches() {
      const { data } = await supabase.from('niches').select('*').order('name')
      setNiches((data ?? []) as Niche[])
    }

    loadNiches()
  }, [supabase])

  useEffect(() => {
    async function loadKeywords() {
      setLoading(true)

      let query = supabase
        .from('keywords')
        .select('*, niches(name)', { count: 'exact' })
        .order('trend_score', { ascending: false, nullsFirst: false })

      if (nicheFilter !== 'all') {
        query = query.eq('niche_id', nicheFilter)
      }

      if (sourceFilter !== 'all') {
        query = query.eq('source', sourceFilter)
      }

      if (search.trim()) {
        query = query.ilike('keyword', `%${search.trim()}%`)
      }

      const from = page * PAGE_SIZE
      const to = from + PAGE_SIZE - 1

      const { data, count, error } = await query.range(from, to)

      if (error) {
        console.error(error)
      }

      setKeywords((data ?? []) as Keyword[])
      setTotalCount(count ?? 0)
      setLoading(false)
    }

    loadKeywords()
  }, [supabase, search, nicheFilter, sourceFilter, page])

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE))

  const pageLabel = useMemo(() => {
    const start = totalCount === 0 ? 0 : page * PAGE_SIZE + 1
    const end = Math.min((page + 1) * PAGE_SIZE, totalCount)
    return `${start}–${end} of ${totalCount}`
  }, [page, totalCount])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Keywords</h1>
        <p className="mt-1 text-slate-600">
          Seed and AI-expanded keywords with trend scores
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="min-w-[220px] flex-1 space-y-2">
          <Label htmlFor="search">Search</Label>
          <Input
            id="search"
            placeholder="Filter by keyword..."
            value={search}
            onChange={(e) => {
              setPage(0)
              setSearch(e.target.value)
            }}
          />
        </div>

        <div className="space-y-2">
          <Label>Niche</Label>
          <Select
            value={nicheFilter}
            onValueChange={(value) => {
              if (value) {
                setPage(0)
                setNicheFilter(value)
              }
            }}
          >
            <SelectTrigger className="w-44">
              <SelectValue placeholder="All niches" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All niches</SelectItem>
              {niches.map((niche) => (
                <SelectItem key={niche.id} value={niche.id}>
                  {niche.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Source</Label>
          <Select
            value={sourceFilter}
            onValueChange={(value) => {
              if (value) {
                setPage(0)
                setSourceFilter(value)
              }
            }}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="All sources" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All sources</SelectItem>
              <SelectItem value="seed">Seed</SelectItem>
              <SelectItem value="ai_expand">AI Expand</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Keyword</TableHead>
              <TableHead>Niche</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Demand</TableHead>
              <TableHead>Growth</TableHead>
              <TableHead>Stability</TableHead>
              <TableHead>Trend Score</TableHead>
              <TableHead>Discovered At</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-slate-500">
                  Loading keywords...
                </TableCell>
              </TableRow>
            ) : keywords.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-slate-500">
                  No keywords found.
                </TableCell>
              </TableRow>
            ) : (
              keywords.map((keyword) => (
                <TableRow key={keyword.id}>
                  <TableCell className="font-medium">{keyword.keyword}</TableCell>
                  <TableCell>{keyword.niches?.name ?? '—'}</TableCell>
                  <TableCell>{keyword.source ?? '—'}</TableCell>
                  <TableCell>{keyword.demand_score ?? '—'}</TableCell>
                  <TableCell>{keyword.growth_score ?? '—'}</TableCell>
                  <TableCell>{keyword.stability_score ?? '—'}</TableCell>
                  <TableCell>
                    <span
                      className={cn(
                        'font-semibold',
                        getTrendColor(keyword.trend_score ?? 0)
                      )}
                    >
                      {keyword.trend_score ?? '—'}
                    </span>
                  </TableCell>
                  <TableCell>{formatDate(keyword.created_at)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">{pageLabel}</p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page + 1 >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
