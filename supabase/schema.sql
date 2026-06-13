-- =============================================
-- AOIP SCHEMA — Run in Supabase SQL Editor
-- =============================================

-- Niches (Finance, Fitness, Students, etc.)
CREATE TABLE IF NOT EXISTS niches (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  priority    INT DEFAULT 5,
  enabled     BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Seed keywords entered by the developer (up to 1000)
CREATE TABLE IF NOT EXISTS seed_keywords (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  keyword     TEXT NOT NULL,
  niche_id    UUID REFERENCES niches(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE(keyword, niche_id)
);

-- All keywords: seeds + AI-expanded sub-keywords
CREATE TABLE IF NOT EXISTS keywords (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  keyword          TEXT NOT NULL,
  niche_id         UUID REFERENCES niches(id) ON DELETE CASCADE,
  source           TEXT,
  parent_keyword   TEXT,
  demand_score     NUMERIC,
  growth_score     NUMERIC,
  stability_score  NUMERIC,
  seasonal_score   NUMERIC,
  trend_score      NUMERIC,
  last_scored_at   TIMESTAMPTZ,
  created_at       TIMESTAMPTZ DEFAULT now(),
  UNIQUE(keyword, niche_id)
);

-- Competitor apps discovered from Play Store searches
CREATE TABLE IF NOT EXISTS competitors (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  keyword_id        UUID REFERENCES keywords(id) ON DELETE CASCADE,
  app_id            TEXT NOT NULL,
  app_name          TEXT,
  category          TEXT,
  downloads         TEXT,
  rating            NUMERIC,
  review_count      INT,
  last_updated      TEXT,
  has_ads           BOOLEAN,
  has_iap           BOOLEAN,
  subscription      TEXT,
  competition_score NUMERIC,
  saturation_score  NUMERIC,
  fetched_at        TIMESTAMPTZ DEFAULT now(),
  UNIQUE(keyword_id, app_id)
);

-- Pain points and feature requests mined from reviews
CREATE TABLE IF NOT EXISTS review_insights (
  id             UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  competitor_id  UUID REFERENCES competitors(id) ON DELETE CASCADE,
  type           TEXT,
  text           TEXT,
  frequency      INT DEFAULT 1,
  created_at     TIMESTAMPTZ DEFAULT now()
);

-- Raw Reddit posts collected per niche
CREATE TABLE IF NOT EXISTS community_posts (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  niche_id    UUID REFERENCES niches(id) ON DELETE CASCADE,
  source      TEXT,
  subreddit   TEXT,
  title       TEXT,
  content     TEXT,
  upvotes     INT,
  url         TEXT UNIQUE,
  fetched_at  TIMESTAMPTZ DEFAULT now()
);

-- AI-generated insights from community posts
CREATE TABLE IF NOT EXISTS community_insights (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  niche_id    UUID REFERENCES niches(id) ON DELETE CASCADE,
  type        TEXT,
  text        TEXT,
  confidence  NUMERIC,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Scored opportunities (one row per keyword)
CREATE TABLE IF NOT EXISTS opportunities (
  id                   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  keyword_id           UUID REFERENCES keywords(id) ON DELETE CASCADE UNIQUE,
  demand_score         NUMERIC,
  growth_score         NUMERIC,
  pain_point_score     NUMERIC,
  community_score      NUMERIC,
  monetization_score   NUMERIC,
  competition_penalty  NUMERIC,
  complexity_penalty   NUMERIC,
  final_score          NUMERIC,
  ai_reasoning         TEXT,
  scored_at            TIMESTAMPTZ DEFAULT now()
);

-- AI-generated product concepts for top opportunities
CREATE TABLE IF NOT EXISTS product_concepts (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  opportunity_id    UUID REFERENCES opportunities(id) ON DELETE CASCADE UNIQUE,
  app_name          TEXT,
  tagline           TEXT,
  target_audience   TEXT,
  core_features     JSONB,
  premium_features  JSONB,
  monetization      TEXT,
  price_suggestion  TEXT,
  tech_stack        TEXT,
  build_time_weeks  INT,
  full_concept      TEXT,
  generated_at      TIMESTAMPTZ DEFAULT now()
);

-- Scheduler job run log (for dashboard status page)
CREATE TABLE IF NOT EXISTS job_log (
  id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  job_name     TEXT,
  status       TEXT,
  message      TEXT,
  started_at   TIMESTAMPTZ DEFAULT now(),
  finished_at  TIMESTAMPTZ
);
