"""
Integrations API.

Sync endpoints are now non-blocking: they enqueue an arq background job and
return immediately with {source, job_id, status: "queued"}.  The frontend
live-polls /api/integrations/status (cached 15 s, invalidated by the worker
after each sync) to track progress.

New endpoints added in Phase 5:
  POST /integrations/retry/{run_id}   – re-enqueue a failed sync run
  GET  /integrations/activity         – recent sync event feed
  GET  /integrations/heartbeat        – per-connector data-freshness from Redis
"""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

import logging

from app.core.deps import require_admin, get_current_user
from app.database import get_db
from app.models.user import User
from app.services.ingestion_service import CONNECTORS, sync_source, sync_all
from app.services import cache_service
from app.services.queue_service import enqueue_sync, enqueue_sync_all

logger = logging.getLogger(__name__)
from app.models.integration import IntegrationSyncRun
from app.models.validation_log import IngestionValidationLog
from app.connectors.identity_connector import IdentityConnector
from app.connectors.model_pricing_connector import ModelPricingConnector
from app.connectors.license_connector import LicenseInventoryConnector
from app.connectors.api_gateway_connector import APIGatewayConnector
from app.connectors.browser_extension_connector import BrowserExtensionConnector
from app.connectors.kafka_connector import KafkaTelemetryConnector
from app.connectors.clickhouse_connector import ClickHouseConnector
from app.connectors.kubernetes_connector import KubernetesLogsConnector
from app.connectors.productivity_connector import ProductivityConnector
from app.schemas.common import SyncResponse, IntegrationStatus

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _run_sync_bg(source: str, triggered_by: str) -> None:
    """Run a sync in a FastAPI BackgroundTask (own DB session, no request timeout)."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        sync_source(source, db, triggered_by=triggered_by)
        cache_service.cache_delete_prefix("integrations:")
        cache_service.cache_delete_prefix("dashboard:")
    except Exception as exc:
        logger.error("Background sync failed for %s: %s", source, exc)
    finally:
        db.close()

_CONNECTOR_META = {
    "identity":      IdentityConnector,
    "model_pricing": ModelPricingConnector,
    "licenses":      LicenseInventoryConnector,
    "api_gateway":   APIGatewayConnector,
    "browser":       BrowserExtensionConnector,
    "kafka":         KafkaTelemetryConnector,
    "clickhouse":    ClickHouseConnector,
    "kubernetes":    KubernetesLogsConnector,
    "productivity":  ProductivityConnector,
}


def _compute_health(last_run: IntegrationSyncRun | None, warnings: int) -> str:
    if last_run is None:
        return "not_synced"
    if last_run.status == "running":
        return "syncing"
    if last_run.status == "failed":
        return "failed"
    if warnings > 0:
        return "degraded"
    return "healthy"


# ── sync endpoints (async / non-blocking) ─────────────────────────────────────

@router.post("/sync/{source}", response_model=SyncResponse)
async def sync_one(
    source: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Enqueue a connector sync via arq (returns job_id immediately).
    Falls back to a FastAPI BackgroundTask when Redis / arq is unavailable
    so the HTTP handler returns instantly regardless of dataset size.
    """
    if source not in CONNECTORS:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")
    try:
        job_id = await enqueue_sync(source, triggered_by=current_user.email)
        return SyncResponse(
            source=source,
            job_id=job_id,
            status="queued",
            message=f"Sync queued for {source} — poll /api/tasks/{job_id} for status",
        )
    except Exception as exc:
        logger.warning("Redis unavailable, running %s sync in background task: %s", source, exc)
        background_tasks.add_task(_run_sync_bg, source, current_user.email)
        return SyncResponse(
            source=source,
            status="running",
            message=f"Sync started for {source} — refresh integrations page in ~30s",
        )


@router.post("/sync/all/run", response_model=list[SyncResponse])
async def sync_all_sources(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Enqueue all 9 connector syncs.
    Falls back to FastAPI BackgroundTasks when Redis / arq is unavailable.
    """
    try:
        results = await enqueue_sync_all(triggered_by=current_user.email)
        return [
            SyncResponse(
                source=r["source"],
                job_id=r["job_id"],
                status="queued",
                message=f"Queued — poll /api/tasks/{r['job_id']}",
            )
            for r in results
        ]
    except Exception as exc:
        logger.warning("Redis unavailable, queuing all syncs as background tasks: %s", exc)
        responses = []
        for source in CONNECTORS:
            background_tasks.add_task(_run_sync_bg, source, current_user.email)
            responses.append(SyncResponse(
                source=source,
                status="running",
                message=f"Sync started for {source}",
            ))
        return responses


@router.post("/retry/{run_id}", response_model=SyncResponse)
async def retry_sync(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Re-enqueue a failed sync run by its IntegrationSyncRun ID."""
    run = db.query(IntegrationSyncRun).filter(IntegrationSyncRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    if run.status != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Run {run_id} has status '{run.status}'; only failed runs can be retried",
        )
    try:
        job_id = await enqueue_sync(run.source_name, triggered_by=current_user.email)
        return SyncResponse(
            source=run.source_name,
            job_id=job_id,
            status="queued",
            message=f"Retry queued for {run.source_name} — poll /api/tasks/{job_id}",
        )
    except Exception as exc:
        logger.warning("Redis unavailable, running retry synchronously: %s", exc)
        result = sync_source(run.source_name, db, triggered_by=current_user.email)
        return SyncResponse(**result)


# ── read endpoints ─────────────────────────────────────────────────────────────

@router.get("/status", response_model=list[IntegrationStatus])
def get_status(db: Session = Depends(get_db)):
    """Per-connector health + observability metrics. Cached for 15 s."""
    cached = cache_service.cache_get("integrations:status")
    if cached:
        return cached

    statuses = []
    for key, cls in _CONNECTOR_META.items():
        connector = cls()

        last_run = (
            db.query(IntegrationSyncRun)
            .filter(IntegrationSyncRun.source_name == key)
            .order_by(IntegrationSyncRun.started_at.desc())
            .first()
        )
        last_success = (
            db.query(IntegrationSyncRun)
            .filter(IntegrationSyncRun.source_name == key, IntegrationSyncRun.status == "success")
            .order_by(IntegrationSyncRun.finished_at.desc())
            .first()
        )
        last_failed = (
            db.query(IntegrationSyncRun)
            .filter(IntegrationSyncRun.source_name == key, IntegrationSyncRun.status == "failed")
            .order_by(IntegrationSyncRun.finished_at.desc())
            .first()
        )
        warnings = (
            db.query(func.count(IngestionValidationLog.id))
            .filter(IngestionValidationLog.run_id == last_run.id)
            .scalar() or 0
        ) if last_run else 0

        health = _compute_health(last_run, warnings)

        statuses.append(IntegrationStatus(
            source_name=connector.source_name,
            source_type=connector.source_type,
            connection_mode=f"Mock {connector.source_type.upper()}",
            rows_ingested=last_run.rows_ingested if last_run else 0,
            rows_skipped=last_run.rows_skipped if last_run else 0,
            last_sync=last_run.finished_at if last_run else None,
            last_sync_success=last_success.finished_at if last_success else None,
            last_sync_failed=last_failed.finished_at if last_failed else None,
            last_duration_ms=last_run.duration_ms if last_run else 0,
            validation_warnings=warnings,
            watermark_since=last_run.watermark_since if last_run else None,
            health=health,
            status=last_run.status if last_run else "not_synced",
            schema_valid=last_run.schema_valid if last_run else True,
            production_equivalent=connector.production_equivalent,
        ))

    serialised = [s.model_dump(mode="json") for s in statuses]
    cache_service.cache_set("integrations:status", serialised, ttl=15)
    return statuses


@router.get("/activity")
def activity_feed(
    limit: int = Query(default=20, le=100),
    source: str | None = Query(default=None, description="Filter by connector name"),
    db: Session = Depends(get_db),
):
    """Recent sync run events as an activity stream, newest first."""
    q = db.query(IntegrationSyncRun).order_by(IntegrationSyncRun.started_at.desc())
    if source:
        q = q.filter(IntegrationSyncRun.source_name == source)
    runs = q.limit(limit).all()
    return [
        {
            "id": r.id,
            "source_name": r.source_name,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_ms": r.duration_ms,
            "rows_ingested": r.rows_ingested,
            "rows_skipped": r.rows_skipped,
            "validation_warnings_count": r.validation_warnings_count,
            "triggered_by": r.triggered_by,
            "error_message": r.error_message,
        }
        for r in runs
    ]


@router.get("/heartbeat")
def get_heartbeat(db: Session = Depends(get_db)):
    """
    Per-connector data-freshness snapshot.

    Reads from Redis heartbeat cache when available (populated by the arq cron
    task every 15 min).  Falls back to a live DB query so the endpoint always
    returns fresh data even before the first heartbeat cron run.
    """
    now = datetime.now(timezone.utc)
    result: dict = {}

    for source in CONNECTORS:
        cached = cache_service.cache_get(f"heartbeat:{source}")
        if cached:
            result[source] = cached
            continue

        # DB fallback
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

        result[source] = {
            "source": source,
            "status": status,
            "data_freshness_hours": round(age_hours, 2) if age_hours is not None else None,
            "checked_at": None,
        }

    return result


@router.get("/validation-logs", response_model=list[dict])
def validation_logs(
    connector: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(IngestionValidationLog).order_by(IngestionValidationLog.created_at.desc())
    if connector:
        q = q.filter(IngestionValidationLog.connector_name == connector)
    logs = q.limit(min(limit, 500)).all()
    return [
        {
            "id": l.id,
            "created_at": l.created_at.isoformat(),
            "run_id": l.run_id,
            "connector_name": l.connector_name,
            "row_number": l.row_number,
            "field_name": l.field_name,
            "error_type": l.error_type,
            "raw_value": l.raw_value,
            "error_message": l.error_message,
        }
        for l in logs
    ]


@router.get("/history", response_model=list[dict])
def sync_history(limit: int = 50, db: Session = Depends(get_db)):
    runs = (
        db.query(IntegrationSyncRun)
        .order_by(IntegrationSyncRun.started_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        {
            "id": r.id,
            "source_name": r.source_name,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_ms": r.duration_ms,
            "rows_ingested": r.rows_ingested,
            "rows_skipped": r.rows_skipped,
            "rows_updated": r.rows_updated,
            "rows_failed": r.rows_failed,
            "validation_warnings_count": r.validation_warnings_count,
            "watermark_since": r.watermark_since.isoformat() if r.watermark_since else None,
            "schema_valid": r.schema_valid,
            "triggered_by": r.triggered_by,
            "error_message": r.error_message,
        }
        for r in runs
    ]
