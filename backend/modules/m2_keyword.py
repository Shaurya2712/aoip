# STATUS: COMPLETE
# modules/m2_keyword.py
# PURPOSE: Expand each seed keyword into 15 related sub-keywords using the AI API.
# RUNS: Every 6 hours via scheduler.
# OUTPUT: Writes new rows to the `keywords` table.

import asyncio
from db import get_db
from ai_client import ai_bulk
from modules.m1_niche import get_active_niches, get_seed_keywords

EXPAND_PROMPT = """
You are a mobile app market research expert focused on the Indian Android market.

Given the seed keyword "{keyword}" for the "{niche}" niche, generate exactly 15 related
search queries that Indian Android users would type into Google Play Store or Google Search
to find utility apps and tools.

Rules:
- Focus on utility apps, calculators, trackers, planners, managers
- Include both English and Hinglish variations where relevant
- Include regional variations (e.g. "GST calculator", "EMI calculator India")
- Do NOT include brand names or existing app names
- Each keyword should be 2-5 words

Return ONLY this JSON, nothing else:
{{"keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8", "kw9", "kw10", "kw11", "kw12", "kw13", "kw14", "kw15"]}}
"""


async def run():
    db = get_db()
    niches = await get_active_niches()

    for niche in niches:
        seeds = await get_seed_keywords(niche["id"])

        for seed in seeds:
            await asyncio.sleep(2)  # Rate limit buffer between AI calls

            try:
                result = await ai_bulk(
                    EXPAND_PROMPT.format(keyword=seed, niche=niche["name"])
                )
                new_keywords = result.get("keywords", [])
                all_keywords = list(set([seed.lower().strip()] + [k.lower().strip() for k in new_keywords]))

                for kw in all_keywords:
                    if not kw:
                        continue
                    db.table("keywords").upsert(
                        {
                            "keyword": kw,
                            "niche_id": niche["id"],
                            "source": "seed" if kw == seed.lower().strip() else "ai_expand",
                            "parent_keyword": seed.lower().strip(),
                        },
                        on_conflict="keyword,niche_id",
                    ).execute()

            except Exception as e:
                print(f"[m2] Error expanding keyword '{seed}': {e}")
                continue
