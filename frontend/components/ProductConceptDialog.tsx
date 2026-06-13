// STATUS: COMPLETE
'use client'

import type { Opportunity, ProductConcept } from '@/lib/types'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface ProductConceptDialogProps {
  opportunity: Opportunity | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function getProductConcept(opportunity: Opportunity): ProductConcept | null {
  const concepts = opportunity.product_concepts
  if (!concepts) return null
  if (Array.isArray(concepts)) return concepts[0] ?? null
  return concepts
}

export default function ProductConceptDialog({
  opportunity,
  open,
  onOpenChange,
}: ProductConceptDialogProps) {
  if (!opportunity) return null

  const concept = getProductConcept(opportunity)
  const keyword = opportunity.keywords?.keyword ?? 'Opportunity'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{concept?.app_name || keyword}</DialogTitle>
        </DialogHeader>

        {!concept ? (
          <p className="text-sm text-slate-600">
            No product concept generated yet for this opportunity.
          </p>
        ) : (
          <div className="space-y-4 text-sm text-slate-700">
            {concept.tagline && (
              <p className="text-base italic text-slate-900">{concept.tagline}</p>
            )}

            {concept.target_audience && (
              <div>
                <h4 className="mb-1 font-semibold text-slate-900">Target Audience</h4>
                <p>{concept.target_audience}</p>
              </div>
            )}

            {concept.core_features && concept.core_features.length > 0 && (
              <div>
                <h4 className="mb-1 font-semibold text-slate-900">Core Features</h4>
                <ul className="list-disc space-y-1 pl-5">
                  {concept.core_features.map((feature) => (
                    <li key={feature}>{feature}</li>
                  ))}
                </ul>
              </div>
            )}

            {concept.premium_features && concept.premium_features.length > 0 && (
              <div>
                <h4 className="mb-1 font-semibold text-slate-900">Premium Features</h4>
                <ul className="list-disc space-y-1 pl-5">
                  {concept.premium_features.map((feature) => (
                    <li key={feature}>{feature}</li>
                  ))}
                </ul>
              </div>
            )}

            {concept.monetization && (
              <div>
                <h4 className="mb-1 font-semibold text-slate-900">Monetization</h4>
                <p>{concept.monetization}</p>
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-3">
              {concept.price_suggestion && (
                <div>
                  <h4 className="mb-1 font-semibold text-slate-900">Price</h4>
                  <p>{concept.price_suggestion}</p>
                </div>
              )}
              {concept.build_time_weeks != null && (
                <div>
                  <h4 className="mb-1 font-semibold text-slate-900">Build Time</h4>
                  <p>{concept.build_time_weeks} weeks</p>
                </div>
              )}
              {concept.tech_stack && (
                <div>
                  <h4 className="mb-1 font-semibold text-slate-900">Tech Stack</h4>
                  <p>{concept.tech_stack}</p>
                </div>
              )}
            </div>

            {concept.full_concept && (
              <div>
                <h4 className="mb-1 font-semibold text-slate-900">Full Concept</h4>
                <p className="leading-relaxed">{concept.full_concept}</p>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
