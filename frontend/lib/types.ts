// STATUS: COMPLETE

export interface Niche {
  id: string
  name: string
  priority: number
  enabled: boolean
  created_at?: string
  seed_keywords?: { count: number }[]
}

export interface Keyword {
  id: string
  keyword: string
  niche_id: string
  source: string | null
  parent_keyword: string | null
  demand_score: number | null
  growth_score: number | null
  stability_score: number | null
  seasonal_score: number | null
  trend_score: number | null
  last_scored_at: string | null
  created_at: string
  niches?: { name: string } | null
}

export interface ProductConcept {
  app_name: string | null
  tagline: string | null
  target_audience: string | null
  core_features: string[] | null
  premium_features: string[] | null
  monetization: string | null
  price_suggestion: string | null
  tech_stack: string | null
  build_time_weeks: number | null
  full_concept: string | null
}

export interface Opportunity {
  id: string
  keyword_id: string
  demand_score: number | null
  growth_score: number | null
  pain_point_score: number | null
  community_score: number | null
  monetization_score: number | null
  competition_penalty: number | null
  complexity_penalty: number | null
  final_score: number | null
  ai_reasoning: string | null
  scored_at: string | null
  keywords?: {
    keyword: string
    niche_id: string
    niches?: { name: string } | null
  } | null
  product_concepts?: ProductConcept | ProductConcept[] | null
}

export interface Competitor {
  id: string
  keyword_id: string
  app_id: string
  app_name: string | null
  category: string | null
  downloads: string | null
  rating: number | null
  review_count: number | null
  last_updated: string | null
  has_ads: boolean | null
  has_iap: boolean | null
  subscription: string | null
  competition_score: number | null
  saturation_score: number | null
  fetched_at: string | null
  keywords?: { keyword: string } | null
}

export interface ReviewInsight {
  id: string
  competitor_id: string
  type: string
  text: string
  frequency: number
  created_at?: string
}

export interface CommunityInsight {
  id: string
  niche_id: string
  type: string
  text: string
  confidence: number | null
  created_at?: string
  niches?: { name: string } | null
}

export interface CommunityPost {
  id: string
  niche_id: string
  source: string | null
  subreddit: string | null
  title: string | null
  content: string | null
  upvotes: number | null
  url: string | null
  fetched_at: string | null
}

export interface JobLog {
  id: string
  job_name: string | null
  status: string | null
  message: string | null
  started_at: string | null
  finished_at: string | null
}

export interface DailyReport {
  date?: string
  type?: string
  generated_at?: string
  summary?: {
    top_opportunity?: Opportunity | null
    new_keywords_count?: number
    new_concepts_count?: number
  }
  top_opportunities?: Opportunity[]
  new_keywords?: Keyword[]
  new_concepts?: ProductConcept[]
  top_pain_points?: CommunityInsight[]
}
