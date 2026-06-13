# STATUS: COMPLETE
# modules/m8_analyst.py
# PURPOSE: Generate full product concepts for top-ranked opportunities using AI.
# RUNS: Daily at 2am IST via scheduler.
# OUTPUT: Inserts rows into `product_concepts` table.

import asyncio
from db import get_db
from ai_client import ai_analyze

CONCEPT_PROMPT = """
You are a senior Android app product strategist specialising in the Indian market.
You help indie developers build profitable utility apps.

Generate a complete product concept for this app opportunity:

KEYWORD: "{keyword}"
NICHE: "{niche}"
OPPORTUNITY SCORE: {score}/500

TOP USER COMPLAINTS FROM EXISTING APPS:
{complaints}

TOP FEATURE REQUESTS FROM USERS:
{features}

COMMUNITY PAIN POINTS (from Reddit):
{community}

Your concept must directly address the complaints and feature requests above.
Design for Indian Android users — consider: offline-first, low data usage, Hindi/regional language options, India-specific features (GST, UPI, etc. where relevant), ₹ pricing.

Return ONLY this JSON, nothing else:
{{
  "app_name": "Catchy name for the app",
  "tagline": "One line value proposition under 10 words",
  "target_audience": "Specific description of who uses this app",
  "core_features": [
    "Feature 1 — description",
    "Feature 2 — description",
    "Feature 3 — description",
    "Feature 4 — description",
    "Feature 5 — description"
  ],
  "premium_features": [
    "Premium feature 1",
    "Premium feature 2",
    "Premium feature 3"
  ],
  "monetization": "Detailed monetization strategy",
  "price_suggestion": "e.g. Free with ads, ₹299/year premium",
  "tech_stack": "e.g. Flutter + Firebase + Supabase",
  "build_time_weeks": 6,
  "full_concept": "A 150-200 word detailed product description covering the problem, solution, differentiator, and go-to-market angle."
}}
"""


async def run():
    db = get_db()

    # Get top opportunities that don't have a concept yet
    all_opps = (
        db.table("opportunities")
        .select("id, final_score, keyword_id")
        .order("final_score", desc=True)
        .limit(50)
        .execute()
        .data
    )

    existing_concept_ids = set(
        r["opportunity_id"]
        for r in db.table("product_concepts").select("opportunity_id").execute().data
    )

    to_process = [o for o in all_opps if o["id"] not in existing_concept_ids][:20]

    if not to_process:
        print("[m8] All top opportunities already have concepts.")
        return

    for opp in to_process:
        await asyncio.sleep(3)
        try:
            kw = (
                db.table("keywords")
                .select("keyword, niche_id")
                .eq("id", opp["keyword_id"])
                .single()
                .execute()
                .data
            )
            niche = (
                db.table("niches")
                .select("name")
                .eq("id", kw["niche_id"])
                .single()
                .execute()
                .data
            )
            # Get competitor IDs for this keyword
            comp_ids = [
                c["id"]
                for c in db.table("competitors")
                .select("id")
                .eq("keyword_id", opp["keyword_id"])
                .execute()
                .data
            ]
            # Gather review insights
            insights = (
                db.table("review_insights")
                .select("type, text, frequency")
                .in_("competitor_id", comp_ids)
                .order("frequency", desc=True)
                .limit(30)
                .execute()
                .data
            )
            # Gather community pain points
            community = (
                db.table("community_insights")
                .select("type, text")
                .eq("niche_id", kw["niche_id"])
                .eq("type", "pain_point")
                .limit(15)
                .execute()
                .data
            )

            complaints = [i["text"] for i in insights if i["type"] == "complaint"][:10]
            features = [i["text"] for i in insights if i["type"] == "feature_request"][:10]
            comm_pain = [i["text"] for i in community][:8]

            concept = await ai_analyze(
                CONCEPT_PROMPT.format(
                    keyword=kw["keyword"],
                    niche=niche["name"],
                    score=opp.get("final_score", 0),
                    complaints="\n".join(f"- {c}" for c in complaints) or "No data yet",
                    features="\n".join(f"- {f}" for f in features) or "No data yet",
                    community="\n".join(f"- {c}" for c in comm_pain) or "No data yet",
                )
            )

            db.table("product_concepts").insert(
                {"opportunity_id": opp["id"], **concept}
            ).execute()

            print(f"[m8] Concept generated: {concept.get('app_name')} for '{kw['keyword']}'")

        except Exception as e:
            print(f"[m8] Error for opportunity {opp['id']}: {e}")
            continue
