"""
Watermark / incremental sync tests.

Verifies that:
- sync() with no watermark returns all rows
- sync() with a future since skips all time-series rows
- sync() with a past since returns rows after that point
- Reference-data connectors (no timestamp) ignore the watermark
- rows_skipped is counted correctly
- ConnectorResult has the expected shape
"""

import pytest
from datetime import datetime, timezone

from app.connectors.base import BaseConnector, ConnectorResult
from app.connectors.api_gateway_connector import APIGatewayConnector
from app.connectors.identity_connector import IdentityConnector
from app.connectors.kafka_connector import KafkaTelemetryConnector
from app.services.ingestion_service import _get_last_success_time, sync_source, CONNECTORS
from app.models.integration import IntegrationSyncRun


# ── fixture connector with controlled data ─────────────────────────────────────

class _TimestampConnector(BaseConnector):
    """Test connector that returns rows with known timestamps."""
    source_name = "test_ts"
    source_type = "csv"
    production_equivalent = "test"
    REQUIRED_COLS = {"trace_id", "timestamp"}

    def __init__(self, rows):
        self._rows = rows
        self.data_dir = None  # not needed

    def _fetch_raw(self):
        return []  # not used — _normalize is called with explicit rows

    def _normalize(self, rows):
        return rows

    def sync(self, since=None):
        all_rows = self._rows
        if since and all_rows and "timestamp" in all_rows[0]:
            filtered = [r for r in all_rows if r["timestamp"] >= since]
            skipped = len(all_rows) - len(filtered)
        else:
            filtered = all_rows
            skipped = 0
        return ConnectorResult(rows=filtered, schema_errors=[], row_warnings=[], rows_skipped=skipped)


class _RefConnector(BaseConnector):
    """Test connector without timestamps (reference data)."""
    source_name = "test_ref"
    source_type = "csv"
    production_equivalent = "test"
    REQUIRED_COLS = {"employee_id"}

    def __init__(self, rows):
        self._rows = rows
        self.data_dir = None

    def _fetch_raw(self):
        return []

    def _normalize(self, rows):
        return rows

    def sync(self, since=None):
        # Reference connectors expose no 'timestamp' → watermark is ignored
        return ConnectorResult(rows=self._rows, schema_errors=[], row_warnings=[], rows_skipped=0)


# ── test rows ──────────────────────────────────────────────────────────────────

JAN = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
FEB = datetime(2025, 2, 15, 12, 0, tzinfo=timezone.utc)
MAR = datetime(2025, 3, 15, 12, 0, tzinfo=timezone.utc)

_TS_ROWS = [
    {"trace_id": "T001", "timestamp": JAN},
    {"trace_id": "T002", "timestamp": FEB},
    {"trace_id": "T003", "timestamp": MAR},
]


class TestWatermarkFiltering:
    def test_no_watermark_returns_all_rows(self):
        c = _TimestampConnector(_TS_ROWS)
        result = c.sync(since=None)
        assert len(result.rows) == 3
        assert result.rows_skipped == 0

    def test_future_watermark_skips_all_rows(self):
        future = datetime(2030, 1, 1, tzinfo=timezone.utc)
        c = _TimestampConnector(_TS_ROWS)
        result = c.sync(since=future)
        assert len(result.rows) == 0
        assert result.rows_skipped == 3

    def test_past_watermark_returns_rows_after_cutoff(self):
        # since=JAN should keep FEB and MAR (>= JAN means JAN itself is included too)
        c = _TimestampConnector(_TS_ROWS)
        result = c.sync(since=FEB)
        # FEB and MAR pass (>= FEB); JAN is skipped
        assert len(result.rows) == 2
        assert result.rows_skipped == 1
        assert all(r["timestamp"] >= FEB for r in result.rows)

    def test_rows_skipped_plus_rows_equals_total(self):
        c = _TimestampConnector(_TS_ROWS)
        result = c.sync(since=MAR)
        assert result.rows_skipped + len(result.rows) == len(_TS_ROWS)

    def test_reference_connector_ignores_watermark(self):
        ref_rows = [{"employee_id": "E001"}, {"employee_id": "E002"}]
        c = _RefConnector(ref_rows)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        result = c.sync(since=future)
        # No timestamp field → watermark is ignored → all rows returned
        assert len(result.rows) == 2
        assert result.rows_skipped == 0

    def test_connector_result_shape(self):
        c = _TimestampConnector(_TS_ROWS)
        result = c.sync()
        assert isinstance(result, ConnectorResult)
        assert isinstance(result.rows, list)
        assert isinstance(result.schema_errors, list)
        assert isinstance(result.row_warnings, list)
        assert isinstance(result.rows_skipped, int)

    def test_empty_rows_no_crash(self):
        c = _TimestampConnector([])
        result = c.sync(since=JAN)
        assert result.rows == []
        assert result.rows_skipped == 0


class TestWatermarkLookup:
    def test_no_previous_sync_returns_none(self, db):
        since = _get_last_success_time("api_gateway_test_nonexistent", db)
        assert since is None

    def test_last_success_returned_after_successful_run(self, db):
        t = datetime(2025, 6, 1, 10, 0)  # naive — matches DB storage
        run = IntegrationSyncRun(
            source_name="watermark_test_src",
            status="success",
            finished_at=t,
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()

        since = _get_last_success_time("watermark_test_src", db)
        assert since is not None
        since_naive = since.replace(tzinfo=None) if since.tzinfo else since
        assert abs((since_naive - t).total_seconds()) < 1

    def test_failed_run_not_used_as_watermark(self, db):
        db.add(IntegrationSyncRun(
            source_name="watermark_failed_src",
            status="failed",
            finished_at=datetime(2025, 7, 1, tzinfo=timezone.utc),
            started_at=datetime.now(timezone.utc),
        ))
        db.flush()
        since = _get_last_success_time("watermark_failed_src", db)
        assert since is None

    def test_returns_most_recent_success(self, db):
        earlier = datetime(2025, 1, 1)  # naive
        later   = datetime(2025, 6, 1)  # naive
        for t in [earlier, later]:
            db.add(IntegrationSyncRun(
                source_name="watermark_multi_src",
                status="success",
                finished_at=t,
                started_at=datetime.now(timezone.utc),
            ))
        db.flush()
        since = _get_last_success_time("watermark_multi_src", db)
        since_naive = since.replace(tzinfo=None) if since and since.tzinfo else since
        assert since_naive is not None
        assert abs((since_naive - later).total_seconds()) < 1
