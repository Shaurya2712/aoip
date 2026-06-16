# STATUS: COMPLETE
# modules/m2_keyword.py
# PURPOSE: Expand seed keywords into related sub-keywords using the AI API.
# RUNS: Every 6 hours via scheduler.
# OUTPUT: Writes new rows to the `keywords` table.

import asyncio
from datetime import datetime, timedelta, timezone
from db import get_db
from ai_client import ai_bulk
from modules.m1_niche import get_active_niches, get_seed_keywords
from config import M2_BATCH_SIZE, M2_MAX_BATCHES_PER_RUN, M2_REEXPAND_DAYS

BATCH_EXPAND_PROMPT = """
You are a mobile app market research expert focused on the Indian Android market.

For the "{niche}" niche, expand EACH seed keyword below into exactly 10 related search queries
that Indian Android users would type into Google Play Store or Google Search for utility apps.

Seed keywords (one per line):
{seeds_block}

Rules:
- Focus on utility apps, calculators, trackers, planners, managers
- Include English and Hinglish variations where relevant
- Do NOT include brand names or existing app names
- Each keyword should be 2-5 words

Return ONLY this JSON, nothing else:
{{"expansions": [{{"seed": "exact seed from list", "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8", "kw9", "kw10"]}}]}}
"""


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _recently_expanded_parents(db, niche_id: str) -> set[str]:
    """Seeds expanded within M2_REEXPAND_DAYS — skip to avoid repeat API calls."""
    since = (datetime.now(timezone.utc) - timedelta(days=M2_REEXPAND_DAYS)).isoformat()
    res = (
        db.table("keywords")
        .select("parent_keyword")
        .eq("niche_id", niche_id)
        .eq("source", "ai_expand")
        .gte("created_at", since)
        .execute()
    )
    return {r["parent_keyword"] for r in res.data if r.get("parent_keyword")}


def _upsert_keywords(db, niche_id: str, seed_norm: str, keywords: list[str], from_ai: bool):
    for kw in keywords:
        if not kw:
            continue
        db.table("keywords").upsert(
            {
                "keyword": kw,
                "niche_id": niche_id,
                "source": "seed" if kw == seed_norm else ("ai_expand" if from_ai else "seed"),
                "parent_keyword": seed_norm,
            },
            on_conflict="keyword,niche_id",
        ).execute()


async def run():
    db = get_db()
    niches = await get_active_niches()
    batches_done = 0
    api_calls = 0

    for niche in niches:
        if batches_done >= M2_MAX_BATCHES_PER_RUN:
            break

        seeds = await get_seed_keywords(niche["id"])
        expanded_recently = _recently_expanded_parents(db, niche["id"])
        pending = [s.lower().strip() for s in seeds if s.lower().strip() not in expanded_recently]

        # Always ensure seed rows exist even when skipping AI expansion
        for seed in seeds:
            seed_norm = seed.lower().strip()
            if not seed_norm:
                continue
            if seed_norm in expanded_recently:
                _upsert_keywords(db, niche["id"], seed_norm, [seed_norm], from_ai=False)

        if not pending:
            print(f"[m2] {niche['name']}: all seeds recently expanded, skipping AI.")
            continue

        for batch in _chunks(pending, M2_BATCH_SIZE):
            if batches_done >= M2_MAX_BATCHES_PER_RUN:
                print(f"[m2] Hit batch cap ({M2_MAX_BATCHES_PER_RUN}), stopping until next run.")
                break

            seeds_block = "\n".join(f"- {s}" for s in batch)
            try:
                result = await ai_bulk(
                    BATCH_EXPAND_PROMPT.format(niche=niche["name"], seeds_block=seeds_block)
                )
                api_calls += 1
                expansions = result.get("expansions", [])

                matched = {e.get("seed", "").lower().strip() for e in expansions}
                for seed_norm in batch:
                    entry = next(
                        (e for e in expansions if (e.get("seed") or "").lower().strip() == seed_norm),
                        None,
                    )
                    if entry:
                        kws = [seed_norm] + [
                            k.lower().strip() for k in entry.get("keywords", []) if k
                        ]
                        _upsert_keywords(db, niche["id"], seed_norm, list(set(kws)), from_ai=True)
                    else:
                        _upsert_keywords(db, niche["id"], seed_norm, [seed_norm], from_ai=False)

                    if seed_norm not in matched:
                        print(f"[m2] No AI expansion for '{seed_norm}', seed only.")

                print(f"[m2] {niche['name']}: batch of {len(batch)} seeds expanded")

            except Exception as e:
                print(f"[m2] Batch error ({niche['name']}): {e}")
                for seed_norm in batch:
                    _upsert_keywords(db, niche["id"], seed_norm, [seed_norm], from_ai=False)

            batches_done += 1
            await asyncio.sleep(1)

    print(f"[m2] Done — {api_calls} API call(s), {batches_done} batch(es)")
    if api_calls == 0 and batches_done == 0:
        return "no work: all seeds recently expanded"
    return f"{api_calls} API call(s), {batches_done} batch(es)"
