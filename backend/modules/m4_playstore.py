# STATUS: COMPLETE
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
