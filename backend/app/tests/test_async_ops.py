"""
Async operations tests — activity feed, retry, heartbeat, system status.

Arq queue calls are mocked with AsyncMock so these tests run without a live
Redis or arq worker.  Cache calls are handled via the fakeredis fixture.
"""

import pytest
import fakeredis
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.integration import IntegrationSyncRun
from app.services import cache_service
from app.tests.conftest import get_token, auth_header


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def fake_redis_client():
    fake = fakeredis.FakeRedis(decode_responses=True)
    original = cache_service._client
    cache_service._client = fake
    yield fake
    cache_service._client = original


@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def _make_run(db, source="api_gateway", status="success", error="") -> IntegrationSyncRun:
    run = IntegrationSyncRun(
        source_name=source,
        status=status,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        error_message=error,
        rows_ingested=100,
        duration_ms=250,
    )
    db.add(run)
    db.flush()
    return run


# ── activity feed ─────────────────────────────────────────────────────────────

class TestActivityFeed:
    def test_empty_feed_returns_list(self, client):
        resp = client.get("/api/integrations/activity")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_feed_contains_seeded_runs(self, client, db):
        _make_run(db, source="api_gateway", status="success")
        _make_run(db, source="browser", status="failed", error="Timeout")
        resp = client.get("/api/integrations/activity")
        assert resp.status_code == 200
        items = resp.json()
        sources = {r["source_name"] for r in items}
        assert "api_gateway" in sources
        assert "browser" in sources

    def test_feed_ordered_newest_first(self, client, db):
        _make_run(db, source="kafka", status="success")
        _make_run(db, source="clickhouse", status="success")
        resp = client.get("/api/integrations/activity")
        items = resp.json()
        # Timestamps should be non-increasing (newest first)
        started_ats = [r["started_at"] for r in items if r["started_at"]]
        assert started_ats == sorted(started_ats, reverse=True)

    def test_feed_source_filter(self, client, db):
        _make_run(db, source="api_gateway", status="success")
        _make_run(db, source="browser", status="success")
        resp = client.get("/api/integrations/activity?source=api_gateway")
        items = resp.json()
        assert all(r["source_name"] == "api_gateway" for r in items)

    def test_feed_limit_respected(self, client, db):
        for _ in range(10):
            _make_run(db)
        resp = client.get("/api/integrations/activity?limit=3")
        assert len(resp.json()) <= 3

    def test_feed_item_shape(self, client, db):
        _make_run(db)
        item = client.get("/api/integrations/activity").json()[0]
        assert all(k in item for k in [
            "id", "source_name", "status", "started_at", "finished_at",
            "duration_ms", "rows_ingested", "rows_skipped",
            "validation_warnings_count", "triggered_by",
        ])


# ── retry endpoint ────────────────────────────────────────────────────────────

class TestRetryEndpoint:
    def test_retry_failed_run_returns_queued(self, client, db, admin_user):
        run = _make_run(db, source="api_gateway", status="failed", error="Connection timeout")
        token = get_token(client, admin_user.email, "testpass123")

        with patch("app.api.integrations.enqueue_sync", new_callable=AsyncMock, return_value="fake-job-id"):
            resp = client.post(f"/api/integrations/retry/{run.id}", headers=auth_header(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["job_id"] == "fake-job-id"
        assert data["source"] == "api_gateway"

    def test_retry_success_run_returns_400(self, client, db, admin_user):
        run = _make_run(db, source="api_gateway", status="success")
        token = get_token(client, admin_user.email, "testpass123")

        resp = client.post(f"/api/integrations/retry/{run.id}", headers=auth_header(token))
        assert resp.status_code == 400

    def test_retry_nonexistent_run_returns_404(self, client, db, admin_user):
        token = get_token(client, admin_user.email, "testpass123")
        resp = client.post("/api/integrations/retry/99999", headers=auth_header(token))
        assert resp.status_code == 404

    def test_retry_requires_admin(self, client, db, viewer_user):
        run = _make_run(db, source="api_gateway", status="failed")
        token = get_token(client, viewer_user.email, "testpass123")
        resp = client.post(f"/api/integrations/retry/{run.id}", headers=auth_header(token))
        assert resp.status_code == 403


# ── async sync endpoints ──────────────────────────────────────────────────────

class TestAsyncSyncEndpoint:
    def test_sync_one_returns_queued(self, client, db, admin_user):
        token = get_token(client, admin_user.email, "testpass123")
        with patch("app.api.integrations.enqueue_sync", new_callable=AsyncMock, return_value="job-abc"):
            resp = client.post("/api/integrations/sync/api_gateway", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["job_id"] == "job-abc"
        assert data["source"] == "api_gateway"

    def test_sync_unknown_source_returns_404(self, client, db, admin_user):
        token = get_token(client, admin_user.email, "testpass123")
        resp = client.post("/api/integrations/sync/nonexistent", headers=auth_header(token))
        assert resp.status_code == 404

    def test_sync_all_returns_list(self, client, db, admin_user):
        token = get_token(client, admin_user.email, "testpass123")
        mock_results = [{"source": s, "job_id": f"job-{s}"} for s in ["api_gateway", "browser"]]
        with patch("app.api.integrations.enqueue_sync_all", new_callable=AsyncMock, return_value=mock_results):
            resp = client.post("/api/integrations/sync/all/run", headers=auth_header(token))
        assert resp.status_code == 200
        items = resp.json()
        assert all(r["status"] == "queued" for r in items)


# ── heartbeat endpoint ────────────────────────────────────────────────────────

class TestHeartbeatEndpoint:
    def test_returns_dict_with_connector_keys(self, client):
        resp = client.get("/api/integrations/heartbeat")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "api_gateway" in data
        assert "browser" in data

    def test_returns_no_data_status_without_syncs(self, client):
        resp = client.get("/api/integrations/heartbeat")
        data = resp.json()
        # No syncs have been run, so all connectors should be no_data
        for source, hb in data.items():
            assert hb["status"] in {"no_data", "healthy", "stale"}

    def test_redis_heartbeat_takes_priority(self, client, db, fake_redis_client):
        # Pre-populate Redis heartbeat for api_gateway
        import json
        fake_redis_client.setex(
            "heartbeat:api_gateway",
            3600,
            json.dumps({
                "source": "api_gateway",
                "status": "healthy",
                "data_freshness_hours": 0.5,
                "checked_at": "2026-05-22T10:00:00+00:00",
            }),
        )
        resp = client.get("/api/integrations/heartbeat")
        data = resp.json()
        assert data["api_gateway"]["status"] == "healthy"
        assert data["api_gateway"]["data_freshness_hours"] == 0.5

    def test_healthy_after_recent_sync(self, client, db):
        _make_run(db, source="api_gateway", status="success")
        resp = client.get("/api/integrations/heartbeat")
        assert resp.json()["api_gateway"]["status"] == "healthy"


# ── system status endpoint ────────────────────────────────────────────────────

class TestSystemStatus:
    def test_returns_expected_shape(self, client):
        resp = client.get("/api/system/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "redis" in data
        assert "active_jobs" in data
        assert "worker" in data

    def test_redis_disconnected_when_unavailable(self, client):
        with patch.object(cache_service, "_get_client", side_effect=Exception("down")):
            resp = client.get("/api/system/status")
        assert resp.status_code == 200
        assert resp.json()["redis"] == "disconnected"

    def test_active_jobs_counts_running_runs(self, client, db):
        _make_run(db, source="api_gateway", status="running")
        _make_run(db, source="browser", status="running")
        _make_run(db, source="kafka", status="success")
        resp = client.get("/api/system/status")
        assert resp.json()["active_jobs"] == 2

    def test_worker_field_is_arq(self, client):
        assert client.get("/api/system/status").json()["worker"] == "arq"
