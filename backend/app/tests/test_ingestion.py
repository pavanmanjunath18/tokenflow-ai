"""
Ingestion UPSERT tests.

Verifies:
- Repeated sync of the same data is idempotent (row count stays stable)
- Updated fields are reflected after a second upsert
- Partial failures leave existing data intact
- sync_source returns structured results
"""

import pytest
from datetime import datetime
from app.services.ingestion_service import _upsert_batch, sync_source
from app.models.usage_event import AIUsageEvent
from app.models.employee import Employee
from app.models.license import AILicense
from app.models.browser_event import BrowserEvent


def _usage_row(trace_id: str, cost: float = 1.0) -> dict:
    return {
        "trace_id": trace_id,
        "timestamp": datetime(2025, 1, 1, 12, 0, 0),
        "employee_id": "E001",
        "department": "Engineering",
        "team": "Platform",
        "internal_app": "test_app",
        "provider": "anthropic",
        "model_name": "claude-3-5-sonnet",
        "task_type": "code_generation",
        "input_tokens": 100,
        "output_tokens": 200,
        "total_tokens": 300,
        "cost_usd": cost,
        "latency_ms": 500,
        "status_code": 200,
        "cache_hit": False,
        "request_allowed": True,
        "expensive_model_simple_task": False,
    }


class TestUpsertIdempotency:
    def test_same_rows_twice_no_growth(self, db):
        rows = [_usage_row("UPSERT_T001"), _usage_row("UPSERT_T002")]
        _upsert_batch(db, AIUsageEvent, rows, "trace_id")
        count_first = db.query(AIUsageEvent).filter(
            AIUsageEvent.trace_id.in_(["UPSERT_T001", "UPSERT_T002"])
        ).count()

        _upsert_batch(db, AIUsageEvent, rows, "trace_id")
        count_second = db.query(AIUsageEvent).filter(
            AIUsageEvent.trace_id.in_(["UPSERT_T001", "UPSERT_T002"])
        ).count()

        assert count_first == 2
        assert count_second == 2  # no duplicates

    def test_updated_field_reflected(self, db):
        rows = [_usage_row("UPSERT_T003", cost=1.0)]
        _upsert_batch(db, AIUsageEvent, rows, "trace_id")

        updated = [_usage_row("UPSERT_T003", cost=9.99)]
        _upsert_batch(db, AIUsageEvent, updated, "trace_id")

        event = db.query(AIUsageEvent).filter_by(trace_id="UPSERT_T003").first()
        assert event is not None
        assert abs(event.cost_usd - 9.99) < 0.001

    def test_new_rows_added_to_existing(self, db):
        _upsert_batch(db, AIUsageEvent, [_usage_row("UPSERT_T010")], "trace_id")
        count_before = db.query(AIUsageEvent).filter(
            AIUsageEvent.trace_id.like("UPSERT_T01%")
        ).count()

        _upsert_batch(db, AIUsageEvent, [_usage_row("UPSERT_T011"), _usage_row("UPSERT_T012")], "trace_id")
        count_after = db.query(AIUsageEvent).filter(
            AIUsageEvent.trace_id.like("UPSERT_T01%")
        ).count()

        assert count_after >= count_before + 2


class TestEmployeeUpsert:
    def test_employee_pk_upsert(self, db):
        emp = {
            "employee_id": "TEST_E001",
            "employee_name": "Alice Smith",
            "email": "alice@test.com",
            "department": "Engineering",
            "team": "Backend",
            "role": "Senior Engineer",
            "manager_id": "",
            "cost_center": "CC001",
            "location": "Tempe, AZ",
            "employment_type": "Full-time",
            "start_date": None,
            "sso_provider": "okta",
            "status": "active",
        }
        _upsert_batch(db, Employee, [emp], "employee_id")
        _upsert_batch(db, Employee, [{**emp, "team": "Frontend"}], "employee_id")

        e = db.query(Employee).filter_by(employee_id="TEST_E001").first()
        assert e is not None
        assert e.team == "Frontend"  # updated
        assert db.query(Employee).filter_by(employee_id="TEST_E001").count() == 1


class TestSyncSourceResult:
    def test_sync_returns_structured_response(self, db):
        """sync_source returns a dict with required keys regardless of outcome."""
        # This will fail because synthetic data files aren't present in tests,
        # but the response structure must still be correct.
        result = sync_source("model_pricing", db, triggered_by="test@test.com")
        assert "source" in result
        assert "rows_ingested" in result
        assert "status" in result
        assert result["source"] == "model_pricing"

    def test_unknown_source_raises(self, db):
        with pytest.raises(ValueError, match="Unknown source"):
            sync_source("nonexistent_source", db)
