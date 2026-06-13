# STATUS: COMPLETE
# api/opportunities.py
from fastapi import APIRouter, Query
from typing import Optional
from db import get_db

router = APIRouter()


@router.get("/")
def list_opportunities(
    niche_id: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    q = (
        get_db()
        .table("opportunities")
        .select("*, keywords(keyword, niche_id, niches(name)), product_concepts(app_name, tagline, price_suggestion, build_time_weeks)")
    )
    if min_score is not None:
        q = q.gte("final_score", min_score)
    res = q.order("final_score", desc=True).range(offset, offset + limit - 1).execute()
    # Filter by niche in Python (join filter)
    data = res.data
    if niche_id:
        data = [o for o in data if o.get("keywords", {}).get("niche_id") == niche_id]
    return data


@router.get("/{opportunity_id}")
def get_opportunity(opportunity_id: str):
    res = (
        get_db()
        .table("opportunities")
        .select("*, keywords(keyword, niches(name)), product_concepts(*)")
        .eq("id", opportunity_id)
        .single()
        .execute()
    )
    return res.data
