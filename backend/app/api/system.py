"""
System health endpoint — operational status of the async infrastructure.

GET /api/system/status
  Returns Redis connectivity, active sync job count, and worker identity.
  Used by the integrations page system-status bar.

All fields degrade gracefully: if Redis is down, redis = "disconnected" and
active_jobs reflects only the DB view (running IntegrationSyncRun rows).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.integration import IntegrationSyncRun

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
async def system_status(db: Session = Depends(get_db)):
    from app.services import cache_service

    redis_info = cache_service.get_info()

    active_syncs = (
        db.query(IntegrationSyncRun)
        .filter(IntegrationSyncRun.status == "running")
        .count()
    )

    try:
        from app.services.queue_service import get_active_job_count
        queue_depth = await get_active_job_count()
    except Exception:
        queue_depth = -1

    return {
        "redis": "connected" if redis_info["connected"] else "disconnected",
        "redis_version": redis_info.get("version", "unknown"),
        "active_jobs": active_syncs,
        "queue_depth": queue_depth,
        "worker": "arq",
        "worker_command": "arq app.worker.settings.WorkerSettings",
    }
