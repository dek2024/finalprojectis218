"""Tests for user-related behaviors using the ORM and API together."""

from fastapi import status


def test_change_password_success(client, auth_headers):
    """Authenticated user should be able to change their password."""

    payload = {
        "current_password": "password123",
        "new_password": "NewStrongPass456!",
    }
    resp = client.post("/api/auth/change-password", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["message"] == "Password changed successfully"


def test_change_password_invalid_current(client, auth_headers):
    """Change password with wrong current password should fail with 401."""

    payload = {
        "current_password": "wrong",
        "new_password": "NewStrongPass456!",
    }
    resp = client.post("/api/auth/change-password", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_token_requires_auth(client):
    """Calling refresh-token without a valid token should fail."""

    resp = client.post("/api/auth/refresh-token")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_token_success(client, auth_headers):
    """Refresh token endpoint should return a new access token when authorized."""

    resp = client.post("/api/auth/refresh-token", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
