"""
Connector sync → DB using transactional UPSERT.

Source ownership (each source owns its table exclusively):
  api_gateway  → ai_usage_events       (authoritative analytics source)
  identity     → employees
  model_pricing→ model_pricing
  licenses     → ai_licenses
  browser      → browser_events
  kafka        → kafka_events           (supplemental, NOT usage_events)
  clickhouse   → clickhouse_aggregates  (supplemental, pre-aggregated)
  kubernetes   → kubernetes_logs
  productivity → (no DB table yet — schema verified, count returned)

Ingestion pattern: UPSERT using PostgreSQL ON CONFLICT DO UPDATE.
  - No table is ever truncated
  - Re-syncing the same data is idempotent
  - Failed syncs leave existing data intact
  - Watermark: sync run records started_at / finished_at for history
"""

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
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


def sync_source(source: str, db: Session, triggered_by: str = "system") -> dict:
    if source not in CONNECTORS:
        raise ValueError(f"Unknown source: {source}. Available: {list(CONNECTORS)}")

    run = IntegrationSyncRun(
        source_name=source,
        started_at=datetime.now(timezone.utc),
        triggered_by=triggered_by,
    )
    db.add(run)
    db.flush()

    t_start = time.monotonic()
    try:
        connector = CONNECTORS[source]()
        rows, errors = connector.sync()

        warning_count = len(errors)
        if errors:
            logger.warning("Schema warnings for %s: %s", source, errors)
            run.schema_valid = False

        ingested = _load(source, rows, db)

        run.rows_ingested = ingested
        run.validation_warnings_count = warning_count
        run.status = "success"
        run.finished_at = datetime.now(timezone.utc)
        run.duration_ms = int((time.monotonic() - t_start) * 1000)

        db.add(AuditLog(
            action="integration_sync",
            resource_type="integration",
            resource_id=source,
            actor=triggered_by,
            actor_email=triggered_by,
            details=f"Upserted {ingested} rows via {connector.source_type} connector",
        ))
        db.commit()
        return {
            "source": source,
            "rows_ingested": ingested,
            "rows_failed": 0,
            "status": "success",
            "message": f"Upserted {ingested} rows in {run.duration_ms}ms",
        }

    except Exception as exc:
        db.rollback()
        run.status = "failed"
        run.error_message = str(exc)[:500]
        run.finished_at = datetime.now(timezone.utc)
        run.duration_ms = int((time.monotonic() - t_start) * 1000)
        db.add(run)
        db.commit()
        logger.exception("Sync failed for %s", source)
        return {
            "source": source,
            "rows_ingested": 0,
            "rows_failed": 0,
            "status": "failed",
            "message": str(exc),
        }


def sync_all(db: Session, triggered_by: str = "system") -> list[dict]:
    return [sync_source(s, db, triggered_by=triggered_by) for s in CONNECTORS]


# ── loaders ───────────────────────────────────────────────────────────────────

def _load(source: str, rows: list[dict], db: Session) -> int:
    loaders = {
        "identity":      _load_employees,
        "model_pricing": _load_model_pricing,
        "licenses":      _load_licenses,
        "api_gateway":   _load_api_gateway_events,
        "browser":       _load_browser_events,
        "kafka":         _load_kafka_events,
        "clickhouse":    _load_clickhouse_aggregates,
        "kubernetes":    _load_kubernetes_logs,
        "productivity":  _load_ignore,
    }
    return loaders[source](rows, db)


def _load_employees(rows, db):
    return _upsert_batch(db, Employee, rows, conflict_col="employee_id")


def _load_model_pricing(rows, db):
    return _upsert_batch(db, ModelPricing, rows, conflict_col="model_name")


def _load_licenses(rows, db):
    return _upsert_batch(db, AILicense, rows, conflict_col="license_id")


def _load_api_gateway_events(rows, db):
    return _upsert_batch(db, AIUsageEvent, rows, conflict_col="trace_id")


def _load_browser_events(rows, db):
    return _upsert_batch(db, BrowserEvent, rows, conflict_col="event_id")


def _load_kafka_events(rows, db):
    kafka_rows = [
        {
            "trace_id":      r["trace_id"],
            "timestamp":     r["timestamp"],
            "employee_id":   r["employee_id"],
            "department":    r["department"],
            "provider":      r["provider"],
            "model_name":    r["model_name"],
            "input_tokens":  r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "cost_usd":      r["cost_usd"],
            "latency_ms":    r["latency_ms"],
            "cache_hit":     r["cache_hit"],
            "policy_result": "allowed" if r.get("request_allowed", True) else "blocked",
        }
        for r in rows
    ]
    return _upsert_batch(db, KafkaEvent, kafka_rows, conflict_col="trace_id")


def _load_clickhouse_aggregates(rows, db):
    ch_rows = []
    for r in rows:
        d = r.get("timestamp")
        date_val = d.date() if hasattr(d, "date") else None
        ch_rows.append({
            "agg_id":          r["trace_id"],
            "date":            date_val,
            "employee_id":     r["employee_id"],
            "department":      r["department"],
            "provider":        r["provider"],
            "model_name":      r["model_name"],
            "request_count":   1,
            "input_tokens":    r["input_tokens"],
            "output_tokens":   r["output_tokens"],
            "total_tokens":    r["total_tokens"],
            "cost_usd":        r["cost_usd"],
            "avg_latency_ms":  r["latency_ms"],
            "cache_hit_count": 1 if r.get("cache_hit") else 0,
            "cache_hit_rate":  1.0 if r.get("cache_hit") else 0.0,
        })
    return _upsert_batch(db, ClickHouseAggregate, ch_rows, conflict_col="agg_id")


def _load_kubernetes_logs(rows, db):
    return _upsert_batch(db, KubernetesLog, rows, conflict_col="log_id")


def _load_ignore(rows, db):
    return len(rows)


# ── UPSERT helper ─────────────────────────────────────────────────────────────

def _upsert_batch(
    db: Session,
    model,
    rows: list[dict],
    conflict_col: str,
    batch_size: int = 5_000,
) -> int:
    """
    UPSERT rows into *model*'s table using PostgreSQL ON CONFLICT DO UPDATE.

    Conflict resolution: if a row with the same *conflict_col* value exists,
    all non-PK columns are updated in-place. This is safe to call repeatedly
    with the same data — subsequent calls are no-ops on unchanged rows.

    Returns total rows processed (inserts + updates).
    """
    if not rows:
        return 0

    table = model.__table__
    valid_cols = {c.name for c in table.columns}
    pk_cols = {c.name for c in table.columns if c.primary_key}

    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i: i + batch_size]

        # Strip columns not present in the table schema
        clean = [{k: v for k, v in r.items() if k in valid_cols} for r in batch]

        stmt = pg_insert(table).values(clean)

        # Build SET clause: update all columns except PK and conflict key
        row_keys = set(clean[0].keys())
        update_set = {
            k: stmt.excluded[k]
            for k in row_keys
            if k not in pk_cols and k != conflict_col
        }

        if not update_set:
            # Nothing to update — use ON CONFLICT DO NOTHING for PK-only tables
            stmt = stmt.on_conflict_do_nothing(index_elements=[conflict_col])
        else:
            stmt = stmt.on_conflict_do_update(
                index_elements=[conflict_col],
                set_=update_set,
            )

        db.execute(stmt)
        total += len(batch)
        db.flush()

    return total
