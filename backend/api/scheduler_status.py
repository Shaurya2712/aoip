# STATUS: COMPLETE
# api/scheduler_status.py
from fastapi import APIRouter, HTTPException
from db import get_db
from scheduler import trigger_job

router = APIRouter()

TRIGGERABLE_JOBS = [
    "keyword_expansion",
    "trend_analysis",
    "playstore_intel",
    "review_mining",
    "community_research",
    "opportunity_scoring",
    "product_concepts",
    "daily_report",
]


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


@router.post("/trigger/{job_name}")
def trigger_job_endpoint(job_name: str):
    """Manually start a scheduler job (runs in background)."""
    if job_name not in TRIGGERABLE_JOBS:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_name}")
    if not trigger_job(job_name):
        raise HTTPException(status_code=503, detail="Scheduler not ready yet")
    return {"status": "queued", "job_name": job_name}
