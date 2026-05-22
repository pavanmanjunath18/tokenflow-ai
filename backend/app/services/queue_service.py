"""
Arq job queue helpers.

All async — call with `await` from async FastAPI route handlers.
Raises on Redis connection failure (let the HTTP layer return a 503).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _redis_settings():
    from arq.connections import RedisSettings
    from app.config import settings
    url = settings.redis_url
    # Upstash and other managed services use rediss:// (TLS).
    # arq's RedisSettings.from_dsn doesn't recognise "rediss://" natively,
    # so strip the extra 's' and pass ssl=True explicitly.
    if url.startswith("rediss://"):
        return RedisSettings.from_dsn(url.replace("rediss://", "redis://", 1), ssl=True)
    return RedisSettings.from_dsn(url)


async def enqueue_sync(source_name: str, triggered_by: str = "system") -> str:
    """Enqueue a single connector sync; returns the arq job ID."""
    from arq import create_pool
    pool = await create_pool(_redis_settings())
    job = await pool.enqueue_job("sync_connector_task", source_name, triggered_by)
    await pool.aclose()
    return job.job_id


async def enqueue_sync_all(triggered_by: str = "system") -> list[dict]:
    """Enqueue all 9 connectors; returns [{source, job_id}]."""
    from arq import create_pool
    from app.services.ingestion_service import CONNECTORS
    pool = await create_pool(_redis_settings())
    results = []
    for source in CONNECTORS:
        job = await pool.enqueue_job("sync_connector_task", source, triggered_by)
        results.append({"source": source, "job_id": job.job_id})
    await pool.aclose()
    return results


async def get_job_status(job_id: str) -> dict[str, Any]:
    """Look up an arq job by ID and return its current state."""
    from arq import create_pool
    from arq.jobs import Job
    pool = await create_pool(_redis_settings())
    job = Job(job_id, pool)
    status = await job.status()
    try:
        info = await job.info()
    except Exception:
        info = None
    await pool.aclose()
    return {
        "job_id": job_id,
        "status": status.value if status else "not_found",
        "enqueue_time": info.enqueue_time.isoformat() if info and info.enqueue_time else None,
        "start_time": info.start_time.isoformat() if info and info.start_time else None,
        "finish_time": info.finish_time.isoformat() if info and info.finish_time else None,
        "result": info.result if info else None,
    }


async def get_active_job_count() -> int:
    """Count queued + in-progress arq jobs (best-effort; returns -1 on error)."""
    from arq import create_pool
    try:
        pool = await create_pool(_redis_settings())
        queued = await pool.zcard("arq:queue")
        in_prog = await pool.zcard("arq:in-progress")
        await pool.aclose()
        return int(queued) + int(in_prog)
    except Exception:
        return -1
