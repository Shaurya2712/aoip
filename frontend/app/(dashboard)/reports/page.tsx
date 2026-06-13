// STATUS: COMPLETE
'use client'

import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import { createClient } from '@/lib/supabase'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { BACKEND_URL } from '@/lib/utils'
import type { DailyReport } from '@/lib/types'

export default function ReportsPage() {
  const supabase = createClient()
  const [reportType, setReportType] = useState<'daily' | 'weekly'>('daily')
  const [report, setReport] = useState<DailyReport | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadReport() {
      setLoading(true)

      if (reportType === 'daily') {
        try {
          const response = await fetch(`${BACKEND_URL}/api/reports/daily`)
          if (response.ok) {
            const data = await response.json()
            setReport(data as DailyReport)
            setLoading(false)
            return
          }
        } catch {
          // Fall through to Supabase fallback
        }
      }

      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - (reportType === 'weekly' ? 7 : 1))

      const [
        { data: topOpportunities },
        { count: newKeywordsCount },
        { count: newConceptsCount },
        { data: topPain },
      ] = await Promise.all([
        supabase
          .from('opportunities')
          .select('final_score, ai_reasoning, keyword_id, keywords(keyword, niches(name))')
          .order('final_score', { ascending: false })
          .limit(reportType === 'weekly' ? 25 : 15),
        supabase
          .from('keywords')
          .select('*', { count: 'exact', head: true })
          .gte('created_at', yesterday.toISOString()),
        supabase
          .from('product_concepts')
          .select('*', { count: 'exact', head: true })
          .gte('generated_at', yesterday.toISOString()),
        supabase
          .from('community_insights')
          .select('text, confidence, niches(name)')
          .eq('type', 'pain_point')
          .order('confidence', { ascending: false })
          .limit(10),
      ])

      setReport({
        date: new Date().toISOString().slice(0, 10),
        type: reportType,
        generated_at: new Date().toISOString(),
        summary: {
          new_keywords_count: newKeywordsCount ?? 0,
          new_concepts_count: newConceptsCount ?? 0,
        },
        top_opportunities: (topOpportunities ?? []) as unknown as DailyReport['top_opportunities'],
        top_pain_points: (topPain ?? []) as unknown as DailyReport['top_pain_points'],
      })
      setLoading(false)
    }

    loadReport()
  }, [supabase, reportType])

  function downloadJson() {
    if (!report) return

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `aoip-${reportType}-report-${report.date ?? 'export'}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Reports</h1>
          <p className="mt-1 text-slate-600">
            Daily and weekly intelligence summaries
          </p>
        </div>

        <Button variant="outline" onClick={downloadJson} disabled={!report}>
          <Download className="h-4 w-4" />
          Download JSON
        </Button>
      </div>

      <Tabs
        value={reportType}
        onValueChange={(value) => {
          if (value === 'daily' || value === 'weekly') {
            setReportType(value)
          }
        }}
      >
        <TabsList>
          <TabsTrigger value="daily">Daily</TabsTrigger>
          <TabsTrigger value="weekly">Weekly</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? (
        <p className="text-slate-500">Loading report...</p>
      ) : !report ? (
        <Card className="border-dashed border-slate-300 bg-white">
          <CardContent className="py-10 text-center text-slate-500">
            No report data available yet.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader>
              <CardTitle>
                {reportType === 'daily' ? 'Daily' : 'Weekly'} Report — {report.date}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-3">
                <Badge variant="secondary">
                  {report.summary?.new_keywords_count ?? 0} new keywords
                </Badge>
                <Badge variant="secondary">
                  {report.summary?.new_concepts_count ?? 0} new concepts
                </Badge>
              </div>

              <div>
                <h3 className="mb-2 font-semibold text-slate-900">Top Opportunities</h3>
                {(report.top_opportunities ?? []).length === 0 ? (
                  <p className="text-sm text-slate-500">No opportunities scored yet.</p>
                ) : (
                  <ul className="space-y-2">
                    {(report.top_opportunities ?? []).map((opp, index) => (
                      <li
                        key={opp.id ?? index}
                        className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-sm"
                      >
                        <span>
                          {opp.keywords?.keyword ?? 'Unknown keyword'}
                          {opp.keywords?.niches?.name
                            ? ` · ${opp.keywords.niches.name}`
                            : ''}
                        </span>
                        <Badge variant="outline">
                          {Math.round(opp.final_score ?? 0)}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader>
              <CardTitle>Top Pain Points</CardTitle>
            </CardHeader>
            <CardContent>
              {(report.top_pain_points ?? []).length === 0 ? (
                <p className="text-sm text-slate-500">No community pain points yet.</p>
              ) : (
                <ul className="space-y-2">
                  {(report.top_pain_points ?? []).map((pain, index) => (
                    <li
                      key={pain.id ?? index}
                      className="flex items-start justify-between gap-3 rounded-md border border-slate-200 p-3 text-sm"
                    >
                      <span>{pain.text}</span>
                      <Badge variant="outline">
                        {Math.round((pain.confidence ?? 0) * 100)}%
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
