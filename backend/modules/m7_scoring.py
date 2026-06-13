# STATUS: COMPLETE
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
