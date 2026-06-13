# STATUS: COMPLETE
# api/community.py
from fastapi import APIRouter, Query
from typing import Optional
from db import get_db

router = APIRouter()


@router.get("/insights")
def get_insights(
    niche_id: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    q = get_db().table("community_insights").select("*, niches(name)")
    if niche_id:
        q = q.eq("niche_id", niche_id)
    if type:
        q = q.eq("type", type)
    res = q.order("confidence", desc=True).limit(limit).execute()
    return res.data


@router.get("/posts")
def get_posts(niche_id: Optional[str] = None, limit: int = 50):
    q = get_db().table("community_posts").select("*")
    if niche_id:
        q = q.eq("niche_id", niche_id)
    res = q.order("upvotes", desc=True).limit(limit).execute()
    return res.data
