# STATUS: COMPLETE
# modules/m3_trends.py
# PURPOSE: Fetch Google Trends data per keyword and score it via AI.
# RUNS: Every 6 hours via scheduler.
# OUTPUT: Updates demand_score, growth_score, stability_score, seasonal_score, trend_score on `keywords` table.

import asyncio
import functools
import statistics
from datetime import datetime, timedelta, timezone
from pytrends.request import TrendReq
from db import get_db
from ai_client import ai_bulk
from config import (
    M3_MAX_KEYWORDS_PER_RUN,
    M3_BATCH_SIZE,
    M3_PYTRENDS_DELAY_SEC,
    M3_PYTRENDS_TIMEOUT_SEC,
    M3_PYTRENDS_MAX_RETRIES,
    M3_PYTRENDS_429_BACKOFF_SEC,
    M3_PYTRENDS_429_ABORT_AFTER,
    M3_AI_ESTIMATE_ON_TRENDS_FAIL,
    M3_AI_ESTIMATE_MAX_PER_RUN,
)

BATCH_SCORE_PROMPT = """
You are analysing Google Trends summaries for a mobile app market researcher (India, last 12 months).

For EACH keyword below, compute integer scores 0-100:
- demand_score, growth_score, stability_score, seasonal_score, trend_score

Keywords and summaries:
{items_block}

Return ONLY this JSON:
{{"scores": [{{"keyword": "exact keyword", "demand_score": 0, "growth_score": 0, "stability_score": 0, "seasonal_score": 0, "trend_score": 0}}]}}
"""

SINGLE_SCORE_PROMPT = """
Analyse this Google Trends summary for "{keyword}" (India, utility apps, last 12 months).

Summary: {summary}

Return ONLY this JSON:
{{"demand_score": 0, "growth_score": 0, "stability_score": 0, "seasonal_score": 0, "trend_score": 0}}
"""

ESTIMATE_PROMPT = """
Keyword: "{keyword}"
Market: Indian Android utility apps. Google Trends data was unavailable.

Estimate plausible integer scores 0-100 for search demand, growth, stability, seasonality, and overall trend_score.

Return ONLY this JSON:
{{"demand_score": 0, "growth_score": 0, "stability_score": 0, "seasonal_score": 0, "trend_score": 0}}
"""


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _is_rate_limited(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg


def _summarize_trends(values: list) -> dict:
    """Compact stats — avoids huge prompts that trigger Gemma 500 errors."""
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return {"avg": 0, "min": 0, "max": 0, "growth_pct": 0, "volatility": 0}
    mid = len(nums) // 2
    first_half = nums[:mid] or [0]
    second_half = nums[mid:] or first_half
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    growth_pct = round((second_avg - first_avg) / max(first_avg, 1) * 100, 1)
    avg = round(sum(nums) / len(nums), 1)
    volatility = round(statistics.pstdev(nums), 1) if len(nums) > 1 else 0.0
    return {
        "avg": avg,
        "min": int(min(nums)),
        "max": int(max(nums)),
        "growth_pct": growth_pct,
        "volatility": volatility,
    }


def _heuristic_scores(summary: dict) -> dict:
    """Rule-based fallback when Gemini returns 500."""
    demand = int(min(100, max(0, summary["avg"])))
    growth = int(min(100, max(0, 50 + summary["growth_pct"] / 2)))
    stability = int(min(100, max(0, 100 - summary["volatility"] * 3)))
    seasonal = int(min(100, max(0, summary["volatility"] * 4)))
    trend = int(min(100, max(0, demand * 0.35 + growth * 0.35 + stability * 0.2)))
    return {
        "demand_score": demand,
        "growth_score": growth,
        "stability_score": stability,
        "seasonal_score": seasonal,
        "trend_score": trend,
    }


def _keywords_needing_score(db, limit: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    res = (
        db.table("keywords")
        .select("id, keyword, last_scored_at")
        .order("last_scored_at", nullsfirst=True)
        .limit(500)
        .execute()
    )
    pending = []
    for row in res.data or []:
        ts = row.get("last_scored_at")
        if ts is None:
            pending.append(row)
        else:
            try:
                if _parse_ts(ts) < cutoff:
                    pending.append(row)
            except ValueError:
                pending.append(row)
        if len(pending) >= limit:
            break
    return pending


def _fetch_interest(pytrends: TrendReq, keyword: str):
    pytrends.build_payload([keyword], timeframe="today 12-m", geo="IN")
    return pytrends.interest_over_time()


async def _fetch_with_retries(loop, keyword: str) -> object | None:
    for attempt in range(M3_PYTRENDS_MAX_RETRIES):
        pytrends = TrendReq(hl="en-IN", tz=330, timeout=(10, 25))
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(_fetch_interest, pytrends, keyword),
                ),
                timeout=M3_PYTRENDS_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            print(f"[m3] Timeout ({M3_PYTRENDS_TIMEOUT_SEC}s) for: {keyword}")
            return None
        except Exception as e:
            if _is_rate_limited(e) and attempt < M3_PYTRENDS_MAX_RETRIES - 1:
                wait = M3_PYTRENDS_429_BACKOFF_SEC * (attempt + 1)
                print(f"[m3] Google Trends 429 for '{keyword}' — waiting {wait}s before retry")
                await asyncio.sleep(wait)
                continue
            raise
    return None


def _save_scores(db, item: dict, scores: dict, now_iso: str):
    db.table("keywords").update(
        {
            "demand_score": scores.get("demand_score"),
            "growth_score": scores.get("growth_score"),
            "stability_score": scores.get("stability_score"),
            "seasonal_score": scores.get("seasonal_score"),
            "trend_score": scores.get("trend_score"),
            "last_scored_at": now_iso,
        }
    ).eq("id", item["id"]).execute()
    print(f"[m3] Scored: {item['keyword']} → trend_score={scores.get('trend_score')}")


async def _ai_score_one(item: dict) -> dict | None:
    summary = item.get("summary") or _summarize_trends(item.get("data", []))
    summary_text = (
        f"avg={summary['avg']}, min={summary['min']}, max={summary['max']}, "
        f"growth_pct={summary['growth_pct']}, volatility={summary['volatility']}"
    )
    try:
        return await ai_bulk(
            SINGLE_SCORE_PROMPT.format(keyword=item["keyword"], summary=summary_text)
        )
    except Exception as e:
        print(f"[m3] AI score failed for '{item['keyword']}': {e}")
        if item.get("data"):
            print(f"[m3] Using heuristic scores for: {item['keyword']}")
            return _heuristic_scores(summary)
        return None


async def _ai_estimate_no_trends(item: dict) -> dict | None:
    try:
        return await ai_bulk(ESTIMATE_PROMPT.format(keyword=item["keyword"]))
    except Exception as e:
        print(f"[m3] AI estimate failed for '{item['keyword']}': {e}")
        return None


async def _score_and_save(db, with_trends: list[dict], without_trends: list[dict]) -> int:
    api_calls = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for item in with_trends:
        if "summary" not in item and item.get("data"):
            item["summary"] = _summarize_trends(item["data"])

    for batch in _chunks(with_trends, M3_BATCH_SIZE):
        if len(batch) == 1:
            scores = await _ai_score_one(batch[0])
            api_calls += 1
            if scores:
                _save_scores(db, batch[0], scores, now_iso)
            await asyncio.sleep(1)
            continue

        items_block = "\n".join(
            f'- "{item["keyword"]}": {item["summary"]}' for item in batch
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
                if scores:
                    _save_scores(db, item, scores, now_iso)
                else:
                    fallback = await _ai_score_one(item)
                    api_calls += 1
                    if fallback:
                        _save_scores(db, item, fallback, now_iso)
        except Exception as e:
            print(f"[m3] Batch scoring error: {e} — retrying one-by-one")
            for item in batch:
                scores = await _ai_score_one(item)
                api_calls += 1
                if scores:
                    _save_scores(db, item, scores, now_iso)
                await asyncio.sleep(1)

        await asyncio.sleep(1)

    if M3_AI_ESTIMATE_ON_TRENDS_FAIL and without_trends:
        cap = M3_AI_ESTIMATE_MAX_PER_RUN
        print(f"[m3] AI-estimating up to {cap} keyword(s) without Trends data...")
        for item in without_trends[:cap]:
            scores = await _ai_estimate_no_trends(item)
            api_calls += 1
            if scores:
                _save_scores(db, item, scores, now_iso)
            await asyncio.sleep(1)

    return api_calls


async def run():
    db = get_db()
    print("[m3] Starting trend analysis...")
    print(
        f"[m3] settings: {M3_MAX_KEYWORDS_PER_RUN} kw/run, "
        f"{M3_PYTRENDS_DELAY_SEC}s delay, AI batch={M3_BATCH_SIZE}, "
        f"estimate_on_fail={M3_AI_ESTIMATE_ON_TRENDS_FAIL}"
    )

    keywords = _keywords_needing_score(db, M3_MAX_KEYWORDS_PER_RUN)
    print(f"[m3] {len(keywords)} keyword(s) queued")

    if not keywords:
        print("[m3] No keywords need trend scoring.")
        return "no work: all keywords scored in last 24h"

    loop = asyncio.get_event_loop()
    with_trends: list[dict] = []
    without_trends: list[dict] = []
    consecutive_429 = 0
    trends_blocked = False

    for i, kw in enumerate(keywords, start=1):
        if trends_blocked:
            without_trends.append(kw)
            continue

        label = kw["keyword"]
        print(f"[m3] ({i}/{len(keywords)}) Waiting {M3_PYTRENDS_DELAY_SEC}s...")
        await asyncio.sleep(M3_PYTRENDS_DELAY_SEC)

        print(f"[m3] ({i}/{len(keywords)}) Fetching Google Trends: {label}")
        try:
            df = await _fetch_with_retries(loop, label)

            if df is None:
                without_trends.append(kw)
                continue

            if df.empty or label not in df.columns:
                print(f"[m3] No trends data for: {label}")
                without_trends.append(kw)
                consecutive_429 = 0
                continue

            summary = _summarize_trends(df[label].tolist())
            with_trends.append({
                "id": kw["id"],
                "keyword": label,
                "data": df[label].tolist(),
                "summary": summary,
            })
            consecutive_429 = 0
            print(f"[m3] Got trends for {label}: avg={summary['avg']}, growth={summary['growth_pct']}%")

        except Exception as e:
            if _is_rate_limited(e):
                consecutive_429 += 1
                print(f"[m3] Trends fetch error for '{label}': {e}")
                without_trends.append(kw)
                if consecutive_429 >= M3_PYTRENDS_429_ABORT_AFTER:
                    print(
                        f"[m3] Google Trends blocking this host ({consecutive_429}× 429). "
                        "Skipping further pytrends calls this run."
                    )
                    trends_blocked = True
                    without_trends.extend(keywords[i:])
                    break
                wait = M3_PYTRENDS_429_BACKOFF_SEC * consecutive_429
                print(f"[m3] Cooling down {wait}s...")
                await asyncio.sleep(wait)
                continue
            print(f"[m3] Trends fetch error for '{label}': {e}")
            without_trends.append(kw)
            consecutive_429 = 0

    api_calls = await _score_and_save(db, with_trends, without_trends)
    saved = len(with_trends) + (
        min(len(without_trends), M3_AI_ESTIMATE_MAX_PER_RUN)
        if M3_AI_ESTIMATE_ON_TRENDS_FAIL
        else 0
    )

    if not with_trends and not (M3_AI_ESTIMATE_ON_TRENDS_FAIL and without_trends):
        print("[m3] No keywords scored. Run from your laptop or retry in 6h.")
        return "0 keywords scored (Google Trends blocked, no AI estimates)"
    print(
        f"[m3] Done — {api_calls} AI call(s), "
        f"{len(with_trends)} with trends, "
        f"{len(without_trends)} without trends"
    )
    return (
        f"{api_calls} AI call(s); "
        f"{len(with_trends)} trends + "
        f"{min(len(without_trends), M3_AI_ESTIMATE_MAX_PER_RUN) if M3_AI_ESTIMATE_ON_TRENDS_FAIL else 0} estimated"
    )
