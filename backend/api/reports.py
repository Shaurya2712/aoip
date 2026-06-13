# STATUS: COMPLETE
# api/reports.py
from fastapi import APIRouter
from db import get_db
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/daily")
def get_daily_report():
    today = datetime.utcnow().date().isoformat()
    try:
        data = get_db().storage.from_("reports").download(f"daily/{today}.json")
        import json
        return json.loads(data)
    except Exception:
        # Fallback: build report on the fly from DB
        return _build_live_report()


def _build_live_report():
    db = get_db()
    top_opps = (
        db.table("opportunities")
        .select("final_score, keyword_id, keywords(keyword, niches(name))")
        .order("final_score", desc=True)
        .limit(10)
        .execute()
        .data
    )
    return {"type": "live", "generated_at": datetime.utcnow().isoformat(), "top_opportunities": top_opps}
