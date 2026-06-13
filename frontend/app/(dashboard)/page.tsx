// STATUS: COMPLETE
import { createServerClient } from '@/lib/supabase'
import HomeDashboard from '@/components/HomeDashboard'
import type { Niche, Opportunity } from '@/lib/types'

export default async function HomePage() {
  const supabase = createServerClient()

  const [
    { count: opportunitiesCount },
    { count: keywordsCount },
    { count: conceptsCount },
    { data: lastJob },
    { data: topOpportunities },
    { data: niches },
    { data: keywordCounts },
  ] = await Promise.all([
    supabase.from('opportunities').select('*', { count: 'exact', head: true }),
    supabase.from('keywords').select('*', { count: 'exact', head: true }),
    supabase.from('product_concepts').select('*', { count: 'exact', head: true }),
    supabase
      .from('job_log')
      .select('started_at')
      .order('started_at', { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase
      .from('opportunities')
      .select(
        '*, keywords(keyword, niche_id, niches(name)), product_concepts(app_name, tagline, price_suggestion, build_time_weeks, target_audience, core_features, premium_features, monetization, tech_stack, full_concept)'
      )
      .order('final_score', { ascending: false })
      .limit(10),
    supabase
      .from('niches')
      .select('*')
      .eq('enabled', true)
      .order('priority', { ascending: false }),
    supabase.from('keywords').select('niche_id'),
  ])

  const countsByNiche = (keywordCounts ?? []).reduce<Record<string, number>>(
    (acc: Record<string, number>, row: { niche_id: string | null }) => {
      if (row.niche_id) {
        acc[row.niche_id] = (acc[row.niche_id] ?? 0) + 1
      }
      return acc
    },
    {}
  )

  const activeNiches = ((niches ?? []) as Niche[]).map((niche) => ({
    ...niche,
    keywordCount: countsByNiche[niche.id] ?? 0,
  }))

  return (
    <HomeDashboard
      stats={{
        opportunities: opportunitiesCount ?? 0,
        keywords: keywordsCount ?? 0,
        concepts: conceptsCount ?? 0,
        lastJobRun: lastJob?.started_at ?? null,
      }}
      topOpportunities={(topOpportunities ?? []) as Opportunity[]}
      activeNiches={activeNiches}
    />
  )
}
