# STATUS: COMPLETE
# modules/m3_trends.py
# PURPOSE: Fetch Google Trends data per keyword and score it via AI.
# RUNS: Every 6 hours via scheduler.
# OUTPUT: Updates demand_score, growth_score, stability_score, seasonal_score, trend_score on `keywords` table.

import asyncio
import time
from pytrends.request import TrendReq
from db import get_db
from ai_client import ai_bulk
from config import M3_MAX_KEYWORDS_PER_RUN, M3_BATCH_SIZE

BATCH_SCORE_PROMPT = """
You are analysing Google Trends data for a mobile app market researcher (India, last 12 months).

For EACH keyword below, compute integer scores 0-100:
- demand_score: average search interest
- growth_score: trend momentum (rising = high)
- stability_score: consistency year-round
- seasonal_score: how seasonal (spikes = high)
- trend_score: overall weighted score

Keywords and their interest arrays (0-100):
{items_block}

Return ONLY this JSON, nothing else:
{{"scores": [{{"keyword": "exact keyword", "demand_score": 0, "growth_score": 0, "stability_score": 0, "seasonal_score": 0, "trend_score": 0}}]}}
"""


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def run():
    db = get_db()

    res = (
        db.table("keywords")
        .select("id, keyword")
        .or_(
            "last_scored_at.is.null,"
            "last_scored_at.lt." + "now()-interval '24 hours'"
        )
        .limit(M3_MAX_KEYWORDS_PER_RUN)
        .execute()
    )

    if not res.data:
        print("[m3] No keywords need trend scoring.")
        return

    pytrends = TrendReq(hl="en-IN", tz=330, timeout=(10, 25))
    scored_items = []

    for kw in res.data:
        time.sleep(12)  # pytrends rate limit — do not reduce this
        try:
            pytrends.build_payload([kw["keyword"]], timeframe="today 12-m", geo="IN")
            df = pytrends.interest_over_time()

            if df.empty or kw["keyword"] not in df.columns:
                print(f"[m3] No trends data for: {kw['keyword']}")
                continue

            scored_items.append({
                "id": kw["id"],
                "keyword": kw["keyword"],
                "data": df[kw["keyword"]].tolist(),
            })
        except Exception as e:
            print(f"[m3] Trends fetch error for '{kw['keyword']}': {e}")
            continue

    if not scored_items:
        print("[m3] No trend data collected.")
        return

    api_calls = 0
    for batch in _chunks(scored_items, M3_BATCH_SIZE):
        items_block = "\n".join(
            f'- "{item["keyword"]}": {item["data"]}' for item in batch
        )
        try:
            result = await ai_bulk(BATCH_SCORE_PROMPT.format(items_block=items_block))
            api_calls += 1
            scores_by_kw = {
                (s.get("keyword") or "").lower().strip(): s
                for s in result.get("scores", [])
            }

            for item in batch:
                scores = scores_by_kw.get(item["keyword"].lower().strip())
                if not scores:
                    print(f"[m3] No AI score for: {item['keyword']}")
                    continue

                db.table("keywords").update(
                    {
                        "demand_score": scores.get("demand_score"),
                        "growth_score": scores.get("growth_score"),
                        "stability_score": scores.get("stability_score"),
                        "seasonal_score": scores.get("seasonal_score"),
                        "trend_score": scores.get("trend_score"),
                        "last_scored_at": "now()",
                    }
                ).eq("id", item["id"]).execute()

                print(f"[m3] Scored: {item['keyword']} → trend_score={scores.get('trend_score')}")

        except Exception as e:
            print(f"[m3] Batch scoring error: {e}")

        await asyncio.sleep(1)

    print(f"[m3] Done — {api_calls} API call(s) for {len(scored_items)} keyword(s)")
