"""
Authentication + RBAC tests.

Verifies:
- Login with valid credentials returns a JWT
- Login with bad credentials returns 401
- Protected endpoints reject unauthenticated requests
- Role enforcement (admin-only, reviewer+, etc.)
"""

import pytest
from fastapi.testclient import TestClient
from app.tests.conftest import get_token, auth_header


def test_login_returns_token(client, admin_user):
    resp = client.post(
        "/api/auth/token",
        data={"username": "test-admin@tokenflow.local", "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_bad_password(client, admin_user):
    resp = client.post(
        "/api/auth/token",
        data={"username": "test-admin@tokenflow.local", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/api/auth/token",
        data={"username": "nobody@example.com", "password": "anything"},
    )
    assert resp.status_code == 401


def test_me_returns_current_user(client, admin_user):
    token = get_token(client, "test-admin@tokenflow.local", "testpass123")
    resp = client.get("/api/auth/me", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test-admin@tokenflow.local"
    assert data["role"] == "admin"


def test_sync_requires_auth(client):
    """Unauthenticated sync attempt must return 401."""
    resp = client.post("/api/integrations/sync/identity")
    assert resp.status_code == 401


def test_sync_requires_admin_role(client, viewer_user):
    """Viewer role is not allowed to trigger syncs."""
    token = get_token(client, "test-viewer@tokenflow.local", "testpass123")
    resp = client.post(
        "/api/integrations/sync/identity",
        headers=auth_header(token),
    )
    assert resp.status_code == 403


def test_audit_log_requires_admin(client, reviewer_user):
    """Reviewer cannot access audit logs (admin only)."""
    token = get_token(client, "test-reviewer@tokenflow.local", "testpass123")
    resp = client.get("/api/audit", headers=auth_header(token))
    assert resp.status_code == 403


def test_audit_log_accessible_by_admin(client, admin_user):
    token = get_token(client, "test-admin@tokenflow.local", "testpass123")
    resp = client.get("/api/audit", headers=auth_header(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_generate_recs_requires_admin(client, reviewer_user):
    """Reviewer cannot trigger recommendation generation."""
    token = get_token(client, "test-reviewer@tokenflow.local", "testpass123")
    resp = client.post("/api/recommendations/generate", headers=auth_header(token))
    assert resp.status_code == 403


def test_review_rec_allowed_for_reviewer(client, reviewer_user, db):
    """Reviewer role can review recommendations."""
    from app.models.recommendation import Recommendation
    import hashlib

    sig = hashlib.sha256(b"test_rec").hexdigest()[:16]
    rec = Recommendation(
        signature_hash=sig,
        recommendation_type="model_downgrade",
        title="Test rec",
        severity="medium",
        department="Engineering",
        estimated_monthly_savings=50.0,
        confidence_score=0.8,
    )
    db.add(rec)
    db.flush()
    rec_id = rec.id

    token = get_token(client, "test-reviewer@tokenflow.local", "testpass123")
    resp = client.patch(
        f"/api/recommendations/{rec_id}/review",
        json={"status": "investigating", "review_notes": "Looking into this"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "investigating"


def test_admin_can_create_users(client, admin_user):
    token = get_token(client, "test-admin@tokenflow.local", "testpass123")
    resp = client.post(
        "/api/auth/users",
        json={"email": "newuser@test.com", "password": "pass123", "role": "analyst"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "newuser@test.com"
    assert resp.json()["role"] == "analyst"


def test_viewer_cannot_create_users(client, viewer_user):
    token = get_token(client, "test-viewer@tokenflow.local", "testpass123")
    resp = client.post(
        "/api/auth/users",
        json={"email": "another@test.com", "password": "pass123"},
        headers=auth_header(token),
    )
    assert resp.status_code == 403
