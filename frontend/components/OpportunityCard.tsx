// STATUS: COMPLETE
'use client'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn, getScoreColor } from '@/lib/utils'
import type { Opportunity, ProductConcept } from '@/lib/types'

interface OpportunityCardProps {
  opportunity: Opportunity
  onViewConcept?: () => void
}

function getProductConcept(opportunity: Opportunity): ProductConcept | null {
  const concepts = opportunity.product_concepts
  if (!concepts) return null
  if (Array.isArray(concepts)) return concepts[0] ?? null
  return concepts
}

export default function OpportunityCard({ opportunity, onViewConcept }: OpportunityCardProps) {
  const score = opportunity.final_score ?? 0
  const keyword = opportunity.keywords?.keyword ?? 'Unknown keyword'
  const niche = opportunity.keywords?.niches?.name ?? 'Unknown niche'
  const concept = getProductConcept(opportunity)

  return (
    <Card className="border-slate-200 bg-white shadow-sm">
      <CardContent className="p-5">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-slate-900">{keyword}</h3>
            <Badge variant="secondary" className="mt-1">
              {niche}
            </Badge>
          </div>
          <div
            className={cn(
              'rounded-lg px-3 py-2 text-center',
              getScoreColor(score)
            )}
          >
            <div className="text-2xl font-bold">{Math.round(score)}</div>
            <div className="text-xs uppercase tracking-wide">Score</div>
          </div>
        </div>

        <div className="mb-3 flex flex-wrap gap-2">
          <Badge variant="outline" className="text-xs">
            Demand {Math.round(opportunity.demand_score ?? 0)}
          </Badge>
          <Badge variant="outline" className="text-xs">
            Growth {Math.round(opportunity.growth_score ?? 0)}
          </Badge>
          <Badge variant="outline" className="text-xs">
            Competition -{Math.round(opportunity.competition_penalty ?? 0)}
          </Badge>
        </div>

        {concept?.app_name && (
          <div className="mb-3 rounded-md bg-slate-50 p-3">
            <p className="italic font-medium text-slate-800">{concept.app_name}</p>
            {concept.tagline && (
              <p className="mt-1 text-sm text-slate-600">{concept.tagline}</p>
            )}
            {concept.build_time_weeks != null && (
              <p className="mt-1 text-xs text-slate-500">
                Est. build time: {concept.build_time_weeks} weeks
              </p>
            )}
          </div>
        )}

        {onViewConcept && (
          <Button variant="outline" size="sm" onClick={onViewConcept}>
            View Full Concept
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
