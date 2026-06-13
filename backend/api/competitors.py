# STATUS: COMPLETE
# api/competitors.py
from fastapi import APIRouter
from db import get_db

router = APIRouter()


@router.get("/{competitor_id}/insights")
def get_insights(competitor_id: str):
    res = (
        get_db()
        .table("review_insights")
        .select("*")
        .eq("competitor_id", competitor_id)
        .order("frequency", desc=True)
        .execute()
    )
    return res.data
