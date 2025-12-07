"""Pytest configuration and shared fixtures for the CareerLens FastAPI app."""

import os
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure the project root (which contains the ``app`` package) is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.main import app
from app.database import Base, get_db
from app.models import User
from app.auth.jwt import PasswordHandler


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Return a SQLite URL for a temporary on-disk test database.

    Using a real file (not purely in-memory) keeps the URL simple while still
    being isolated from the dev database.
    """

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return f"sqlite:///{path}"


@pytest.fixture(scope="session")
def engine(test_db_url):
    """Create a SQLAlchemy engine bound to the test database."""

    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Provide a fresh database session for each test function.

    Each test runs inside its own transaction to stay isolated.
    """

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with the application's get_db dependency overridden.

    All routes that depend on get_db() will use the in-memory test session
    instead of the real application database.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session) -> User:
    """Create and return a single active test user in the database."""
    # Ensure there are no leftover users from previous tests that might
    # violate the unique constraints on email/username.
    db_session.query(User).delete()
    db_session.commit()

    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=PasswordHandler.hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Return Authorization headers for the test user using the login endpoint."""

    resp = client.post(
        "/api/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
