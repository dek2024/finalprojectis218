"""Tests for authentication endpoints: registration, login, and /me profile."""

from fastapi import status


def test_register_success(client):
    """Register a new user with valid data should succeed."""

    payload = {
        "email": "new@example.com",
        "username": "newuser",
        "full_name": "New User",
        "password": "StrongPass123!",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["email"] == payload["email"]
    assert body["username"] == payload["username"]


def test_register_duplicate_email(client, test_user):
    """Registering with an existing email should fail with 400."""

    payload = {
        "email": test_user.email,
        "username": "anotheruser",
        "full_name": "Another User",
        "password": "password123",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in resp.json()["detail"]


def test_register_duplicate_username(client, test_user):
    """Registering with an existing username should fail with 400."""

    payload = {
        "email": "someone@example.com",
        "username": test_user.username,
        "full_name": "Another User",
        "password": "password123",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Username already taken" in resp.json()["detail"]


def test_register_missing_fields(client):
    """Missing required fields should result in 422 validation error from FastAPI."""

    resp = client.post("/api/auth/register", json={"email": "x@example.com"})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_success(client, test_user):
    """Login with correct credentials should return access and refresh tokens."""

    resp = client.post(
        "/api/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, test_user):
    """Login with wrong password should return 401."""

    resp = client.post(
        "/api/auth/login",
        json={"email": test_user.email, "password": "wrong"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_missing_fields(client):
    """Missing email/password fields should trigger 422 validation error."""

    resp = client.post("/api/auth/login", json={"email": "x@example.com"})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_me_authorized(client, auth_headers):
    """/api/auth/me should return the current user when authorized."""

    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["email"] == "test@example.com"


def test_get_me_unauthorized(client):
    """/api/auth/me without a token should return 401."""

    resp = client.get("/api/auth/me")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
