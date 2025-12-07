"""Tests for high-level application routes such as /dashboard and /health."""

from fastapi import status


def test_health_check(client):
    """/health should return a simple healthy status payload."""

    resp = client.get("/health")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data


def test_home_page(client):
    """Root route should return the HTML home page (200)."""

    resp = client.get("/")
    assert resp.status_code == status.HTTP_200_OK
    assert "text/html" in resp.headers["content-type"].lower()


def test_dashboard_requires_auth(client):
    """/dashboard is rendered server-side but JS will check token.

    Here we only assert that the HTML template is returned; the
    client-side JS handles redirecting if there is no token.
    """

    resp = client.get("/dashboard")
    assert resp.status_code == status.HTTP_200_OK
    assert "text/html" in resp.headers["content-type"].lower()
