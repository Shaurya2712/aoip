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
Score an Android app opportunity for an indie developer in India.

KEYWORD: {keyword}
NICHE: {niche}

SIGNALS:
- Trends demand (0-100): {demand}
- Trends growth (0-100): {growth}
- Trends stability (0-100): {stability}
- Competitor apps found: {num_competitors}
- Avg competitor rating: {avg_rating}/5
- Avg competition score (0-100): {avg_competition}
- Review insights: {insight_count}
- Community posts in niche: {community_count}

Score each dimension 0-100, then:
final_score = demand_score + growth_score + pain_point_score + community_score + monetization_score
              - competition_penalty - complexity_penalty

Return ONLY this JSON (no markdown, short strings, no quotes inside values):
{{
  "demand_score": 0,
  "growth_score": 0,
  "pain_point_score": 0,
  "community_score": 0,
  "monetization_score": 0,
  "competition_penalty": 0,
  "complexity_penalty": 0,
  "final_score": 0,
  "ai_reasoning": "short reason under 80 chars"
}}
"""

SCORE_PROMPT_MINIMAL = """
Score Android app opportunity in India.

Keyword: {keyword}
Demand: {demand}, Growth: {growth}, Competitors: {num_competitors}, Review insights: {insight_count}

Return ONLY JSON with integer fields:
demand_score, growth_score, pain_point_score, community_score, monetization_score,
competition_penalty, complexity_penalty, final_score, ai_reasoning (max 60 chars, no quotes inside).
"""


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _clamp_int(value, default: int = 0, lo: int = 0, hi: int = 100) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _heuristic_opportunity_score(
    kw: dict,
    *,
    num_competitors: int,
    avg_rating: float,
    avg_competition: float,
    insight_count: int,
    community_count: int,
) -> dict:
    """Rule-based fallback when Gemini fails — uses trend + competitor signals."""
    demand = _clamp_int(kw.get("demand_score"))
    growth = _clamp_int(kw.get("growth_score"))
    stability = _clamp_int(kw.get("stability_score"))

    pain_point = min(100, insight_count * 10)
    if avg_rating > 0 and avg_rating < 3.5:
        pain_point = min(100, pain_point + 15)

    community = min(100, community_count * 8)
    monetization = min(100, int(demand * 0.35 + stability * 0.25 + growth * 0.15))

    if avg_competition > 0:
        competition_penalty = _clamp_int(avg_competition * 0.85)
    else:
        competition_penalty = min(100, num_competitors * 7)

    complexity_penalty = min(50, max(0, num_competitors * 3 - 5))

    final_score = max(
        0,
        demand + growth + pain_point + community + monetization
        - competition_penalty - complexity_penalty,
    )

    return {
        "demand_score": demand,
        "growth_score": growth,
        "pain_point_score": pain_point,
        "community_score": community,
        "monetization_score": monetization,
        "competition_penalty": competition_penalty,
        "complexity_penalty": complexity_penalty,
        "final_score": final_score,
        "ai_reasoning": "Heuristic score from trends and competitor data.",
    }


def _normalize_score(raw: dict, signals: dict) -> dict:
    """Ensure all fields are present and final_score is consistent."""
    demand = _clamp_int(raw.get("demand_score"), signals["demand"])
    growth = _clamp_int(raw.get("growth_score"), signals["growth"])
    pain = _clamp_int(raw.get("pain_point_score"))
    community = _clamp_int(raw.get("community_score"))
    monetization = _clamp_int(raw.get("monetization_score"))
    comp_pen = _clamp_int(raw.get("competition_penalty"))
    complexity = _clamp_int(raw.get("complexity_penalty"), hi=100)

    computed = max(
        0,
        demand + growth + pain + community + monetization - comp_pen - complexity,
    )
    final = _clamp_int(raw.get("final_score"), computed, lo=0, hi=500)
    if abs(final - computed) > 40:
        final = computed

    reasoning = str(raw.get("ai_reasoning") or "").strip()
    if not reasoning:
        reasoning = "AI-scored from market signals."
    reasoning = reasoning[:200]

    return {
        "demand_score": demand,
        "growth_score": growth,
        "pain_point_score": pain,
        "community_score": community,
        "monetization_score": monetization,
        "competition_penalty": comp_pen,
        "complexity_penalty": complexity,
        "final_score": final,
        "ai_reasoning": reasoning,
    }


async def _ai_score_keyword(prompt: str, minimal_prompt: str) -> dict | None:
    for attempt, p in enumerate((prompt, minimal_prompt)):
        try:
            return await ai_bulk(p)
        except Exception as e:
            label = "full" if attempt == 0 else "minimal"
            print(f"[m7] AI ({label}) attempt failed: {e}")
            if attempt == 0:
                await asyncio.sleep(2)
    return None


def _keywords_for_scoring(db, limit: int) -> list[dict]:
    """Keywords with trend data not opportunity-scored in 24h."""
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
    heuristic_saved = 0
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

            comps = (
                db.table("competitors")
                .select("id, rating, competition_score")
                .eq("keyword_id", kw["id"])
                .execute()
                .data
            )
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

            ratings = [c["rating"] for c in comps if c.get("rating") is not None]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

            comp_scores = [c["competition_score"] for c in comps if c.get("competition_score") is not None]
            avg_competition = sum(comp_scores) / len(comp_scores) if comp_scores else 0.0

            signals = {
                "demand": kw.get("demand_score", 0) or 0,
                "growth": kw.get("growth_score", 0) or 0,
                "stability": kw.get("stability_score", 0) or 0,
                "num_competitors": len(comps),
                "avg_rating": round(avg_rating, 1),
                "avg_competition": round(avg_competition, 1),
                "insight_count": insight_count,
                "community_count": community_cache[niche_id],
            }

            prompt = SCORE_PROMPT.format(
                keyword=kw["keyword"],
                niche=niche_cache[niche_id],
                **signals,
            )
            minimal = SCORE_PROMPT_MINIMAL.format(
                keyword=kw["keyword"],
                demand=signals["demand"],
                growth=signals["growth"],
                num_competitors=signals["num_competitors"],
                insight_count=signals["insight_count"],
            )

            raw = await _ai_score_keyword(prompt, minimal)
            used_heuristic = False
            if raw:
                api_calls += 1
                score = _normalize_score(raw, signals)
            else:
                score = _heuristic_opportunity_score(
                    kw,
                    num_competitors=len(comps),
                    avg_rating=avg_rating,
                    avg_competition=avg_competition,
                    insight_count=insight_count,
                    community_count=community_cache[niche_id],
                )
                used_heuristic = True
                heuristic_saved += 1
                print(f"[m7] Using heuristic scores for: {kw['keyword']}")

            db.table("opportunities").upsert(
                {"keyword_id": kw["id"], "scored_at": now_iso, **score},
                on_conflict="keyword_id",
            ).execute()

            saved += 1
            tag = " (heuristic)" if used_heuristic else ""
            print(f"[m7] Scored '{kw['keyword']}' → final_score={score.get('final_score')}{tag}")

        except Exception as e:
            print(f"[m7] Error scoring '{kw['keyword']}': {e} — trying heuristic fallback")
            try:
                comps = (
                    db.table("competitors")
                    .select("id, rating, competition_score")
                    .eq("keyword_id", kw["id"])
                    .execute()
                    .data
                )
                ratings = [c["rating"] for c in comps if c.get("rating") is not None]
                comp_scores = [c["competition_score"] for c in comps if c.get("competition_score") is not None]
                score = _heuristic_opportunity_score(
                    kw,
                    num_competitors=len(comps),
                    avg_rating=sum(ratings) / len(ratings) if ratings else 0.0,
                    avg_competition=sum(comp_scores) / len(comp_scores) if comp_scores else 0.0,
                    insight_count=0,
                    community_count=community_cache.get(kw["niche_id"], 0),
                )
                db.table("opportunities").upsert(
                    {"keyword_id": kw["id"], "scored_at": now_iso, **score},
                    on_conflict="keyword_id",
                ).execute()
                saved += 1
                heuristic_saved += 1
                print(f"[m7] Scored '{kw['keyword']}' → final_score={score.get('final_score')} (heuristic)")
            except Exception as e2:
                print(f"[m7] Heuristic fallback failed for '{kw['keyword']}': {e2}")
            continue

    print(
        f"[m7] Done — {api_calls} AI call(s), {saved} opportunity(s) saved"
        + (f", {heuristic_saved} heuristic" if heuristic_saved else "")
    )
    if saved == 0:
        return f"0 opportunities saved ({api_calls} AI calls failed)"
    return f"{saved} opportunity(s) scored"
