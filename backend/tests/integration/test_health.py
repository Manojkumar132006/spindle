"""Integration tests for FastAPI health endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from spindle.api.app import app


@pytest.mark.asyncio
async def test_root_health():
    """Test /health endpoint returns 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["project"] == "Spindle"
        assert "version" in data


@pytest.mark.asyncio
async def test_api_v1_health_with_mock_db(monkeypatch):
    """Test /api/v1/health endpoint returns database status."""
    from spindle.api import app as app_module

    # Mock verify_connection to return True
    async def mock_verify():
        return True

    monkeypatch.setattr(app_module, "verify_connection", mock_verify)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
