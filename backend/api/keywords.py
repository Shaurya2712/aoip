# STATUS: COMPLETE
# api/keywords.py
from fastapi import APIRouter, Query
from typing import Optional
from db import get_db

router = APIRouter()


@router.get("/")
def list_keywords(
    niche_id: Optional[str] = None,
    source: Optional[str] = None,
    min_trend_score: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
):
    q = get_db().table("keywords").select("*, niches(name)")
    if niche_id:
        q = q.eq("niche_id", niche_id)
    if source:
        q = q.eq("source", source)
    if min_trend_score is not None:
        q = q.gte("trend_score", min_trend_score)
    if search:
        q = q.ilike("keyword", f"%{search}%")
    res = q.order("trend_score", desc=True, nullsfirst=False).range(offset, offset + limit - 1).execute()
    return res.data


@router.get("/{keyword_id}/competitors")
def get_competitors(keyword_id: str):
    res = get_db().table("competitors").select("*").eq("keyword_id", keyword_id).order("rating", desc=True).execute()
    return res.data
