# STATUS: COMPLETE
# scheduler.py
import threading
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from db import get_db
from job_exceptions import JobSkipped
from config import (
    SCHEDULER_M2_INTERVAL_MIN,
    SCHEDULER_M3_INTERVAL_MIN,
    SCHEDULER_M4_INTERVAL_MIN,
    SCHEDULER_M5_INTERVAL_MIN,
    SCHEDULER_M6_INTERVAL_MIN,
    SCHEDULER_M7_INTERVAL_MIN,
    SCHEDULER_PIPELINE_CHAIN,
    SCHEDULER_PIPELINE_INTERVAL_MIN,
)

logger = logging.getLogger(__name__)
_job_lock = threading.Lock()
IST = ZoneInfo("Asia/Kolkata")

# Populated by start_scheduler(); used for manual triggers
JOB_REGISTRY: dict = {}
SCHEDULE_INFO: dict = {}


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
        logger.warning(f"Skipping {job_name} — another job is running")
        started = datetime.utcnow()
        log_id = log_job_start(job_name, started)
        log_job_finish(
            log_id,
            "error",
            "skipped: another job is already running",
            datetime.utcnow(),
        )
        return
    started = datetime.utcnow()
    log_id = log_job_start(job_name, started)
    try:
        summary = asyncio.run(coro_factory())
        finished = datetime.utcnow()
        message = summary if isinstance(summary, str) and summary else "completed"
        log_job_finish(log_id, "success", message, finished)
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


def get_schedule_info() -> dict:
    """Expose current scheduler intervals for the dashboard."""
    return dict(SCHEDULE_INFO)


async def _run_pipeline_chain(m3_run, m4_run, m7_run) -> str:
    """Run m3 → m4 → m7 sequentially in one lock slot."""
    parts: list[str] = []
    for step_name, fn in (
        ("m3", m3_run),
        ("m4", m4_run),
        ("m7", m7_run),
    ):
        try:
            summary = await fn()
            parts.append(f"{step_name}: {summary or 'ok'}")
        except Exception as e:
            logger.error(f"Pipeline step {step_name} failed: {e}")
            parts.append(f"{step_name}: error")
    return " | ".join(parts)


def _add_interval_job(
    scheduler: BackgroundScheduler,
    job_id: str,
    coro_factory,
    interval_min: int,
    stagger_min: int,
):
    """Register an interval job with a staggered first run to avoid pile-ups."""
    first_run = datetime.now(IST) + timedelta(minutes=stagger_min)
    scheduler.add_job(
        lambda j=job_id, c=coro_factory: run_job(j, c),
        IntervalTrigger(minutes=interval_min, timezone=IST),
        id=job_id,
        max_instances=1,
        next_run_time=first_run,
    )
    SCHEDULE_INFO[job_id] = {"interval_minutes": interval_min, "first_run_stagger_min": stagger_min}


def start_scheduler():
    from modules.m2_keyword import run as m2_run
    from modules.m3_trends import run as m3_run
    from modules.m4_playstore import run as m4_run
    from modules.m5_reviews import run as m5_run
    from modules.m6_community import run as m6_run
    from modules.m7_scoring import run as m7_run
    from modules.m8_analyst import run as m8_run
    from modules.m9_reports import generate_daily

    async def pipeline_chain():
        return await _run_pipeline_chain(m3_run, m4_run, m7_run)

    global JOB_REGISTRY, SCHEDULE_INFO
    JOB_REGISTRY = {
        "keyword_expansion": m2_run,
        "trend_analysis": m3_run,
        "playstore_intel": m4_run,
        "review_mining": m5_run,
        "community_research": m6_run,
        "opportunity_scoring": m7_run,
        "product_concepts": m8_run,
        "daily_report": generate_daily,
        "pipeline_cycle": pipeline_chain,
    }
    SCHEDULE_INFO = {
        "pipeline_chain_enabled": SCHEDULER_PIPELINE_CHAIN,
        "pipeline_interval_minutes": SCHEDULER_PIPELINE_INTERVAL_MIN,
    }

    s = BackgroundScheduler(timezone=IST, job_defaults={"max_instances": 1, "coalesce": True})

    _add_interval_job(s, "keyword_expansion", m2_run, SCHEDULER_M2_INTERVAL_MIN, stagger_min=5)

    if SCHEDULER_PIPELINE_CHAIN:
        _add_interval_job(
            s,
            "pipeline_cycle",
            pipeline_chain,
            SCHEDULER_PIPELINE_INTERVAL_MIN,
            stagger_min=10,
        )
        logger.info(
            "Pipeline chain enabled: m3→m4→m7 every %s min (individual m3/m4/m7 timers off)",
            SCHEDULER_PIPELINE_INTERVAL_MIN,
        )
    else:
        _add_interval_job(s, "trend_analysis", m3_run, SCHEDULER_M3_INTERVAL_MIN, stagger_min=10)
        _add_interval_job(s, "playstore_intel", m4_run, SCHEDULER_M4_INTERVAL_MIN, stagger_min=20)
        _add_interval_job(
            s,
            "opportunity_scoring",
            m7_run,
            SCHEDULER_M7_INTERVAL_MIN,
            stagger_min=30,
        )

    _add_interval_job(s, "review_mining", m5_run, SCHEDULER_M5_INTERVAL_MIN, stagger_min=40)
    _add_interval_job(s, "community_research", m6_run, SCHEDULER_M6_INTERVAL_MIN, stagger_min=50)

    # Daily at 2am IST: product concepts for top opportunities
    s.add_job(
        lambda: run_job("product_concepts", m8_run),
        CronTrigger(hour=2, minute=0, timezone=IST),
        id="product_concepts",
        max_instances=1,
    )
    SCHEDULE_INFO["product_concepts"] = {"cron": "daily 02:00 IST"}

    # Daily at 3am IST: daily report
    s.add_job(
        lambda: run_job("daily_report", generate_daily),
        CronTrigger(hour=3, minute=0, timezone=IST),
        id="daily_report",
        max_instances=1,
    )
    SCHEDULE_INFO["daily_report"] = {"cron": "daily 03:00 IST"}

    s.start()
    logger.info(
        "APScheduler started. pipeline_chain=%s m3=%sm m4=%sm m7=%sm",
        SCHEDULER_PIPELINE_CHAIN,
        SCHEDULER_M3_INTERVAL_MIN,
        SCHEDULER_M4_INTERVAL_MIN,
        SCHEDULER_M7_INTERVAL_MIN,
    )
