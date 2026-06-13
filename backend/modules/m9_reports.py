# STATUS: COMPLETE
# modules/m9_reports.py
# PURPOSE: Generate daily summary reports and store as JSON in Supabase Storage.
# RUNS: Daily at 3am IST via scheduler.

import json
from datetime import datetime, timedelta
from db import get_db


async def generate_daily():
    db = get_db()
    today = datetime.utcnow().date().isoformat()
    yesterday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()

    # Top 15 opportunities
    top_opps = (
        db.table("opportunities")
        .select("final_score, ai_reasoning, keyword_id, keywords(keyword, niche_id, niches(name))")
        .order("final_score", desc=True)
        .limit(15)
        .execute()
        .data
    )

    # New keywords discovered in last 24h
    new_kws = (
        db.table("keywords")
        .select("keyword, source, niches(name)")
        .gte("created_at", yesterday)
        .limit(50)
        .execute()
        .data
    )

    # New product concepts generated
    new_concepts = (
        db.table("product_concepts")
        .select("app_name, tagline, price_suggestion, build_time_weeks")
        .gte("generated_at", yesterday)
        .execute()
        .data
    )

    # Top community pain points
    top_pain = (
        db.table("community_insights")
        .select("text, confidence, niches(name)")
        .eq("type", "pain_point")
        .order("confidence", desc=True)
        .limit(10)
        .execute()
        .data
    )

    report = {
        "date": today,
        "type": "daily",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "top_opportunity": top_opps[0] if top_opps else None,
            "new_keywords_count": len(new_kws),
            "new_concepts_count": len(new_concepts),
        },
        "top_opportunities": top_opps,
        "new_keywords": new_kws,
        "new_concepts": new_concepts,
        "top_pain_points": top_pain,
    }

    # Store in Supabase Storage bucket named 'reports'
    try:
        db.storage.from_("reports").upload(
            f"daily/{today}.json",
            json.dumps(report, indent=2, default=str).encode(),
            {"content-type": "application/json", "upsert": "true"},
        )
        print(f"[m9] Daily report stored: daily/{today}.json")
    except Exception as e:
        print(f"[m9] Storage error: {e}")
        # Fallback: store in job_log table
        db.table("job_log").insert({
            "job_name": "daily_report_content",
            "status": "success",
            "message": json.dumps(report, default=str)[:500],
        }).execute()
