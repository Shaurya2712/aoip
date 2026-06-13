// STATUS: COMPLETE
'use client'

import { useEffect, useMemo, useState } from 'react'
import { createClient } from '@/lib/supabase'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { BACKEND_URL } from '@/lib/utils'
import type { Competitor, ReviewInsight } from '@/lib/types'

interface CompetitorRow extends Competitor {
  keywords?: { keyword: string } | null
}

export default function CompetitorsPage() {
  const supabase = createClient()
  const [competitors, setCompetitors] = useState<CompetitorRow[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<CompetitorRow | null>(null)
  const [insights, setInsights] = useState<ReviewInsight[]>([])
  const [insightsLoading, setInsightsLoading] = useState(false)
  const [sheetOpen, setSheetOpen] = useState(false)

  useEffect(() => {
    async function loadCompetitors() {
      setLoading(true)
      const { data } = await supabase
        .from('competitors')
        .select('*, keywords(keyword)')
        .order('rating', { ascending: false })
        .limit(500)

      setCompetitors((data ?? []) as CompetitorRow[])
      setLoading(false)
    }

    loadCompetitors()
  }, [supabase])

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return competitors

    return competitors.filter((competitor) => {
      const keyword = competitor.keywords?.keyword?.toLowerCase() ?? ''
      const appName = competitor.app_name?.toLowerCase() ?? ''
      return keyword.includes(term) || appName.includes(term)
    })
  }, [competitors, search])

  async function openInsights(competitor: CompetitorRow) {
    setSelected(competitor)
    setSheetOpen(true)
    setInsightsLoading(true)

    try {
      const response = await fetch(
        `${BACKEND_URL}/api/competitors/${competitor.id}/insights`
      )
      if (response.ok) {
        const data = await response.json()
        setInsights(data as ReviewInsight[])
      } else {
        const { data } = await supabase
          .from('review_insights')
          .select('*')
          .eq('competitor_id', competitor.id)
          .order('frequency', { ascending: false })

        setInsights((data ?? []) as ReviewInsight[])
      }
    } catch {
      const { data } = await supabase
        .from('review_insights')
        .select('*')
        .eq('competitor_id', competitor.id)
        .order('frequency', { ascending: false })

      setInsights((data ?? []) as ReviewInsight[])
    } finally {
      setInsightsLoading(false)
    }
  }

  const complaints = insights.filter((item) => item.type === 'complaint')
  const featureRequests = insights.filter((item) => item.type === 'feature_request')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Competitors</h1>
        <p className="mt-1 text-slate-600">
          Play Store apps discovered for tracked keywords
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="max-w-md space-y-2">
          <Label htmlFor="keyword-search">Keyword search</Label>
          <Input
            id="keyword-search"
            placeholder="Search by app name or keyword..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>App Name</TableHead>
              <TableHead>Keyword</TableHead>
              <TableHead>Downloads</TableHead>
              <TableHead>Rating</TableHead>
              <TableHead>Reviews</TableHead>
              <TableHead>Has Ads</TableHead>
              <TableHead>Competition Score</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-slate-500">
                  Loading competitors...
                </TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-slate-500">
                  No competitors found.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((competitor) => (
                <TableRow key={competitor.id}>
                  <TableCell className="font-medium">
                    {competitor.app_name ?? '—'}
                  </TableCell>
                  <TableCell>{competitor.keywords?.keyword ?? '—'}</TableCell>
                  <TableCell>{competitor.downloads ?? '—'}</TableCell>
                  <TableCell>{competitor.rating ?? '—'}</TableCell>
                  <TableCell>{competitor.review_count ?? '—'}</TableCell>
                  <TableCell>{competitor.has_ads ? 'Yes' : 'No'}</TableCell>
                  <TableCell>{competitor.competition_score ?? '—'}</TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openInsights(competitor)}
                    >
                      Insights
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>{selected?.app_name ?? 'Review Insights'}</SheetTitle>
          </SheetHeader>

          {insightsLoading ? (
            <p className="mt-6 text-sm text-slate-500">Loading insights...</p>
          ) : (
            <div className="mt-6 space-y-6">
              <section>
                <h3 className="mb-3 font-semibold text-slate-900">Complaints</h3>
                {complaints.length === 0 ? (
                  <p className="text-sm text-slate-500">No complaints mined yet.</p>
                ) : (
                  <ul className="space-y-2">
                    {complaints.map((item) => (
                      <li
                        key={item.id}
                        className="flex items-start justify-between gap-3 rounded-md border border-slate-200 p-3"
                      >
                        <span className="text-sm text-slate-700">{item.text}</span>
                        <Badge variant="secondary">{item.frequency}×</Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section>
                <h3 className="mb-3 font-semibold text-slate-900">Feature Requests</h3>
                {featureRequests.length === 0 ? (
                  <p className="text-sm text-slate-500">No feature requests mined yet.</p>
                ) : (
                  <ul className="space-y-2">
                    {featureRequests.map((item) => (
                      <li
                        key={item.id}
                        className="flex items-start justify-between gap-3 rounded-md border border-slate-200 p-3"
                      >
                        <span className="text-sm text-slate-700">{item.text}</span>
                        <Badge variant="secondary">{item.frequency}×</Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
