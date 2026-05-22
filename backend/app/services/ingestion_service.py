"""
Connector sync → DB.

Source ownership:
  api_gateway  → ai_usage_events  (primary analytics source, full replace)
  identity     → employees        (full replace)
  model_pricing→ model_pricing    (full replace)
  licenses     → ai_licenses      (full replace)
  browser      → browser_events   (full replace)
  kubernetes   → kubernetes_logs  (full replace)
  kafka        → kafka_events     (supplemental — does NOT write to usage_events)
  clickhouse   → clickhouse_aggregates (supplemental — pre-aggregated, NOT in usage_events)
  productivity → no DB write for now (schema verified, row count returned)

Kafka and ClickHouse are treated as supplemental/validation connectors.
They contain data derived from the same api_gateway traces, so loading them
into ai_usage_events would double- or triple-count spend. In production,
you would pick ONE authoritative source per analytical domain.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.connectors.identity_connector import IdentityConnector
from app.connectors.model_pricing_connector import ModelPricingConnector
from app.connectors.license_connector import LicenseInventoryConnector
from app.connectors.api_gateway_connector import APIGatewayConnector
from app.connectors.browser_extension_connector import BrowserExtensionConnector
from app.connectors.kafka_connector import KafkaTelemetryConnector
from app.connectors.clickhouse_connector import ClickHouseConnector
from app.connectors.kubernetes_connector import KubernetesLogsConnector
from app.connectors.productivity_connector import ProductivityConnector

from app.models.employee import Employee
from app.models.model_pricing import ModelPricing
from app.models.license import AILicense
from app.models.usage_event import AIUsageEvent
from app.models.browser_event import BrowserEvent
from app.models.kubernetes_log import KubernetesLog
from app.models.kafka_event import KafkaEvent
from app.models.clickhouse_aggregate import ClickHouseAggregate
from app.models.integration import IntegrationSyncRun
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

CONNECTORS = {
    "identity":     IdentityConnector,
    "model_pricing": ModelPricingConnector,
    "licenses":     LicenseInventoryConnector,
    "api_gateway":  APIGatewayConnector,
    "browser":      BrowserExtensionConnector,
    "kafka":        KafkaTelemetryConnector,
    "clickhouse":   ClickHouseConnector,
    "kubernetes":   KubernetesLogsConnector,
    "productivity": ProductivityConnector,
}


def sync_source(source: str, db: Session) -> dict:
    if source not in CONNECTORS:
        raise ValueError(f"Unknown source: {source}. Available: {list(CONNECTORS)}")

    run = IntegrationSyncRun(source_name=source, started_at=datetime.utcnow())
    db.add(run)
    db.flush()

    try:
        connector = CONNECTORS[source]()
        rows, errors = connector.sync()

        if errors:
            logger.warning("Schema warnings for %s: %s", source, errors)
            run.schema_valid = False

        ingested = _load(source, rows, db)
        run.rows_ingested = ingested
        run.status = "success"
        run.finished_at = datetime.utcnow()

        db.add(AuditLog(
            action="integration_sync",
            resource_type="integration",
            resource_id=source,
            details=f"Ingested {ingested} rows",
        ))
        db.commit()
        return {"source": source, "rows_ingested": ingested, "rows_failed": 0,
                "status": "success", "message": f"Synced {ingested} rows"}

    except Exception as exc:
        db.rollback()
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.utcnow()
        db.add(run)
        db.commit()
        logger.exception("Sync failed for %s", source)
        return {"source": source, "rows_ingested": 0, "rows_failed": 0,
                "status": "failed", "message": str(exc)}


def sync_all(db: Session) -> list[dict]:
    return [sync_source(s, db) for s in CONNECTORS]


# ── loaders ───────────────────────────────────────────────────────────────────

def _load(source: str, rows: list[dict], db: Session) -> int:
    loaders = {
        "identity":     _load_employees,
        "model_pricing": _load_model_pricing,
        "licenses":     _load_licenses,
        "api_gateway":  _load_api_gateway_events,  # primary analytics source
        "browser":      _load_browser_events,
        "kafka":        _load_kafka_events,          # own table, not usage_events
        "clickhouse":   _load_clickhouse_aggregates, # own table, not usage_events
        "kubernetes":   _load_kubernetes_logs,
        "productivity": _load_ignore,
    }
    return loaders[source](rows, db)


def _load_employees(rows, db):
    db.query(Employee).delete()
    db.bulk_insert_mappings(Employee, rows)
    return len(rows)


def _load_model_pricing(rows, db):
    db.query(ModelPricing).delete()
    db.bulk_insert_mappings(ModelPricing, rows)
    return len(rows)


def _load_licenses(rows, db):
    db.query(AILicense).delete()
    db.bulk_insert_mappings(AILicense, rows)
    return len(rows)


def _load_api_gateway_events(rows, db):
    # Full replace — api_gateway is the single source of truth for usage_events
    db.query(AIUsageEvent).delete()
    _batch_insert(db, AIUsageEvent, rows)
    return len(rows)


def _load_browser_events(rows, db):
    db.query(BrowserEvent).delete()
    _batch_insert(db, BrowserEvent, rows)
    return len(rows)


def _load_kafka_events(rows, db):
    """Store in kafka_events table — separate from usage_events to avoid double-counting."""
    db.query(KafkaEvent).delete()
    # Kafka connector normalises to usage_event shape; remap to kafka_event shape
    kafka_rows = [
        {
            "trace_id":    r["trace_id"],
            "timestamp":   r["timestamp"],
            "employee_id": r["employee_id"],
            "department":  r["department"],
            "provider":    r["provider"],
            "model_name":  r["model_name"],
            "input_tokens":  r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "cost_usd":    r["cost_usd"],
            "latency_ms":  r["latency_ms"],
            "cache_hit":   r["cache_hit"],
            "policy_result": "allowed" if r.get("request_allowed", True) else "blocked",
        }
        for r in rows
    ]
    _batch_insert(db, KafkaEvent, kafka_rows)
    return len(kafka_rows)


def _load_clickhouse_aggregates(rows, db):
    """Store in clickhouse_aggregates table — pre-aggregated, not raw events."""
    db.query(ClickHouseAggregate).delete()
    # Clickhouse connector normalises to usage_event shape; remap to aggregate shape
    ch_rows = []
    for r in rows:
        d = r.get("timestamp")
        date_val = d.date() if hasattr(d, "date") else None
        ch_rows.append({
            "agg_id":        r["trace_id"],
            "date":          date_val,
            "employee_id":   r["employee_id"],
            "department":    r["department"],
            "provider":      r["provider"],
            "model_name":    r["model_name"],
            "request_count": 1,  # each row is already one aggregated record
            "input_tokens":  r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "total_tokens":  r["total_tokens"],
            "cost_usd":      r["cost_usd"],
            "avg_latency_ms": r["latency_ms"],
            "cache_hit_count": 1 if r.get("cache_hit") else 0,
            "cache_hit_rate": 1.0 if r.get("cache_hit") else 0.0,
        })
    _batch_insert(db, ClickHouseAggregate, ch_rows)
    return len(ch_rows)


def _load_kubernetes_logs(rows, db):
    db.query(KubernetesLog).delete()
    _batch_insert(db, KubernetesLog, rows)
    return len(rows)


def _load_ignore(rows, db):
    return len(rows)


def _batch_insert(db, model, rows, batch_size=5_000):
    for i in range(0, len(rows), batch_size):
        db.bulk_insert_mappings(model, rows[i: i + batch_size])
        db.flush()
