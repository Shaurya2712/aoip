# STATUS: COMPLETE
# modules/m7_scoring.py
# PURPOSE: Score keywords as app opportunities using the AI API.
# RUNS: Every 12 hours via scheduler.
# OUTPUT: Upserts rows to `opportunities` table with full score breakdown.

import asyncio
from datetime import datetime, timedelta, timezone
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


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _keywords_for_scoring(db, limit: int) -> list[dict]:
    """Keywords with trend data (trend_score or demand_score) not opportunity-scored in 24h."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_ids = set()
    for row in db.table("opportunities").select("keyword_id, scored_at").execute().data or []:
        ts = row.get("scored_at")
        if not ts:
            continue
        try:
            if _parse_ts(ts) >= cutoff:
                recent_ids.add(row["keyword_id"])
        except ValueError:
            pass

    res = (
        db.table("keywords")
        .select("id, keyword, niche_id, demand_score, growth_score, stability_score, trend_score")
        .limit(500)
        .execute()
    )
    pending = [
        kw
        for kw in (res.data or [])
        if kw["id"] not in recent_ids
        and (kw.get("trend_score") is not None or kw.get("demand_score") is not None)
    ]
    pending.sort(key=lambda k: (k.get("trend_score") or 0, k.get("demand_score") or 0), reverse=True)
    return pending[:limit]


async def run():
    db = get_db()

    to_score = _keywords_for_scoring(db, M7_MAX_KEYWORDS_PER_RUN)

    if not to_score:
        print("[m7] No keywords need opportunity scoring.")
        return "0 opportunities: run Trend analysis first (keywords need trend_score)"

    niche_cache: dict[str, str] = {}
    community_cache: dict[str, int] = {}

    api_calls = 0
    saved = 0
    now_iso = datetime.now(timezone.utc).isoformat()

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
                resp = (
                    db.table("review_insights")
                    .select("id", count="exact")
                    .in_("competitor_id", comp_ids)
                    .execute()
                )
                insight_count = getattr(resp, "count", 0) or 0

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
                {"keyword_id": kw["id"], "scored_at": now_iso, **score},
                on_conflict="keyword_id",
            ).execute()

            saved += 1
            print(f"[m7] Scored '{kw['keyword']}' → final_score={score.get('final_score')}")

        except Exception as e:
            print(f"[m7] Error scoring '{kw['keyword']}': {e}")
            continue

    print(f"[m7] Done — {api_calls} API call(s), {saved} opportunity(s) saved")
    if saved == 0:
        return f"0 opportunities saved ({api_calls} AI calls failed)"
    return f"{saved} opportunity(s) scored"
