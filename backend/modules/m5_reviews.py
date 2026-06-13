# STATUS: COMPLETE
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
