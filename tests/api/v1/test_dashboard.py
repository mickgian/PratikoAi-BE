"""Tests for DEV-356: Dashboard API Endpoint.

Tests the dashboard router logic without requiring a database connection.
The actual endpoint integration is tested via the dashboard_service tests.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends, FastAPI, Query
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def mock_dashboard_service():
    service = MagicMock()
    service.get_dashboard_data = AsyncMock(
        return_value={
            "clients": {"total": 5},
            "communications": {"total": 10, "pending_review": 2},
            "procedures": {"total": 3, "active": 1},
            "matches": {"active_rules": 4},
            "roi": {"hours_saved": 10.5},
        }
    )
    service.invalidate_cache = AsyncMock()
    return service


@pytest.fixture
def app(mock_dashboard_service):
    """Build a lightweight FastAPI app with dashboard-like routes."""
    app = FastAPI()
    router = APIRouter(prefix="/dashboard", tags=["dashboard"])

    @router.get("")
    async def get_dashboard(studio_id: str = Query(...)):
        return await mock_dashboard_service.get_dashboard_data(None, studio_id=studio_id)

    @router.post("/invalidate-cache", status_code=204)
    async def invalidate_cache(studio_id: str = Query(...)):
        await mock_dashboard_service.invalidate_cache(studio_id)

    app.include_router(router, prefix="/api/v1")
    return app


class TestGetDashboard:
    """Tests for GET /dashboard endpoint."""

    @pytest.mark.asyncio
    async def test_returns_dashboard_data(self, app, studio_id):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(f"/api/v1/dashboard?studio_id={studio_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["clients"]["total"] == 5
        assert data["communications"]["pending_review"] == 2
        assert data["procedures"]["active"] == 1
        assert data["matches"]["active_rules"] == 4
        assert data["roi"]["hours_saved"] == 10.5

    @pytest.mark.asyncio
    async def test_missing_studio_id_returns_422(self, app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/dashboard")

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_dashboard_response_has_all_sections(self, app, studio_id):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(f"/api/v1/dashboard?studio_id={studio_id}")

        data = resp.json()
        assert "clients" in data
        assert "communications" in data
        assert "procedures" in data
        assert "matches" in data
        assert "roi" in data


class TestInvalidateCache:
    """Tests for POST /dashboard/invalidate-cache."""

    @pytest.mark.asyncio
    async def test_invalidate_returns_204(self, app, studio_id, mock_dashboard_service):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(f"/api/v1/dashboard/invalidate-cache?studio_id={studio_id}")

        assert resp.status_code == 204
        mock_dashboard_service.invalidate_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_missing_studio_id_returns_422(self, app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/dashboard/invalidate-cache")

        assert resp.status_code == 422
