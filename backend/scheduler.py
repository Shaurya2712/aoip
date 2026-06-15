# STATUS: COMPLETE
# scheduler.py
import threading
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from db import get_db
from job_exceptions import JobSkipped

logger = logging.getLogger(__name__)
_job_lock = threading.Lock()
IST = ZoneInfo("Asia/Kolkata")

# Populated by start_scheduler(); used for manual triggers
JOB_REGISTRY: dict = {}


def log_job_start(job_name: str, started_at: datetime) -> str | None:
    """Insert a running row; returns its id for completion update."""
    try:
        res = (
            get_db()
            .table("job_log")
            .insert(
                {
                    "job_name": job_name,
                    "status": "running",
                    "message": "started",
                    "started_at": started_at.isoformat(),
                }
            )
            .execute()
        )
        return res.data[0]["id"] if res.data else None
    except Exception as e:
        logger.error(f"Failed to log job start: {e}")
        return None


def log_job_finish(
    log_id: str | None,
    status: str,
    message: str,
    finished_at: datetime,
):
    """Update the running row so the dashboard shows one row per run."""
    if not log_id:
        return
    try:
        get_db().table("job_log").update(
            {
                "status": status,
                "message": message[:500] if message else "",
                "finished_at": finished_at.isoformat(),
            }
        ).eq("id", log_id).execute()
    except Exception as e:
        logger.error(f"Failed to log job finish: {e}")


def run_job(job_name: str, coro_factory):
    """
    Acquires the global lock and runs a coroutine.
    Only one job runs at a time — no parallel scraping.
    """
    if not _job_lock.acquire(blocking=False):
        logger.info(f"Skipping {job_name} — another job is running")
        return
    started = datetime.utcnow()
    log_id = log_job_start(job_name, started)
    try:
        asyncio.run(coro_factory())
        finished = datetime.utcnow()
        log_job_finish(log_id, "success", "completed", finished)
    except JobSkipped as e:
        finished = datetime.utcnow()
        logger.info(f"Job {job_name} skipped: {e.reason}")
        log_job_finish(log_id, "success", f"skipped: {e.reason}", finished)
    except Exception as e:
        finished = datetime.utcnow()
        logger.error(f"Job {job_name} failed: {e}")
        log_job_finish(log_id, "error", str(e), finished)
    finally:
        _job_lock.release()


def _run_job_async(job_name: str, coro_factory):
    """Run a job in a background thread (non-blocking for API / startup)."""
    threading.Thread(
        target=lambda: run_job(job_name, coro_factory),
        daemon=True,
        name=f"aoip-job-{job_name}",
    ).start()


def trigger_job(job_name: str) -> bool:
    """Manually queue a scheduled job. Returns False if job_name is unknown."""
    if job_name not in JOB_REGISTRY:
        return False
    _run_job_async(job_name, JOB_REGISTRY[job_name])
    return True


def start_scheduler():
    from modules.m2_keyword import run as m2_run
    from modules.m3_trends import run as m3_run
    from modules.m4_playstore import run as m4_run
    from modules.m5_reviews import run as m5_run
    from modules.m6_community import run as m6_run
    from modules.m7_scoring import run as m7_run
    from modules.m8_analyst import run as m8_run
    from modules.m9_reports import generate_daily

    global JOB_REGISTRY
    JOB_REGISTRY = {
        "keyword_expansion": m2_run,
        "trend_analysis": m3_run,
        "playstore_intel": m4_run,
        "review_mining": m5_run,
        "community_research": m6_run,
        "opportunity_scoring": m7_run,
        "product_concepts": m8_run,
        "daily_report": generate_daily,
    }

    s = BackgroundScheduler(timezone=IST, job_defaults={"max_instances": 1, "coalesce": True})

    # Every 6 hours: expand keywords (capped per run — see M2_MAX_BATCHES_PER_RUN)
    s.add_job(
        lambda: run_job("keyword_expansion", m2_run),
        IntervalTrigger(hours=6),
        id="keyword_expansion",
        max_instances=1,
    )

    # Every 6 hours: Google Trends scoring
    s.add_job(
        lambda: run_job("trend_analysis", m3_run),
        IntervalTrigger(hours=6),
        id="trend_analysis",
        max_instances=1,
    )

    # Every 4 hours: Play Store competitor data
    s.add_job(
        lambda: run_job("playstore_intel", m4_run),
        IntervalTrigger(hours=4),
        id="playstore_intel",
        max_instances=1,
    )

    # Every 8 hours: Mine reviews from competitors
    s.add_job(
        lambda: run_job("review_mining", m5_run),
        IntervalTrigger(hours=8),
        id="review_mining",
        max_instances=1,
    )

    # Every 8 hours: Reddit community research
    s.add_job(
        lambda: run_job("community_research", m6_run),
        IntervalTrigger(hours=8),
        id="community_research",
        max_instances=1,
    )

    # Every 12 hours: Rescore opportunities
    s.add_job(
        lambda: run_job("opportunity_scoring", m7_run),
        IntervalTrigger(hours=12),
        id="opportunity_scoring",
        max_instances=1,
    )

    # Daily at 2am IST: Generate product concepts for top 20
    s.add_job(
        lambda: run_job("product_concepts", m8_run),
        CronTrigger(hour=2, minute=0, timezone="Asia/Kolkata"),
        id="product_concepts",
        max_instances=1,
    )

    # Daily at 3am IST: Generate daily report
    s.add_job(
        lambda: run_job("daily_report", generate_daily),
        CronTrigger(hour=3, minute=0, timezone="Asia/Kolkata"),
        id="daily_report",
        max_instances=1,
    )

    s.start()
    logger.info("APScheduler started. All jobs registered.")
