// STATUS: COMPLETE
'use client'

import { useState } from 'react'
import OpportunityCard from '@/components/OpportunityCard'
import ProductConceptDialog from '@/components/ProductConceptDialog'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate } from '@/lib/utils'
import type { Niche, Opportunity } from '@/lib/types'

interface HomeDashboardProps {
  stats: {
    opportunities: number
    keywords: number
    concepts: number
    lastJobRun: string | null
  }
  topOpportunities: Opportunity[]
  activeNiches: Array<Niche & { keywordCount: number }>
}

export default function HomeDashboard({
  stats,
  topOpportunities,
  activeNiches,
}: HomeDashboardProps) {
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  function openConcept(opportunity: Opportunity) {
    setSelectedOpportunity(opportunity)
    setDialogOpen(true)
  }

  const statCards = [
    { label: 'Total Opportunities', value: stats.opportunities },
    { label: 'Keywords Discovered', value: stats.keywords },
    { label: 'Concepts Generated', value: stats.concepts },
    { label: 'Last Job Run', value: stats.lastJobRun ? formatDate(stats.lastJobRun) : '—' },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Opportunity Dashboard</h1>
        <p className="mt-1 text-slate-600">
          Real-time overview of your app opportunity pipeline
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((stat) => (
          <Card key={stat.label} className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500">
                {stat.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-slate-900">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <section>
        <h2 className="mb-4 text-xl font-semibold text-slate-900">Top 10 Opportunities</h2>
        {topOpportunities.length === 0 ? (
          <Card className="border-dashed border-slate-300 bg-white">
            <CardContent className="py-10 text-center text-slate-500">
              No opportunities yet — add seed keywords to get started
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {topOpportunities.map((opportunity) => (
              <OpportunityCard
                key={opportunity.id}
                opportunity={opportunity}
                onViewConcept={() => openConcept(opportunity)}
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold text-slate-900">Active Niches</h2>
        {activeNiches.length === 0 ? (
          <p className="text-slate-500">No active niches configured yet.</p>
        ) : (
          <div className="flex flex-wrap gap-3">
            {activeNiches.map((niche) => (
              <Badge key={niche.id} variant="secondary" className="px-3 py-2 text-sm">
                {niche.name} · {niche.keywordCount} keywords
              </Badge>
            ))}
          </div>
        )}
      </section>

      <ProductConceptDialog
        opportunity={selectedOpportunity}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  )
}
