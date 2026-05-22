"""
Test configuration.

Uses PostgreSQL (tokenflow_test) with outer-transaction rollback isolation:
  - Each test runs inside an outer transaction
  - The app's `session.commit()` calls only release savepoints (not real commits)
  - The outer transaction is rolled back after each test → perfect isolation

Run tests from backend/:
    pytest app/tests/ -v
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.core.security import hash_password
from app.models.user import User

TEST_DB_URL = "postgresql://tokenflow:tokenflow@localhost:5432/tokenflow_test"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    # Don't drop — let the tables persist for inspection; re-create handles fresh state
    engine.dispose()


@pytest.fixture
def db(test_engine):
    """
    Per-test DB session with full rollback isolation.

    Uses SQLAlchemy 2.0's join_transaction_mode="create_savepoint" so that
    any session.commit() inside the app only releases a savepoint — the outer
    transaction is rolled back when the fixture tears down, leaving the DB clean.
    """
    conn = test_engine.connect()
    outer_trans = conn.begin()

    Session = sessionmaker(
        bind=conn,
        join_transaction_mode="create_savepoint",
    )
    session = Session()
    yield session
    session.close()
    outer_trans.rollback()
    conn.close()


@pytest.fixture
def client(db):
    """TestClient with DB overridden to the isolated test session."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    # raise_server_exceptions=False lets us inspect HTTP error codes
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    user = User(
        email="test-admin@tokenflow.local",
        hashed_password=hash_password("testpass123"),
        full_name="Test Admin",
        role="admin",
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def reviewer_user(db):
    user = User(
        email="test-reviewer@tokenflow.local",
        hashed_password=hash_password("testpass123"),
        full_name="Test Reviewer",
        role="reviewer",
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def viewer_user(db):
    user = User(
        email="test-viewer@tokenflow.local",
        hashed_password=hash_password("testpass123"),
        full_name="Test Viewer",
        role="viewer",
    )
    db.add(user)
    db.flush()
    return user


def get_token(client, email: str, password: str) -> str:
    resp = client.post("/api/auth/token", data={"username": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
