"""
Arq background task functions.

Each task receives a context dict `ctx` from the arq worker and runs in an
isolated DB session it creates and closes itself.

Start the worker from the backend/ directory:
    arq app.worker.settings.WorkerSettings
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def sync_connector_task(ctx: dict, source_name: str, triggered_by: str = "worker"):
    """
    Background task: run one connector sync, invalidate relevant caches.

    Uses asyncio.to_thread so the synchronous sync_source() call doesn't block
    the arq event loop while other queued jobs can be picked up.
    """
    from app.database import SessionLocal
    from app.services.ingestion_service import sync_source
    from app.services.cache_service import cache_delete_prefix

    db = SessionLocal()
    try:
        result = await asyncio.to_thread(sync_source, source_name, db, triggered_by)
        cache_delete_prefix("integrations:")
        cache_delete_prefix("dashboard:")
        logger.info(
            "sync_connector_task completed: source=%s status=%s rows=%s",
            source_name, result["status"], result.get("rows_ingested"),
        )
        return result
    except Exception:
        logger.exception("sync_connector_task raised for source=%s", source_name)
        raise
    finally:
        db.close()


async def heartbeat_task(ctx: dict):
    """
    Cron task: check data freshness for every connector and store results in Redis.

    Runs every 15 minutes (configured in WorkerSettings) and on worker startup.
    Freshness is defined as time since last successful sync.
    """
    from app.database import SessionLocal
    from app.models.integration import IntegrationSyncRun
    from app.services.cache_service import cache_set
    from app.services.ingestion_service import CONNECTORS

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        for source in CONNECTORS:
            last_run = (
                db.query(IntegrationSyncRun)
                .filter(
                    IntegrationSyncRun.source_name == source,
                    IntegrationSyncRun.status == "success",
                )
                .order_by(IntegrationSyncRun.finished_at.desc())
                .first()
            )
            if last_run and last_run.finished_at:
                finished = last_run.finished_at
                if finished.tzinfo is None:
                    finished = finished.replace(tzinfo=timezone.utc)
                age_hours = (now - finished).total_seconds() / 3600
                status = "healthy" if age_hours < 24 else "stale"
            else:
                age_hours = None
                status = "no_data"

            cache_set(
                f"heartbeat:{source}",
                {
                    "source": source,
                    "status": status,
                    "data_freshness_hours": round(age_hours, 2) if age_hours is not None else None,
                    "checked_at": now.isoformat(),
                },
                ttl=3600,
            )

        logger.info("heartbeat_task: checked %d connectors", len(CONNECTORS))
        return {"checked": len(CONNECTORS), "checked_at": now.isoformat()}
    finally:
        db.close()
