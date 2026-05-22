from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_admin, get_current_user
from app.database import get_db
from app.models.user import User
from app.services.ingestion_service import sync_source, sync_all, CONNECTORS
from app.models.integration import IntegrationSyncRun
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


@router.post("/sync/{source}", response_model=SyncResponse)
def sync_one(
    source: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if source not in CONNECTORS:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")
    result = sync_source(source, db, triggered_by=current_user.email)
    return result


@router.post("/sync/all/run", response_model=list[SyncResponse])
def sync_all_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return sync_all(db, triggered_by=current_user.email)


@router.get("/status", response_model=list[IntegrationStatus])
def get_status(db: Session = Depends(get_db)):
    statuses = []
    for key, cls in _CONNECTOR_META.items():
        connector = cls()
        last_run = (
            db.query(IntegrationSyncRun)
            .filter(IntegrationSyncRun.source_name == key)
            .order_by(IntegrationSyncRun.started_at.desc())
            .first()
        )
        statuses.append(IntegrationStatus(
            source_name=connector.source_name,
            source_type=connector.source_type,
            connection_mode=f"Mock {connector.source_type.upper()}",
            rows_ingested=last_run.rows_ingested if last_run else 0,
            last_sync=last_run.finished_at if last_run else None,
            status=last_run.status if last_run else "not_synced",
            schema_valid=last_run.schema_valid if last_run else True,
            production_equivalent=connector.production_equivalent,
        ))
    return statuses


@router.get("/history", response_model=list[dict])
def sync_history(limit: int = 50, db: Session = Depends(get_db)):
    """Recent sync runs across all connectors."""
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
            "rows_updated": r.rows_updated,
            "rows_skipped": r.rows_skipped,
            "rows_failed": r.rows_failed,
            "validation_warnings_count": r.validation_warnings_count,
            "schema_valid": r.schema_valid,
            "triggered_by": r.triggered_by,
            "error_message": r.error_message,
        }
        for r in runs
    ]
