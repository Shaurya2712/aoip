# STATUS: COMPLETE
# modules/m7_scoring.py
# PURPOSE: Score keywords as app opportunities using the AI API.
# RUNS: Every 12 hours via scheduler.
# OUTPUT: Upserts rows to `opportunities` table with full score breakdown.

import asyncio
from db import get_db
from ai_client import ai_bulk
from config import M7_MAX_KEYWORDS_PER_RUN

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

    # Skip keywords scored in the last 24 hours
    recent_opps = (
        db.table("opportunities")
        .select("keyword_id")
        .gte("scored_at", "now()-interval '24 hours'")
        .execute()
        .data
    )
    skip_ids = {r["keyword_id"] for r in recent_opps}

    keywords_res = (
        db.table("keywords")
        .select("id, keyword, niche_id, demand_score, growth_score, stability_score")
        .not_.is_("trend_score", "null")
        .order("trend_score", desc=True)
        .limit(M7_MAX_KEYWORDS_PER_RUN + len(skip_ids))
        .execute()
    )

    to_score = [kw for kw in keywords_res.data if kw["id"] not in skip_ids][:M7_MAX_KEYWORDS_PER_RUN]

    if not to_score:
        print("[m7] No keywords need opportunity scoring.")
        return

    # Pre-fetch niche names and community counts once per niche
    niche_cache: dict[str, str] = {}
    community_cache: dict[str, int] = {}

    api_calls = 0
    for kw in to_score:
        await asyncio.sleep(1)
        try:
            niche_id = kw["niche_id"]
            if niche_id not in niche_cache:
                niche_cache[niche_id] = (
                    db.table("niches").select("name").eq("id", niche_id).single().execute().data["name"]
                )
            if niche_id not in community_cache:
                resp = (
                    db.table("community_posts")
                    .select("id", count="exact")
                    .eq("niche_id", niche_id)
                    .execute()
                )
                community_cache[niche_id] = getattr(resp, "count", 0) or 0

            comps = db.table("competitors").select("id, rating").eq("keyword_id", kw["id"]).execute().data
            comp_ids = [c["id"] for c in comps]
            insight_count = 0
            if comp_ids:
                insight_count = (
                    db.table("review_insights")
                    .select("id", count="exact")
                    .in_("competitor_id", comp_ids)
                    .execute()
                )
                insight_count = getattr(insight_count, "count", 0) or 0

            avg_rating = (
                sum(c["rating"] or 0 for c in comps) / len(comps) if comps else 0
            )

            score = await ai_bulk(
                SCORE_PROMPT.format(
                    keyword=kw["keyword"],
                    niche=niche_cache[niche_id],
                    demand=kw.get("demand_score", 0) or 0,
                    growth=kw.get("growth_score", 0) or 0,
                    stability=kw.get("stability_score", 0) or 0,
                    num_competitors=len(comps),
                    avg_rating=round(avg_rating, 1),
                    insight_count=insight_count,
                    community_count=community_cache[niche_id],
                )
            )
            api_calls += 1

            db.table("opportunities").upsert(
                {"keyword_id": kw["id"], "scored_at": "now()", **score},
                on_conflict="keyword_id",
            ).execute()

            print(f"[m7] Scored '{kw['keyword']}' → final_score={score.get('final_score')}")

        except Exception as e:
            print(f"[m7] Error scoring '{kw['keyword']}': {e}")
            continue

    print(f"[m7] Done — {api_calls} API call(s)")
