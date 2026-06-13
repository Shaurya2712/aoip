# STATUS: COMPLETE
# scheduler.py
import threading
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from db import get_db
from job_exceptions import JobSkipped

logger = logging.getLogger(__name__)
_job_lock = threading.Lock()


def log_job(job_name: str, status: str, message: str = "", started_at: datetime = None, finished_at: datetime = None):
    """Write a job run entry to the job_log table."""
    try:
        row = {
            "job_name": job_name,
            "status": status,
            "message": message[:500] if message else "",
        }
        if started_at:
            row["started_at"] = started_at.isoformat()
        if finished_at:
            row["finished_at"] = finished_at.isoformat()
        get_db().table("job_log").insert(row).execute()
    except Exception as e:
        logger.error(f"Failed to log job: {e}")


def run_job(job_name: str, coro_factory):
    """
    Acquires the global lock and runs a coroutine.
    Only one job runs at a time — no parallel scraping.
    """
    if not _job_lock.acquire(blocking=False):
        logger.info(f"Skipping {job_name} — another job is running")
        return
    started = datetime.utcnow()
    log_job(job_name, "running", "started", started_at=started)
    try:
        asyncio.run(coro_factory())
        finished = datetime.utcnow()
        log_job(job_name, "success", "completed", started_at=started, finished_at=finished)
    except JobSkipped as e:
        finished = datetime.utcnow()
        logger.info(f"Job {job_name} skipped: {e.reason}")
        log_job(job_name, "success", f"skipped: {e.reason}", started_at=started, finished_at=finished)
    except Exception as e:
        finished = datetime.utcnow()
        logger.error(f"Job {job_name} failed: {e}")
        log_job(job_name, "error", str(e), started_at=started, finished_at=finished)
    finally:
        _job_lock.release()


def start_scheduler():
    from modules.m2_keyword import run as m2_run
    from modules.m3_trends import run as m3_run
    from modules.m4_playstore import run as m4_run
    from modules.m5_reviews import run as m5_run
    from modules.m6_community import run as m6_run
    from modules.m7_scoring import run as m7_run
    from modules.m8_analyst import run as m8_run
    from modules.m9_reports import generate_daily

    s = BackgroundScheduler(timezone="Asia/Kolkata")

    # Every 6 hours: expand keywords and score trends
    s.add_job(
        lambda: run_job("keyword_expansion", m2_run),
        IntervalTrigger(hours=6),
        id="keyword_expansion",
        next_run_time=datetime.now()  # Run immediately on startup
    )

    # Every 6 hours offset by 1h: Google Trends scoring
    s.add_job(
        lambda: run_job("trend_analysis", m3_run),
        IntervalTrigger(hours=6),
        id="trend_analysis"
    )

    # Every 4 hours: Play Store competitor data
    s.add_job(
        lambda: run_job("playstore_intel", m4_run),
        IntervalTrigger(hours=4),
        id="playstore_intel"
    )

    # Every 8 hours: Mine reviews from competitors
    s.add_job(
        lambda: run_job("review_mining", m5_run),
        IntervalTrigger(hours=8),
        id="review_mining"
    )

    # Every 8 hours: Reddit community research
    s.add_job(
        lambda: run_job("community_research", m6_run),
        IntervalTrigger(hours=8),
        id="community_research"
    )

    # Every 12 hours: Rescore all opportunities
    s.add_job(
        lambda: run_job("opportunity_scoring", m7_run),
        IntervalTrigger(hours=12),
        id="opportunity_scoring"
    )

    # Daily at 2am IST: Generate product concepts for top 20
    s.add_job(
        lambda: run_job("product_concepts", m8_run),
        CronTrigger(hour=2, minute=0, timezone="Asia/Kolkata"),
        id="product_concepts"
    )

    # Daily at 3am IST: Generate daily report
    s.add_job(
        lambda: run_job("daily_report", generate_daily),
        CronTrigger(hour=3, minute=0, timezone="Asia/Kolkata"),
        id="daily_report"
    )

    s.start()
    logger.info("APScheduler started. All jobs registered.")
