from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ingestion_service import sync_source, sync_all, CONNECTORS
from app.models.integration import IntegrationSyncRun
from app.connectors.identity_connector import IdentityConnector
from app.connectors.model_pricing_connector import ModelPricingConnector
from app.connectors.license_connector import LicenseInventoryConnector
from app.connectors.api_gateway_connector import APIGatewayConnector
from app.schemas.common import SyncResponse, IntegrationStatus

router = APIRouter(prefix="/integrations", tags=["integrations"])

_CONNECTOR_META = {
    "identity":      IdentityConnector,
    "model_pricing": ModelPricingConnector,
    "licenses":      LicenseInventoryConnector,
    "api_gateway":   APIGatewayConnector,
}


@router.post("/sync/{source}", response_model=SyncResponse)
def sync_one(source: str, db: Session = Depends(get_db)):
    if source not in CONNECTORS:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")
    result = sync_source(source, db)
    return result


@router.post("/sync/all/run", response_model=list[SyncResponse])
def sync_all_sources(db: Session = Depends(get_db)):
    return sync_all(db)


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
