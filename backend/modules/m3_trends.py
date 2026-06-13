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
