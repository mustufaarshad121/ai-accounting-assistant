"""Tests for the health endpoint.

Verifies HTTP 200 and the exact expected JSON body, and that the endpoint
works without any database connection configured.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-accounting-assistant-api",
    }
