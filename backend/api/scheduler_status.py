# STATUS: COMPLETE
# api/scheduler_status.py
from fastapi import APIRouter
from db import get_db

router = APIRouter()


@router.get("/status")
def get_status():
    res = (
        get_db()
        .table("job_log")
        .select("*")
        .order("started_at", desc=True)
        .limit(20)
        .execute()
    )
    return res.data
