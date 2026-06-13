# AGENTS.md — App Opportunity Intelligence Platform (AOIP)
# Cursor AI Agent Master Specification

> **READ THIS FILE COMPLETELY BEFORE WRITING A SINGLE LINE OF CODE.**
> This is the single source of truth for all agents. Do not improvise. Do not add features not listed here. Do not skip sections.

---

## AGENT ASSIGNMENTS — WHO OWNS WHAT

| Agent | Name | Owns | Never Touches |
|-------|------|------|---------------|
| Agent 1 | Backend Core | `backend/` (all files) | `frontend/`, `supabase/` |
| Agent 2 | Frontend | `frontend/` (all files) | `backend/`, `supabase/` |
| Agent 3 | DB + Config | `supabase/`, `.env.example` files, `README.md` | `backend/modules/`, `backend/api/`, `frontend/app/` |

**CONFLICT RULE:** If your agent assignment does not include a file, do not open it, do not edit it, do not create it.

---

## PROJECT OVERVIEW

AOIP is a 24/7 autonomous research platform that discovers, scores, and ranks Android app opportunities.

**How it works:**
1. Developer seeds the platform with up to 1,000 keywords via the dashboard
2. AI API expands each keyword into 15 related sub-keywords automatically
3. Scrapers collect Google Trends data, Play Store competitors, Play Store reviews, Reddit posts
4. AI API scores all opportunities using the collected data (no Python math)
5. AI API generates full product concepts for top-ranked opportunities
6. Dashboard displays everything in real time, updating continuously 24/7

**Core design rules that must never be violated:**
- The AI API (Anthropic Claude) does ALL scoring and mathematical analysis — never compute scores in Python
- The AI API does ALL keyword expansion — never scrape Google Search suggestions
- All scraping jobs run sequentially, never in parallel — Render free tier has 512 MB RAM limit
- Always use `time.sleep()` or `asyncio.sleep()` between external API calls
- Supabase is the only database — no SQLite, no files, no in-memory state between requests

---

## SECTION 1 — REPOSITORY STRUCTURE

Create this exact folder and file structure. Every file listed must be created.

```
aoip/
├── AGENTS.md                          ← this file (already exists)
├── README.md                          ← Agent 3 creates this
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── ai_client.py
│   ├── scheduler.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── m1_niche.py
│   │   ├── m2_keyword.py
│   │   ├── m3_trends.py
│   │   ├── m4_playstore.py
│   │   ├── m5_reviews.py
│   │   ├── m6_community.py
│   │   ├── m7_scoring.py
│   │   ├── m8_analyst.py
│   │   └── m9_reports.py
│   └── api/
│       ├── __init__.py
│       ├── niches.py
│       ├── keywords.py
│       ├── opportunities.py
│       ├── competitors.py
│       ├── community.py
│       ├── reports.py
│       └── scheduler_status.py
├── frontend/
│   ├── middleware.ts
│   ├── next.config.ts
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── .env.local.example
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── login/
│   │   │       └── page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── keywords/
│   │   │   │   └── page.tsx
│   │   │   ├── opportunities/
│   │   │   │   └── page.tsx
│   │   │   ├── competitors/
│   │   │   │   └── page.tsx
│   │   │   ├── community/
│   │   │   │   └── page.tsx
│   │   │   ├── niches/
│   │   │   │   └── page.tsx
│   │   │   ├── reports/
│   │   │   │   └── page.tsx
│   │   │   └── scheduler/
│   │   │       └── page.tsx
│   │   ├── globals.css
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                        ← shadcn components go here
│   │   ├── OpportunityCard.tsx
│   │   ├── ScoreBadge.tsx
│   │   ├── TrendSparkline.tsx
│   │   ├── JobStatusChip.tsx
│   │   ├── SeedKeywordImporter.tsx
│   │   └── Sidebar.tsx
│   └── lib/
│       ├── supabase.ts
│       └── utils.ts
└── supabase/
    ├── schema.sql                     ← Agent 3 creates this
    ├── rls_policies.sql               ← Agent 3 creates this
    └── seed_niches.sql                ← Agent 3 creates this
```

---

## SECTION 2 — SUPABASE DATABASE SCHEMA

**Agent 3 writes this into `supabase/schema.sql`.**
**Agent 1 uses these exact table names in all Supabase queries — do not rename anything.**

```sql
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
```

---

## SECTION 3 — ENVIRONMENT VARIABLES

### backend/.env.example

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ANTHROPIC_API_KEY=sk-ant-api03-...
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=AOIP/1.0 by yourusername
BACKEND_SECRET=change_this_to_a_random_string
ENV=production
```

### frontend/.env.local.example

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
NEXT_PUBLIC_BACKEND_URL=https://your-app.onrender.com
```

---

## SECTION 4 — BACKEND: INFRASTRUCTURE FILES

### backend/requirements.txt

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-dotenv==1.0.1
supabase==2.7.4
anthropic==0.34.2
apscheduler==3.10.4
pytrends==4.9.2
google-play-scraper==1.2.6
praw==7.7.1
httpx==0.27.2
```

### backend/config.py

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AOIP/1.0")
BACKEND_SECRET = os.getenv("BACKEND_SECRET", "changeme")
ENV = os.getenv("ENV", "development")

# Safety check — crash early if critical vars are missing
for var_name, var_val in [
    ("SUPABASE_URL", SUPABASE_URL),
    ("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY),
    ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
]:
    if not var_val:
        raise EnvironmentError(f"Missing required environment variable: {var_name}")
```

### backend/db.py

```python
# db.py
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

_client: Client = None

def get_db() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client
```

### backend/ai_client.py

```python
# ai_client.py
import anthropic
import json
import asyncio
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

async def ai_bulk(prompt: str) -> dict:
    """
    Fast and cheap. Use for: keyword expansion, trend scoring, opportunity scoring.
    Model: claude-haiku-4-5-20251001
    Always returns parsed JSON dict.
    """
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=(
                "You are a JSON-only responder. "
                "Always return valid JSON. "
                "Never include markdown code fences, preamble, or explanation. "
                "Your entire response must be parseable by json.loads()."
            ),
            messages=[{"role": "user", "content": prompt}]
        )
    )
    raw = response.content[0].text.strip()
    # Strip accidental markdown fences if model slips
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def ai_analyze(prompt: str) -> dict:
    """
    Detailed analysis. Use for: product concepts, review mining.
    Model: claude-sonnet-4-6
    Always returns parsed JSON dict.
    """
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=(
                "You are a JSON-only responder. "
                "Always return valid JSON. "
                "Never include markdown code fences, preamble, or explanation. "
                "Your entire response must be parseable by json.loads()."
            ),
            messages=[{"role": "user", "content": prompt}]
        )
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
```

### backend/main.py

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from scheduler import start_scheduler
from api import niches, keywords, opportunities, competitors, community, reports, scheduler_status

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield

app = FastAPI(title="AOIP — App Opportunity Intelligence Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(niches.router, prefix="/api/niches", tags=["niches"])
app.include_router(keywords.router, prefix="/api/keywords", tags=["keywords"])
app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["competitors"])
app.include_router(community.router, prefix="/api/community", tags=["community"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(scheduler_status.router, prefix="/api/scheduler", tags=["scheduler"])
```

### backend/scheduler.py

```python
# scheduler.py
import threading
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from db import get_db

logger = logging.getLogger(__name__)
_job_lock = threading.Lock()


def log_job(job_name: str, status: str, message: str = "", started_at: datetime = None, finished_at: datetime = None):
    """Write a job run entry to the job_log table."""
    try:
        row = {
            "job_name": job_name,
            "status": status,
            "message": message[:500] if message else "",
        }
        if started_at:
            row["started_at"] = started_at.isoformat()
        if finished_at:
            row["finished_at"] = finished_at.isoformat()
        get_db().table("job_log").insert(row).execute()
    except Exception as e:
        logger.error(f"Failed to log job: {e}")


def run_job(job_name: str, coro_factory):
    """
    Acquires the global lock and runs a coroutine.
    Only one job runs at a time — no parallel scraping.
    """
    if not _job_lock.acquire(blocking=False):
        logger.info(f"Skipping {job_name} — another job is running")
        return
    started = datetime.utcnow()
    log_job(job_name, "running", "started", started_at=started)
    try:
        asyncio.run(coro_factory())
        finished = datetime.utcnow()
        log_job(job_name, "success", "completed", started_at=started, finished_at=finished)
    except Exception as e:
        finished = datetime.utcnow()
        logger.error(f"Job {job_name} failed: {e}")
        log_job(job_name, "error", str(e), started_at=started, finished_at=finished)
    finally:
        _job_lock.release()


def start_scheduler():
    from modules.m2_keyword import run as m2_run
    from modules.m3_trends import run as m3_run
    from modules.m4_playstore import run as m4_run
    from modules.m5_reviews import run as m5_run
    from modules.m6_community import run as m6_run
    from modules.m7_scoring import run as m7_run
    from modules.m8_analyst import run as m8_run
    from modules.m9_reports import generate_daily

    s = BackgroundScheduler(timezone="Asia/Kolkata")

    # Every 6 hours: expand keywords and score trends
    s.add_job(
        lambda: run_job("keyword_expansion", m2_run),
        IntervalTrigger(hours=6),
        id="keyword_expansion",
        next_run_time=datetime.now()  # Run immediately on startup
    )

    # Every 6 hours offset by 1h: Google Trends scoring
    s.add_job(
        lambda: run_job("trend_analysis", m3_run),
        IntervalTrigger(hours=6),
        id="trend_analysis"
    )

    # Every 4 hours: Play Store competitor data
    s.add_job(
        lambda: run_job("playstore_intel", m4_run),
        IntervalTrigger(hours=4),
        id="playstore_intel"
    )

    # Every 8 hours: Mine reviews from competitors
    s.add_job(
        lambda: run_job("review_mining", m5_run),
        IntervalTrigger(hours=8),
        id="review_mining"
    )

    # Every 8 hours: Reddit community research
    s.add_job(
        lambda: run_job("community_research", m6_run),
        IntervalTrigger(hours=8),
        id="community_research"
    )

    # Every 12 hours: Rescore all opportunities
    s.add_job(
        lambda: run_job("opportunity_scoring", m7_run),
        IntervalTrigger(hours=12),
        id="opportunity_scoring"
    )

    # Daily at 2am IST: Generate product concepts for top 20
    s.add_job(
        lambda: run_job("product_concepts", m8_run),
        CronTrigger(hour=2, minute=0, timezone="Asia/Kolkata"),
        id="product_concepts"
    )

    # Daily at 3am IST: Generate daily report
    s.add_job(
        lambda: run_job("daily_report", generate_daily),
        CronTrigger(hour=3, minute=0, timezone="Asia/Kolkata"),
        id="daily_report"
    )

    s.start()
    logger.info("APScheduler started. All jobs registered.")
```

---

## SECTION 5 — BACKEND: MODULE FILES

**All files go into `backend/modules/`.**

### backend/modules/m1_niche.py

```python
# modules/m1_niche.py
from db import get_db


async def get_active_niches() -> list[dict]:
    """Returns all enabled niches, highest priority first."""
    res = (
        get_db()
        .table("niches")
        .select("*")
        .eq("enabled", True)
        .order("priority", desc=True)
        .execute()
    )
    return res.data


async def get_seed_keywords(niche_id: str) -> list[str]:
    """Returns all seed keyword strings for a given niche."""
    res = (
        get_db()
        .table("seed_keywords")
        .select("keyword")
        .eq("niche_id", niche_id)
        .execute()
    )
    return [r["keyword"] for r in res.data]
```

### backend/modules/m2_keyword.py

```python
# modules/m2_keyword.py
# PURPOSE: Expand each seed keyword into 15 related sub-keywords using the AI API.
# RUNS: Every 6 hours via scheduler.
# OUTPUT: Writes new rows to the `keywords` table.

import asyncio
from db import get_db
from ai_client import ai_bulk
from modules.m1_niche import get_active_niches, get_seed_keywords

EXPAND_PROMPT = """
You are a mobile app market research expert focused on the Indian Android market.

Given the seed keyword "{keyword}" for the "{niche}" niche, generate exactly 15 related
search queries that Indian Android users would type into Google Play Store or Google Search
to find utility apps and tools.

Rules:
- Focus on utility apps, calculators, trackers, planners, managers
- Include both English and Hinglish variations where relevant
- Include regional variations (e.g. "GST calculator", "EMI calculator India")
- Do NOT include brand names or existing app names
- Each keyword should be 2-5 words

Return ONLY this JSON, nothing else:
{{"keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8", "kw9", "kw10", "kw11", "kw12", "kw13", "kw14", "kw15"]}}
"""


async def run():
    db = get_db()
    niches = await get_active_niches()

    for niche in niches:
        seeds = await get_seed_keywords(niche["id"])

        for seed in seeds:
            await asyncio.sleep(2)  # Rate limit buffer between AI calls

            try:
                result = await ai_bulk(
                    EXPAND_PROMPT.format(keyword=seed, niche=niche["name"])
                )
                new_keywords = result.get("keywords", [])
                all_keywords = list(set([seed.lower().strip()] + [k.lower().strip() for k in new_keywords]))

                for kw in all_keywords:
                    if not kw:
                        continue
                    db.table("keywords").upsert(
                        {
                            "keyword": kw,
                            "niche_id": niche["id"],
                            "source": "seed" if kw == seed.lower().strip() else "ai_expand",
                            "parent_keyword": seed.lower().strip(),
                        },
                        on_conflict="keyword,niche_id",
                    ).execute()

            except Exception as e:
                print(f"[m2] Error expanding keyword '{seed}': {e}")
                continue
```

### backend/modules/m3_trends.py

```python
# modules/m3_trends.py
# PURPOSE: Fetch Google Trends data per keyword and score it via AI.
# RUNS: Every 6 hours via scheduler.
# OUTPUT: Updates demand_score, growth_score, stability_score, seasonal_score, trend_score on `keywords` table.

import asyncio
import time
from pytrends.request import TrendReq
from db import get_db
from ai_client import ai_bulk

SCORE_PROMPT = """
You are analysing Google Trends data for a mobile app market researcher.

Keyword: "{keyword}"
Country: India
Timeframe: Last 12 months (weekly data points)
Interest array (0-100, where 100 = peak popularity in period):
{data}

Based on this data, compute these scores (all must be integers 0-100):

- demand_score: The average level of search interest. High = people consistently search for this.
- growth_score: The trend momentum. High = interest is rising sharply. Low = declining or flat.
- stability_score: How consistent the interest is. High = steady searches year-round. Low = very volatile.
- seasonal_score: How seasonal this keyword is. High = spikes at certain times. Low = flat all year.
- trend_score: Your overall weighted score combining all of the above. Formula hint: (demand*0.35 + growth*0.35 + stability*0.20 - seasonal*0.10). Round to integer.

Return ONLY this JSON, nothing else:
{{"demand_score": 0, "growth_score": 0, "stability_score": 0, "seasonal_score": 0, "trend_score": 0}}
"""


async def run():
    db = get_db()

    # Get keywords not scored in last 24 hours (or never scored)
    res = (
        db.table("keywords")
        .select("id, keyword")
        .or_(
            "last_scored_at.is.null,"
            "last_scored_at.lt." + "now()-interval '24 hours'"
        )
        .limit(80)
        .execute()
    )

    if not res.data:
        print("[m3] No keywords need trend scoring.")
        return

    pytrends = TrendReq(hl="en-IN", tz=330, timeout=(10, 25))

    for kw in res.data:
        time.sleep(12)  # pytrends rate limit — do not reduce this
        try:
            pytrends.build_payload(
                [kw["keyword"]], timeframe="today 12-m", geo="IN"
            )
            df = pytrends.interest_over_time()

            if df.empty or kw["keyword"] not in df.columns:
                print(f"[m3] No trends data for: {kw['keyword']}")
                continue

            data_points = df[kw["keyword"]].tolist()

            scores = await ai_bulk(
                SCORE_PROMPT.format(keyword=kw["keyword"], data=data_points)
            )

            db.table("keywords").update(
                {
                    "demand_score": scores.get("demand_score"),
                    "growth_score": scores.get("growth_score"),
                    "stability_score": scores.get("stability_score"),
                    "seasonal_score": scores.get("seasonal_score"),
                    "trend_score": scores.get("trend_score"),
                    "last_scored_at": "now()",
                }
            ).eq("id", kw["id"]).execute()

            print(f"[m3] Scored: {kw['keyword']} → trend_score={scores.get('trend_score')}")

        except Exception as e:
            print(f"[m3] Error for '{kw['keyword']}': {e}")
            continue
```

### backend/modules/m4_playstore.py

```python
# modules/m4_playstore.py
# PURPOSE: Search Play Store for each keyword and collect top 10 competitor apps.
# RUNS: Every 4 hours via scheduler.
# OUTPUT: Writes rows to `competitors` table. Updates competition_score and saturation_score.

import asyncio
from google_play_scraper import search
from db import get_db
from ai_client import ai_bulk

COMPETE_PROMPT = """
You are analysing the Android Play Store competitive landscape for a market researcher.

Search keyword: "{keyword}"
Country: India

Here are the top apps found for this keyword:
{apps_summary}

Based on this data, score the competitive landscape:

- competition_score (0-100): How competitive is this market?
  100 = huge established players with millions of downloads and 4.5+ ratings.
  0 = very few apps, low downloads, poor ratings — easy to enter.

- saturation_score (0-100): How saturated is this market?
  100 = market is flooded, very hard to get visibility.
  0 = few apps, lots of room for a new entrant.

Consider: number of quality competitors, download concentration, rating quality, update recency.

Return ONLY this JSON, nothing else:
{{"competition_score": 0, "saturation_score": 0, "reasoning": "brief explanation under 20 words"}}
"""


async def run():
    db = get_db()

    # Process keywords that have trend scores (prioritise validated keywords)
    res = (
        db.table("keywords")
        .select("id, keyword, niche_id")
        .not_.is_("trend_score", "null")
        .order("trend_score", desc=True)
        .limit(60)
        .execute()
    )

    if not res.data:
        print("[m4] No scored keywords to process.")
        return

    for kw in res.data:
        await asyncio.sleep(3)
        try:
            results = search(
                kw["keyword"], lang="en", country="in", n_hits=10
            )
            if not results:
                continue

            apps_summary = []
            for r in results:
                apps_summary.append({
                    "name": r.get("title", ""),
                    "downloads": r.get("installs", "unknown"),
                    "rating": r.get("score", 0),
                    "review_count": r.get("ratings", 0),
                    "last_updated": r.get("updated", ""),
                })
                # Upsert competitor record
                db.table("competitors").upsert(
                    {
                        "keyword_id": kw["id"],
                        "app_id": r.get("appId", ""),
                        "app_name": r.get("title", ""),
                        "category": r.get("genre", ""),
                        "downloads": r.get("installs", ""),
                        "rating": r.get("score"),
                        "review_count": r.get("ratings"),
                        "last_updated": str(r.get("updated", "")),
                        "has_ads": r.get("containsAds", False),
                        "has_iap": r.get("offersIAP", False),
                    },
                    on_conflict="keyword_id,app_id",
                ).execute()

            # Get AI to score competition level
            scores = await ai_bulk(
                COMPETE_PROMPT.format(
                    keyword=kw["keyword"],
                    apps_summary=str(apps_summary)
                )
            )

            # Update competition scores on all competitor rows for this keyword
            db.table("competitors").update(
                {
                    "competition_score": scores.get("competition_score"),
                    "saturation_score": scores.get("saturation_score"),
                }
            ).eq("keyword_id", kw["id"]).execute()

            print(f"[m4] {kw['keyword']} — {len(results)} apps, competition={scores.get('competition_score')}")

        except Exception as e:
            print(f"[m4] Error for '{kw['keyword']}': {e}")
            continue
```

### backend/modules/m5_reviews.py

```python
# modules/m5_reviews.py
# PURPOSE: Mine 1-3 star reviews from competitor apps and extract pain points via AI.
# RUNS: Every 8 hours via scheduler.
# OUTPUT: Writes rows to `review_insights` table (type: complaint or feature_request).

import asyncio
from google_play_scraper import reviews, Sort
from db import get_db
from ai_client import ai_analyze

REVIEW_PROMPT = """
You are a product research analyst extracting user pain points from Android app reviews.

App name: "{app_name}"

Here are the 1-3 star reviews (format: [rating★] review text):
{reviews_text}

Your job:
1. Identify the most common user COMPLAINTS (bugs, missing features, bad UX, crashes, too many ads)
2. Identify FEATURE REQUESTS (things users are asking for)
3. Merge near-duplicate items together
4. Estimate frequency (how many of the reviews mention this issue, 1-10 scale)

Return ONLY this JSON, nothing else:
{{
  "complaints": [
    {{"text": "description of complaint", "frequency": 7}},
    {{"text": "another complaint", "frequency": 3}}
  ],
  "feature_requests": [
    {{"text": "requested feature", "frequency": 5}}
  ]
}}

Maximum 10 complaints, maximum 10 feature requests. Quality over quantity.
"""


async def run():
    db = get_db()

    # Get competitors not yet mined (no review insights exist for them)
    all_comps = db.table("competitors").select("id, app_id, app_name").limit(40).execute().data
    mined_ids = set(
        r["competitor_id"]
        for r in db.table("review_insights").select("competitor_id").execute().data
    )
    to_mine = [c for c in all_comps if c["id"] not in mined_ids][:25]

    if not to_mine:
        print("[m5] All competitors already mined.")
        return

    for comp in to_mine:
        await asyncio.sleep(5)
        try:
            result, _ = reviews(
                comp["app_id"],
                lang="en",
                country="in",
                count=60,
                sort=Sort.NEWEST,
            )

            low_star = [r for r in result if r.get("score", 5) <= 3]
            if not low_star:
                print(f"[m5] No low-star reviews for: {comp['app_name']}")
                continue

            reviews_text = "\n".join([
                f"[{r['score']}★] {r['content'][:200]}"
                for r in low_star[:40]
            ])

            insights = await ai_analyze(
                REVIEW_PROMPT.format(
                    app_name=comp["app_name"],
                    reviews_text=reviews_text
                )
            )

            for item in insights.get("complaints", []):
                db.table("review_insights").insert({
                    "competitor_id": comp["id"],
                    "type": "complaint",
                    "text": item["text"],
                    "frequency": item.get("frequency", 1),
                }).execute()

            for item in insights.get("feature_requests", []):
                db.table("review_insights").insert({
                    "competitor_id": comp["id"],
                    "type": "feature_request",
                    "text": item["text"],
                    "frequency": item.get("frequency", 1),
                }).execute()

            print(f"[m5] Mined {comp['app_name']}: {len(insights.get('complaints',[]))} complaints, {len(insights.get('feature_requests',[]))} requests")

        except Exception as e:
            print(f"[m5] Error for '{comp['app_name']}': {e}")
            continue
```

### backend/modules/m6_community.py

```python
# modules/m6_community.py
# PURPOSE: Scrape Reddit for niche-relevant posts and extract insights via AI.
# RUNS: Every 8 hours via scheduler.
# OUTPUT: Writes to community_posts and community_insights tables.

import asyncio
import praw
from db import get_db
from ai_client import ai_analyze
from modules.m1_niche import get_active_niches
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

# Subreddit mapping per niche — add more as needed
NICHE_SUBREDDITS = {
    "Finance":      ["personalfinance", "IndiaInvestments", "india"],
    "Productivity": ["productivity", "androidapps", "selfimprovement"],
    "Students":     ["college", "india", "indian_academia", "learnprogramming"],
    "Fitness":      ["fitness", "india", "IndianFitness", "bodyweightfitness"],
    "Health":       ["Health", "india", "AskDocs"],
    "AI":           ["artificial", "MachineLearning", "ChatGPT"],
    "Education":    ["education", "india", "learnprogramming"],
    "Construction": ["Construction", "civilengineering", "india"],
    "Agriculture":  ["farming", "india", "agriculture"],
    "Real Estate":  ["realestateinvesting", "india", "RealEstate"],
    "Business":     ["smallbusiness", "Entrepreneur", "india"],
}

INSIGHT_PROMPT = """
You are a mobile app product researcher analysing Reddit posts for the "{niche}" market.

Here are Reddit posts from users discussing apps, tools, and problems in this space:
{posts_text}

Extract insights that would help an Android app developer understand what to build.

Return ONLY this JSON, nothing else:
{{
  "pain_points": [
    {{"text": "specific problem users face", "confidence": 0.9}}
  ],
  "feature_requests": [
    {{"text": "something users wish existed", "confidence": 0.8}}
  ],
  "emerging_trends": [
    {{"text": "a growing topic or behaviour", "confidence": 0.7}}
  ]
}}

Maximum 8 items per category. Confidence is 0.0-1.0. Only include items with confidence > 0.5.
"""


async def run():
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    db = get_db()
    niches = await get_active_niches()

    for niche in niches:
        subreddits = NICHE_SUBREDDITS.get(niche["name"], ["androidapps", "india"])
        all_posts = []

        for sub in subreddits:
            await asyncio.sleep(2)
            try:
                for post in reddit.subreddit(sub).search(
                    niche["name"] + " app", limit=15, sort="top", time_filter="month"
                ):
                    all_posts.append({
                        "title": post.title,
                        "text": post.selftext[:300],
                        "upvotes": post.score,
                        "url": post.url,
                        "subreddit": sub,
                    })
                    # Store raw post
                    try:
                        db.table("community_posts").upsert(
                            {
                                "niche_id": niche["id"],
                                "source": "reddit",
                                "subreddit": sub,
                                "title": post.title[:500],
                                "content": post.selftext[:500],
                                "upvotes": post.score,
                                "url": post.url,
                            },
                            on_conflict="url",
                        ).execute()
                    except Exception:
                        pass  # Duplicate URL — ignore

            except Exception as e:
                print(f"[m6] Reddit error on r/{sub}: {e}")
                continue

        if not all_posts:
            print(f"[m6] No posts found for niche: {niche['name']}")
            continue

        # Sort by upvotes, take top 30
        all_posts.sort(key=lambda x: x["upvotes"], reverse=True)
        posts_text = "\n".join([
            f"[{p['upvotes']}↑ r/{p['subreddit']}] {p['title']}: {p['text']}"
            for p in all_posts[:30]
        ])

        try:
            insights = await ai_analyze(
                INSIGHT_PROMPT.format(niche=niche["name"], posts_text=posts_text)
            )

            for category, itype in [
                ("pain_points", "pain_point"),
                ("feature_requests", "feature_request"),
                ("emerging_trends", "trend"),
            ]:
                for item in insights.get(category, []):
                    db.table("community_insights").insert({
                        "niche_id": niche["id"],
                        "type": itype,
                        "text": item["text"],
                        "confidence": item.get("confidence", 0.5),
                    }).execute()

            print(f"[m6] {niche['name']}: {len(all_posts)} posts → insights stored")

        except Exception as e:
            print(f"[m6] AI analysis error for {niche['name']}: {e}")
```

### backend/modules/m7_scoring.py

```python
# modules/m7_scoring.py
# PURPOSE: Score every keyword as an app opportunity using the AI API.
# RUNS: Every 12 hours via scheduler.
# OUTPUT: Upserts rows to `opportunities` table with full score breakdown.

import asyncio
from db import get_db
from ai_client import ai_bulk

SCORE_PROMPT = """
You are scoring an Android app market opportunity for an indie developer targeting India.

KEYWORD: "{keyword}"
NICHE: "{niche}"

AVAILABLE SIGNALS:
- Google Trends demand score (0-100): {demand}
- Google Trends growth score (0-100): {growth}
- Google Trends stability score (0-100): {stability}
- Number of competitor apps found: {num_competitors}
- Average competitor rating: {avg_rating}/5
- Total review insights collected (pain points + requests): {insight_count}
- Community posts mentioning this niche: {community_count}

SCORING INSTRUCTIONS:
Score each dimension 0-100 based on the signals above.
Then compute the final score using this formula:
  final_score = demand_score + growth_score + pain_point_score + community_score + monetization_score
                - competition_penalty - complexity_penalty

Definitions:
- demand_score: Based on trends demand. High demand = high score.
- growth_score: Based on trends growth. Rising fast = high score.
- pain_point_score: Based on insight_count. Many pain points = high opportunity.
- community_score: Based on community_count. High community discussion = high score.
- monetization_score: Estimate how easily this app type can be monetised (subscriptions, one-time, ads). 0-100.
- competition_penalty: Based on num_competitors and avg_rating. Many good competitors = high penalty.
- complexity_penalty: Estimate how complex this app would be to build as an indie dev. Simple utility = low penalty.

Return ONLY this JSON, nothing else:
{{
  "demand_score": 0,
  "growth_score": 0,
  "pain_point_score": 0,
  "community_score": 0,
  "monetization_score": 0,
  "competition_penalty": 0,
  "complexity_penalty": 0,
  "final_score": 0,
  "ai_reasoning": "One sentence explaining why this is or is not a good opportunity."
}}
"""


async def run():
    db = get_db()

    # Get keywords with trend scores
    keywords_res = (
        db.table("keywords")
        .select("id, keyword, niche_id, demand_score, growth_score, stability_score")
        .not_.is_("trend_score", "null")
        .order("trend_score", desc=True)
        .limit(200)
        .execute()
    )

    if not keywords_res.data:
        print("[m7] No scored keywords to process.")
        return

    for kw in keywords_res.data:
        await asyncio.sleep(1)
        try:
            # Gather context
            comps = db.table("competitors").select("rating").eq("keyword_id", kw["id"]).execute().data
            insights = db.table("review_insights").select("id", count="exact").execute()
            community = db.table("community_posts").select("id", count="exact").eq("niche_id", kw["niche_id"]).execute()
            niche = db.table("niches").select("name").eq("id", kw["niche_id"]).single().execute().data

            avg_rating = (
                sum(c["rating"] or 0 for c in comps) / len(comps)
                if comps else 0
            )

            score = await ai_bulk(
                SCORE_PROMPT.format(
                    keyword=kw["keyword"],
                    niche=niche["name"],
                    demand=kw.get("demand_score", 0) or 0,
                    growth=kw.get("growth_score", 0) or 0,
                    stability=kw.get("stability_score", 0) or 0,
                    num_competitors=len(comps),
                    avg_rating=round(avg_rating, 1),
                    insight_count=getattr(insights, "count", 0) or 0,
                    community_count=getattr(community, "count", 0) or 0,
                )
            )

            db.table("opportunities").upsert(
                {"keyword_id": kw["id"], **score},
                on_conflict="keyword_id",
            ).execute()

            print(f"[m7] Scored '{kw['keyword']}' → final_score={score.get('final_score')}")

        except Exception as e:
            print(f"[m7] Error scoring '{kw['keyword']}': {e}")
            continue
```

### backend/modules/m8_analyst.py

```python
# modules/m8_analyst.py
# PURPOSE: Generate full product concepts for top-ranked opportunities using AI.
# RUNS: Daily at 2am IST via scheduler.
# OUTPUT: Inserts rows into `product_concepts` table.

import asyncio
from db import get_db
from ai_client import ai_analyze

CONCEPT_PROMPT = """
You are a senior Android app product strategist specialising in the Indian market.
You help indie developers build profitable utility apps.

Generate a complete product concept for this app opportunity:

KEYWORD: "{keyword}"
NICHE: "{niche}"
OPPORTUNITY SCORE: {score}/500

TOP USER COMPLAINTS FROM EXISTING APPS:
{complaints}

TOP FEATURE REQUESTS FROM USERS:
{features}

COMMUNITY PAIN POINTS (from Reddit):
{community}

Your concept must directly address the complaints and feature requests above.
Design for Indian Android users — consider: offline-first, low data usage, Hindi/regional language options, India-specific features (GST, UPI, etc. where relevant), ₹ pricing.

Return ONLY this JSON, nothing else:
{{
  "app_name": "Catchy name for the app",
  "tagline": "One line value proposition under 10 words",
  "target_audience": "Specific description of who uses this app",
  "core_features": [
    "Feature 1 — description",
    "Feature 2 — description",
    "Feature 3 — description",
    "Feature 4 — description",
    "Feature 5 — description"
  ],
  "premium_features": [
    "Premium feature 1",
    "Premium feature 2",
    "Premium feature 3"
  ],
  "monetization": "Detailed monetization strategy",
  "price_suggestion": "e.g. Free with ads, ₹299/year premium",
  "tech_stack": "e.g. Flutter + Firebase + Supabase",
  "build_time_weeks": 6,
  "full_concept": "A 150-200 word detailed product description covering the problem, solution, differentiator, and go-to-market angle."
}}
"""


async def run():
    db = get_db()

    # Get top opportunities that don't have a concept yet
    all_opps = (
        db.table("opportunities")
        .select("id, final_score, keyword_id")
        .order("final_score", desc=True)
        .limit(50)
        .execute()
        .data
    )

    existing_concept_ids = set(
        r["opportunity_id"]
        for r in db.table("product_concepts").select("opportunity_id").execute().data
    )

    to_process = [o for o in all_opps if o["id"] not in existing_concept_ids][:20]

    if not to_process:
        print("[m8] All top opportunities already have concepts.")
        return

    for opp in to_process:
        await asyncio.sleep(3)
        try:
            kw = (
                db.table("keywords")
                .select("keyword, niche_id")
                .eq("id", opp["keyword_id"])
                .single()
                .execute()
                .data
            )
            niche = (
                db.table("niches")
                .select("name")
                .eq("id", kw["niche_id"])
                .single()
                .execute()
                .data
            )
            # Get competitor IDs for this keyword
            comp_ids = [
                c["id"]
                for c in db.table("competitors")
                .select("id")
                .eq("keyword_id", opp["keyword_id"])
                .execute()
                .data
            ]
            # Gather review insights
            insights = (
                db.table("review_insights")
                .select("type, text, frequency")
                .in_("competitor_id", comp_ids)
                .order("frequency", desc=True)
                .limit(30)
                .execute()
                .data
            )
            # Gather community pain points
            community = (
                db.table("community_insights")
                .select("type, text")
                .eq("niche_id", kw["niche_id"])
                .eq("type", "pain_point")
                .limit(15)
                .execute()
                .data
            )

            complaints = [i["text"] for i in insights if i["type"] == "complaint"][:10]
            features = [i["text"] for i in insights if i["type"] == "feature_request"][:10]
            comm_pain = [i["text"] for i in community][:8]

            concept = await ai_analyze(
                CONCEPT_PROMPT.format(
                    keyword=kw["keyword"],
                    niche=niche["name"],
                    score=opp.get("final_score", 0),
                    complaints="\n".join(f"- {c}" for c in complaints) or "No data yet",
                    features="\n".join(f"- {f}" for f in features) or "No data yet",
                    community="\n".join(f"- {c}" for c in comm_pain) or "No data yet",
                )
            )

            db.table("product_concepts").insert(
                {"opportunity_id": opp["id"], **concept}
            ).execute()

            print(f"[m8] Concept generated: {concept.get('app_name')} for '{kw['keyword']}'")

        except Exception as e:
            print(f"[m8] Error for opportunity {opp['id']}: {e}")
            continue
```

### backend/modules/m9_reports.py

```python
# modules/m9_reports.py
# PURPOSE: Generate daily summary reports and store as JSON in Supabase Storage.
# RUNS: Daily at 3am IST via scheduler.

import json
from datetime import datetime, timedelta
from db import get_db


async def generate_daily():
    db = get_db()
    today = datetime.utcnow().date().isoformat()
    yesterday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()

    # Top 15 opportunities
    top_opps = (
        db.table("opportunities")
        .select("final_score, ai_reasoning, keyword_id, keywords(keyword, niche_id, niches(name))")
        .order("final_score", desc=True)
        .limit(15)
        .execute()
        .data
    )

    # New keywords discovered in last 24h
    new_kws = (
        db.table("keywords")
        .select("keyword, source, niches(name)")
        .gte("created_at", yesterday)
        .limit(50)
        .execute()
        .data
    )

    # New product concepts generated
    new_concepts = (
        db.table("product_concepts")
        .select("app_name, tagline, price_suggestion, build_time_weeks")
        .gte("generated_at", yesterday)
        .execute()
        .data
    )

    # Top community pain points
    top_pain = (
        db.table("community_insights")
        .select("text, confidence, niches(name)")
        .eq("type", "pain_point")
        .order("confidence", desc=True)
        .limit(10)
        .execute()
        .data
    )

    report = {
        "date": today,
        "type": "daily",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "top_opportunity": top_opps[0] if top_opps else None,
            "new_keywords_count": len(new_kws),
            "new_concepts_count": len(new_concepts),
        },
        "top_opportunities": top_opps,
        "new_keywords": new_kws,
        "new_concepts": new_concepts,
        "top_pain_points": top_pain,
    }

    # Store in Supabase Storage bucket named 'reports'
    try:
        db.storage.from_("reports").upload(
            f"daily/{today}.json",
            json.dumps(report, indent=2, default=str).encode(),
            {"content-type": "application/json", "upsert": "true"},
        )
        print(f"[m9] Daily report stored: daily/{today}.json")
    except Exception as e:
        print(f"[m9] Storage error: {e}")
        # Fallback: store in job_log table
        db.table("job_log").insert({
            "job_name": "daily_report_content",
            "status": "success",
            "message": json.dumps(report, default=str)[:500],
        }).execute()
```

---

## SECTION 6 — BACKEND: API ROUTE FILES

**All files go into `backend/api/`.**

### backend/api/niches.py

```python
# api/niches.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from db import get_db

router = APIRouter()


class NicheCreate(BaseModel):
    name: str
    priority: Optional[int] = 5


class NicheUpdate(BaseModel):
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class SeedKeywordsPayload(BaseModel):
    keywords: list[str]  # Max 1000 lines from textarea


@router.get("/")
def list_niches():
    res = get_db().table("niches").select("*, seed_keywords(count)").order("priority", desc=True).execute()
    return res.data


@router.post("/")
def create_niche(body: NicheCreate):
    res = get_db().table("niches").insert({"name": body.name, "priority": body.priority}).execute()
    return res.data[0]


@router.patch("/{niche_id}")
def update_niche(niche_id: str, body: NicheUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    res = get_db().table("niches").update(updates).eq("id", niche_id).execute()
    return res.data[0]


@router.post("/{niche_id}/seeds")
def add_seed_keywords(niche_id: str, body: SeedKeywordsPayload):
    keywords = [k.strip().lower() for k in body.keywords if k.strip()][:1000]
    if not keywords:
        raise HTTPException(status_code=400, detail="No valid keywords provided")
    rows = [{"keyword": kw, "niche_id": niche_id} for kw in keywords]
    # Insert in batches of 100 to avoid payload limits
    inserted = 0
    for i in range(0, len(rows), 100):
        get_db().table("seed_keywords").upsert(rows[i:i+100], on_conflict="keyword,niche_id").execute()
        inserted += len(rows[i:i+100])
    return {"inserted": inserted}
```

### backend/api/keywords.py

```python
# api/keywords.py
from fastapi import APIRouter, Query
from typing import Optional
from db import get_db

router = APIRouter()


@router.get("/")
def list_keywords(
    niche_id: Optional[str] = None,
    source: Optional[str] = None,
    min_trend_score: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
):
    q = get_db().table("keywords").select("*, niches(name)")
    if niche_id:
        q = q.eq("niche_id", niche_id)
    if source:
        q = q.eq("source", source)
    if min_trend_score is not None:
        q = q.gte("trend_score", min_trend_score)
    if search:
        q = q.ilike("keyword", f"%{search}%")
    res = q.order("trend_score", desc=True, nullsfirst=False).range(offset, offset + limit - 1).execute()
    return res.data


@router.get("/{keyword_id}/competitors")
def get_competitors(keyword_id: str):
    res = get_db().table("competitors").select("*").eq("keyword_id", keyword_id).order("rating", desc=True).execute()
    return res.data
```

### backend/api/opportunities.py

```python
# api/opportunities.py
from fastapi import APIRouter, Query
from typing import Optional
from db import get_db

router = APIRouter()


@router.get("/")
def list_opportunities(
    niche_id: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    q = (
        get_db()
        .table("opportunities")
        .select("*, keywords(keyword, niche_id, niches(name)), product_concepts(app_name, tagline, price_suggestion, build_time_weeks)")
    )
    if min_score is not None:
        q = q.gte("final_score", min_score)
    res = q.order("final_score", desc=True).range(offset, offset + limit - 1).execute()
    # Filter by niche in Python (join filter)
    data = res.data
    if niche_id:
        data = [o for o in data if o.get("keywords", {}).get("niche_id") == niche_id]
    return data


@router.get("/{opportunity_id}")
def get_opportunity(opportunity_id: str):
    res = (
        get_db()
        .table("opportunities")
        .select("*, keywords(keyword, niches(name)), product_concepts(*)")
        .eq("id", opportunity_id)
        .single()
        .execute()
    )
    return res.data
```

### backend/api/competitors.py

```python
# api/competitors.py
from fastapi import APIRouter
from db import get_db

router = APIRouter()


@router.get("/{competitor_id}/insights")
def get_insights(competitor_id: str):
    res = (
        get_db()
        .table("review_insights")
        .select("*")
        .eq("competitor_id", competitor_id)
        .order("frequency", desc=True)
        .execute()
    )
    return res.data
```

### backend/api/community.py

```python
# api/community.py
from fastapi import APIRouter, Query
from typing import Optional
from db import get_db

router = APIRouter()


@router.get("/insights")
def get_insights(
    niche_id: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    q = get_db().table("community_insights").select("*, niches(name)")
    if niche_id:
        q = q.eq("niche_id", niche_id)
    if type:
        q = q.eq("type", type)
    res = q.order("confidence", desc=True).limit(limit).execute()
    return res.data


@router.get("/posts")
def get_posts(niche_id: Optional[str] = None, limit: int = 50):
    q = get_db().table("community_posts").select("*")
    if niche_id:
        q = q.eq("niche_id", niche_id)
    res = q.order("upvotes", desc=True).limit(limit).execute()
    return res.data
```

### backend/api/reports.py

```python
# api/reports.py
from fastapi import APIRouter
from db import get_db
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/daily")
def get_daily_report():
    today = datetime.utcnow().date().isoformat()
    try:
        data = get_db().storage.from_("reports").download(f"daily/{today}.json")
        import json
        return json.loads(data)
    except Exception:
        # Fallback: build report on the fly from DB
        return _build_live_report()


def _build_live_report():
    db = get_db()
    top_opps = (
        db.table("opportunities")
        .select("final_score, keyword_id, keywords(keyword, niches(name))")
        .order("final_score", desc=True)
        .limit(10)
        .execute()
        .data
    )
    return {"type": "live", "generated_at": datetime.utcnow().isoformat(), "top_opportunities": top_opps}
```

### backend/api/scheduler_status.py

```python
# api/scheduler_status.py
from fastapi import APIRouter
from db import get_db

router = APIRouter()


@router.get("/status")
def get_status():
    res = (
        get_db()
        .table("job_log")
        .select("*")
        .order("started_at", desc=True)
        .limit(20)
        .execute()
    )
    return res.data
```

---

## SECTION 7 — FRONTEND SETUP

**Agent 2: Before writing any page files, run this command inside the `frontend/` directory:**

```bash
npx create-next-app@14 . --typescript --tailwind --app --no-src-dir --eslint
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card badge table tabs dialog select input label
```

### frontend/lib/supabase.ts

```typescript
// lib/supabase.ts
import { createClientComponentClient, createServerComponentClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'

export const createClient = () => createClientComponentClient()

export const createServerClient = () =>
  createServerComponentClient({ cookies })
```

### frontend/lib/utils.ts

```typescript
// lib/utils.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getScoreColor(score: number): string {
  if (score >= 300) return 'text-green-600 bg-green-50'
  if (score >= 200) return 'text-amber-600 bg-amber-50'
  return 'text-red-600 bg-red-50'
}

export function getTrendColor(score: number): string {
  if (score >= 70) return 'text-green-600'
  if (score >= 40) return 'text-amber-600'
  return 'text-slate-400'
}
```

### frontend/middleware.ts

```typescript
// middleware.ts
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  const supabase = createMiddlewareClient({ req, res })
  const { data: { session } } = await supabase.auth.getSession()

  const isAuthPage = req.nextUrl.pathname.startsWith('/login')

  if (!session && !isAuthPage) {
    return NextResponse.redirect(new URL('/login', req.url))
  }

  if (session && isAuthPage) {
    return NextResponse.redirect(new URL('/', req.url))
  }

  return res
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.png$).*)'],
}
```

---

## SECTION 8 — FRONTEND PAGES

**Build every page listed. No placeholder "TODO" stubs. Every page must render real data from Supabase.**

### app/(auth)/login/page.tsx

Full login page. Features:
- Centered card layout on a `bg-slate-50` full-screen page
- AOIP logo/title at top
- Email and password inputs with proper labels
- "Sign In" button — calls `supabase.auth.signInWithPassword()`
- Error message display below inputs
- On success: `router.push('/')`

### app/(dashboard)/layout.tsx

Persistent sidebar layout. Features:
- Fixed left sidebar, 240px wide, `bg-slate-900` background
- Logo "AOIP" at top in white
- Nav links with icons (use lucide-react):
  - Home (`/`) — LayoutDashboard icon
  - Opportunities (`/opportunities`) — Trophy icon
  - Keywords (`/keywords`) — Search icon
  - Competitors (`/competitors`) — Swords icon
  - Community (`/community`) — Users icon
  - Niches (`/niches`) — Layers icon
  - Reports (`/reports`) — FileText icon
  - Scheduler (`/scheduler`) — Activity icon
- Active link highlighted with `bg-slate-700`
- Sign out button at the bottom
- Main content area: `ml-60 p-8 bg-slate-50 min-h-screen`

### app/(dashboard)/page.tsx — Home

Features:
- Page title: "Opportunity Dashboard"
- Top stat cards row: Total Opportunities | Keywords Discovered | Concepts Generated | Last Job Run
- Section: "Top 10 Opportunities" — uses `OpportunityCard` component
- Section: "Active Niches" — badge list of enabled niches with keyword counts
- All data fetched from Supabase directly (server component or useEffect)

### app/(dashboard)/opportunities/page.tsx

Features:
- Full sortable table of opportunities
- Columns: Rank | Keyword | Niche | Final Score | Demand | Growth | Competition Penalty | Action
- Score column uses `ScoreBadge` component
- Filter bar: dropdown for niche, input for minimum score
- Click any row to open a Dialog showing full product concept
- Product concept dialog shows: app name, tagline, target audience, core features list, premium features list, monetization, price, build time, tech stack, full concept text

### app/(dashboard)/keywords/page.tsx

Features:
- Search input (filter by keyword text)
- Niche filter dropdown
- Source filter (seed / ai_expand)
- Table: Keyword | Niche | Source | Demand | Growth | Stability | Trend Score | Discovered At
- Trend score column uses color coding: green ≥70, amber 40-69, gray <40
- Pagination: show 100 per page

### app/(dashboard)/competitors/page.tsx

Features:
- Keyword search to filter
- Table: App Name | Keyword | Downloads | Rating | Reviews | Has Ads | Competition Score | Action
- Action button opens a sheet/modal with review insights (complaints + feature requests) for that app
- Review insights shown as two lists with frequency badges

### app/(dashboard)/community/page.tsx

Features:
- Three tabs: Pain Points | Feature Requests | Emerging Trends
- Niche filter dropdown
- Each tab shows a card list: insight text, confidence badge, niche badge
- Below insights: "Recent Reddit Posts" table with title, subreddit, upvotes, link

### app/(dashboard)/niches/page.tsx

Features:
- List of all niches as cards
- Each card: niche name, priority slider (1-10), enabled toggle, keyword count badge
- "Add Niche" button → Dialog with name input + priority selector
- Each niche card has an "Add Keywords" button that opens a Dialog with:
  - Large textarea (placeholder: "Enter one keyword per line, max 1000")
  - Live counter showing keyword count as user types
  - Submit button that calls `POST /api/niches/:id/seeds`
  - Success toast showing how many were imported

### app/(dashboard)/reports/page.tsx

Features:
- Toggle: Daily / Weekly
- Report card showing: date, top opportunities list, new keywords count, new concepts count
- Top pain points section
- "Download JSON" button

### app/(dashboard)/scheduler/page.tsx

Features:
- Page title: "Scheduler Status"
- Live job log table using Supabase realtime subscription to `job_log` table
- Columns: Job Name | Status | Started | Finished | Duration | Message
- Status column uses `JobStatusChip` component
- Auto-refreshes via realtime — no manual refresh needed
- Latest entry highlighted at top

---

## SECTION 9 — FRONTEND COMPONENTS

### components/Sidebar.tsx

See layout description in Section 8. Extract the sidebar markup into this component and import it in `(dashboard)/layout.tsx`.

### components/OpportunityCard.tsx

```
Props: opportunity (with nested keyword, niche, product_concept)

Renders:
- Card with white background, subtle shadow
- Top row: keyword text (bold) + niche badge
- Score display: large final_score number, colour-coded (green/amber/red)
- Score breakdown: small pills for demand, growth, competition_penalty
- If product concept exists: app name in italic, tagline, build_time_weeks
- "View Full Concept" button that triggers parent onClick
```

### components/ScoreBadge.tsx

```
Props: score (number), size? ('sm' | 'md')

Renders a pill badge:
- score >= 300 → green background, "Strong" label
- score >= 200 → amber background, "Good" label  
- score < 200 → slate background, "Weak" label
- Shows the numeric score + label
```

### components/TrendSparkline.tsx

```
Props: data (number[]) — array of 12-52 weekly values

Renders a small Recharts LineChart:
- No axes, no labels, no tooltip
- Width: 120px, Height: 40px
- Line colour: green if last value > first value (growing), red if declining
- Used inline in keyword tables
```

### components/JobStatusChip.tsx

```
Props: status ('running' | 'success' | 'error')

Renders a small chip:
- running → blue background, spinner icon, "Running"
- success → green background, check icon, "Success"
- error → red background, X icon, "Error"
```

### components/SeedKeywordImporter.tsx

```
Props: nicheId (string), onSuccess (() => void)

Renders:
- Textarea with placeholder "Enter one keyword per line (max 1,000)"
- Character/line counter below: "247 keywords"
- Warning if over 1000 lines: "Limit is 1,000 — extra lines will be ignored"
- Submit button: "Import Keywords"
- On submit: calls POST /api/niches/:id/seeds
- On success: shows "✓ 247 keywords imported" toast + calls onSuccess()
```

---

## SECTION 10 — SUPABASE CONFIG FILES

**Agent 3 creates these files.**

### supabase/rls_policies.sql

```sql
-- Enable RLS on all tables
ALTER TABLE niches ENABLE ROW LEVEL SECURITY;
ALTER TABLE seed_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE community_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE community_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_concepts ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_log ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated users only
CREATE POLICY "Authenticated users can do everything" ON niches FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can do everything" ON seed_keywords FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can do everything" ON keywords FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can do everything" ON competitors FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can do everything" ON review_insights FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can do everything" ON community_posts FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can do everything" ON community_insights FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can do everything" ON opportunities FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can do everything" ON product_concepts FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can do everything" ON job_log FOR ALL USING (auth.role() = 'authenticated');
```

### supabase/seed_niches.sql

```sql
-- Default niches — run after schema.sql
INSERT INTO niches (name, priority, enabled) VALUES
  ('Finance', 10, true),
  ('Students', 9, true),
  ('Productivity', 9, true),
  ('Health', 8, true),
  ('Fitness', 8, true),
  ('Business', 7, true),
  ('Education', 7, true),
  ('AI', 8, true),
  ('Real Estate', 6, true),
  ('Construction', 5, true),
  ('Agriculture', 5, true)
ON CONFLICT (name) DO NOTHING;
```

### README.md

Agent 3 writes a complete README with these exact sections:
1. **What this is** — 2-paragraph description
2. **Prerequisites** — Node 18+, Python 3.11+, Supabase account, Anthropic API key, Reddit API credentials
3. **Database setup** — Step by step: run schema.sql, then rls_policies.sql, then seed_niches.sql in Supabase SQL editor. Create `reports` storage bucket. Create one user in Authentication → Users.
4. **Backend setup** — `cd backend`, `pip install -r requirements.txt`, copy `.env.example` to `.env`, fill in values, `uvicorn main:app --reload`
5. **Frontend setup** — `cd frontend`, `npm install`, copy `.env.local.example` to `.env.local`, fill in values, `npm run dev`
6. **Deployment** — Render instructions (build command, start command, env vars, cron-job.org health ping). Vercel instructions (root dir, env vars).
7. **First run checklist** — After both are deployed: add niches, add seed keywords, verify /health endpoint, check /scheduler page for first job run.

---

## SECTION 11 — AGENT COMPLETION CHECKLIST

When you finish your assigned work, verify each item below before marking your agent as done.

### Agent 1 — Backend
- [ ] All files in `backend/` created with no placeholder code
- [ ] Every `async def run()` function in modules is fully implemented
- [ ] Every API route returns real data from Supabase (no hardcoded mock data)
- [ ] `scheduler.py` imports all module run functions without circular imports
- [ ] `config.py` raises `EnvironmentError` for missing critical vars
- [ ] No `asyncio.gather()` calls anywhere — all jobs are sequential
- [ ] Every external API call has a `try/except` block and a `sleep()` before it
- [ ] `__init__.py` files exist in `modules/` and `api/` directories

### Agent 2 — Frontend
- [ ] All 8 dashboard pages are complete with real Supabase data fetching
- [ ] Login page redirects to `/` on success and shows error on failure
- [ ] Middleware protects all routes except `/login`
- [ ] All 5 components are complete and accept their documented props
- [ ] No page has "TODO" or "coming soon" placeholder text
- [ ] Sidebar shows correct active state for current route
- [ ] SeedKeywordImporter respects 1000 keyword limit
- [ ] Scheduler page subscribes to realtime job_log changes

### Agent 3 — DB + Config
- [ ] `supabase/schema.sql` has all 10 tables with correct foreign keys
- [ ] `supabase/rls_policies.sql` enables RLS on all 10 tables
- [ ] `supabase/seed_niches.sql` inserts all 11 default niches
- [ ] `backend/.env.example` has all 8 variables from Section 3
- [ ] `frontend/.env.local.example` has all 3 variables from Section 3
- [ ] `README.md` has all 7 sections with exact terminal commands

---

## SECTION 12 — CRITICAL RULES FOR ALL AGENTS

1. **Never write mock data.** Every component fetches from Supabase. If no data exists yet, show an empty state (e.g. "No opportunities yet — add seed keywords to get started").

2. **Never use `asyncio.gather()` or run jobs in parallel.** Memory limit on Render free tier is 512 MB.

3. **Always wrap external API calls in try/except.** pytrends, google-play-scraper, praw, and Anthropic can all fail. Log the error and continue to the next item.

4. **Always sleep between external calls:**
   - pytrends: `time.sleep(12)` — mandatory
   - google-play-scraper: `await asyncio.sleep(3)`
   - praw (Reddit): `await asyncio.sleep(2)`
   - Anthropic API: `await asyncio.sleep(1)`

5. **AI responses must always be valid JSON.** The `ai_client.py` wrapper strips markdown fences. If `json.loads()` still fails, catch the exception, log it, and skip that item.

6. **Table names are sacred.** Use exactly: `niches`, `seed_keywords`, `keywords`, `competitors`, `review_insights`, `community_posts`, `community_insights`, `opportunities`, `product_concepts`, `job_log`. No variations.

7. **The backend uses the Supabase service key** (bypasses RLS). The frontend uses the anon key (RLS enforced). Never swap these.

8. **Do not add features not listed in this document.** Scope creep breaks the 24-hour build target. If you think something is missing, add a comment `# NOTE: consider adding X` and move on.
```
