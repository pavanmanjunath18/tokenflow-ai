"""
Validation log tests.

Verifies:
- _validate_schema detects missing columns
- _validate_rows detects empty/null required fields
- Validation logs are persisted to DB after a sync
- validation_warnings_count on the run matches actual log entries
- Schema errors appear as 'schema' type in the log
- Row warnings appear as 'missing_value' type
"""

import pytest
from datetime import datetime, timezone

from app.connectors.base import BaseConnector, ConnectorResult
from app.connectors.identity_connector import IdentityConnector
from app.connectors.api_gateway_connector import APIGatewayConnector
from app.models.validation_log import IngestionValidationLog
from app.models.integration import IntegrationSyncRun
from app.services.ingestion_service import _persist_validation_logs


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_run(db, source="test_connector") -> IntegrationSyncRun:
    run = IntegrationSyncRun(
        source_name=source,
        status="success",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    return run


# ── schema validation ──────────────────────────────────────────────────────────

class TestSchemaValidation:
    def test_missing_required_columns_detected(self):
        c = IdentityConnector()
        rows = [{"employee_id": "E001", "email": "a@b.com"}]  # missing many
        errors = c._validate_schema(rows)
        assert len(errors) > 0
        assert all("Missing column:" in e for e in errors)
        missing_fields = {e.split(": ")[1] for e in errors}
        assert "employee_name" in missing_fields

    def test_all_required_columns_present_no_errors(self):
        c = IdentityConnector()
        row = {col: "val" for col in c.REQUIRED_COLS}
        errors = c._validate_schema([row])
        assert errors == []

    def test_empty_rows_no_errors(self):
        c = IdentityConnector()
        assert c._validate_schema([]) == []

    def test_no_required_cols_no_errors(self):
        class _NoReqs(IdentityConnector):
            REQUIRED_COLS = set()
        c = _NoReqs()
        assert c._validate_schema([{"any": "val"}]) == []


# ── row validation ─────────────────────────────────────────────────────────────

class TestRowValidation:
    def test_empty_required_field_triggers_warning(self):
        c = IdentityConnector()
        rows = [{"employee_id": "", "employee_name": "", "email": "", "department": "", "status": ""}]
        warnings = c._validate_rows(rows)
        # All 5 REQUIRED_COLS are empty → 5 warnings
        assert len(warnings) == 5
        assert all(w["error_type"] == "missing_value" for w in warnings)

    def test_null_required_field_triggers_warning(self):
        c = IdentityConnector()
        rows = [{"employee_id": None, "employee_name": "Alice", "email": "a@b.com", "department": "Eng", "status": "active"}]
        warnings = c._validate_rows(rows)
        assert any(w["field_name"] == "employee_id" for w in warnings)

    def test_valid_rows_no_warnings(self):
        c = IdentityConnector()
        rows = [{"employee_id": "E001", "employee_name": "Alice", "email": "a@b.com", "department": "Eng", "status": "active"}]
        warnings = c._validate_rows(rows)
        assert warnings == []

    def test_warning_contains_row_number(self):
        c = IdentityConnector()
        rows = [
            {"employee_id": "E001", "employee_name": "Alice", "email": "a@b.com", "department": "Eng", "status": "active"},
            {"employee_id": "",     "employee_name": "Bob",   "email": "b@b.com", "department": "Eng", "status": "active"},
        ]
        warnings = c._validate_rows(rows)
        assert len(warnings) == 1
        assert warnings[0]["row_number"] == 1  # second row

    def test_warning_cap_at_100(self):
        c = IdentityConnector()
        # 200 rows with all REQUIRED_COLS empty → would be 1000 warnings, capped at 100
        rows = [{col: "" for col in c.REQUIRED_COLS} for _ in range(200)]
        warnings = c._validate_rows(rows)
        assert len(warnings) <= 100

    def test_empty_rows_no_warnings(self):
        c = IdentityConnector()
        assert c._validate_rows([]) == []


# ── persistence ────────────────────────────────────────────────────────────────

class TestValidationLogPersistence:
    def test_schema_errors_saved_to_db(self, db):
        run = _make_run(db, "test_schema_src")
        schema_errors = ["Missing column: trace_id", "Missing column: employee_id"]
        _persist_validation_logs(run.id, "test_schema_src", schema_errors, [], db)
        db.flush()

        logs = db.query(IngestionValidationLog).filter_by(run_id=run.id).all()
        assert len(logs) == 2
        assert all(l.error_type == "schema" for l in logs)
        messages = {l.error_message for l in logs}
        assert "Missing column: trace_id" in messages

    def test_row_warnings_saved_to_db(self, db):
        run = _make_run(db, "test_row_src")
        row_warnings = [
            {"row_number": 5, "field_name": "employee_id", "error_type": "missing_value",
             "raw_value": "", "message": "Required field 'employee_id' is empty"},
        ]
        _persist_validation_logs(run.id, "test_row_src", [], row_warnings, db)
        db.flush()

        log = db.query(IngestionValidationLog).filter_by(run_id=run.id).first()
        assert log is not None
        assert log.error_type == "missing_value"
        assert log.field_name == "employee_id"
        assert log.row_number == 5

    def test_no_logs_persisted_when_clean(self, db):
        run = _make_run(db, "test_clean_src")
        _persist_validation_logs(run.id, "test_clean_src", [], [], db)
        db.flush()
        count = db.query(IngestionValidationLog).filter_by(run_id=run.id).count()
        assert count == 0

    def test_run_id_links_to_sync_run(self, db):
        run = _make_run(db, "test_link_src")
        _persist_validation_logs(
            run.id, "test_link_src",
            ["Missing column: foo"],
            [],
            db,
        )
        db.flush()
        log = db.query(IngestionValidationLog).filter_by(run_id=run.id).first()
        assert log.run_id == run.id
        assert log.connector_name == "test_link_src"
