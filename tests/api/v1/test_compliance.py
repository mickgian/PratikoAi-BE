"""Tests for DEV-378: GDPR Compliance Dashboard API."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.compliance import router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def studio_id():
    return uuid4()


class TestComplianceDashboard:
    """Tests for GET /compliance endpoint."""

    @pytest.mark.asyncio
    async def test_returns_all_sections(self, app, studio_id):
        with (
            patch("app.api.v1.compliance.get_db", return_value=AsyncMock()),
            patch("app.api.v1.compliance._get_dpa_status", new_callable=AsyncMock) as mock_dpa,
            patch("app.api.v1.compliance._get_data_requests_status", new_callable=AsyncMock) as mock_dr,
            patch("app.api.v1.compliance._get_breach_status", new_callable=AsyncMock) as mock_breach,
        ):
            mock_dpa.return_value = {"accepted": True, "dpa_version": "1.0"}
            mock_dr.return_value = {"total": 0, "pending": 0, "overdue": 0}
            mock_breach.return_value = {"total_breaches": 0, "active_breaches": 0}

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get(f"/api/v1/compliance?studio_id={studio_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert "dpa" in data
        assert "data_requests" in data
        assert "breach_status" in data
        assert "overall_compliant" in data

    @pytest.mark.asyncio
    async def test_overall_compliant_when_all_ok(self, app, studio_id):
        with (
            patch("app.api.v1.compliance.get_db", return_value=AsyncMock()),
            patch("app.api.v1.compliance._get_dpa_status", new_callable=AsyncMock) as mock_dpa,
            patch("app.api.v1.compliance._get_data_requests_status", new_callable=AsyncMock) as mock_dr,
            patch("app.api.v1.compliance._get_breach_status", new_callable=AsyncMock) as mock_breach,
        ):
            mock_dpa.return_value = {"accepted": True}
            mock_dr.return_value = {"overdue": 0}
            mock_breach.return_value = {"active_breaches": 0}

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get(f"/api/v1/compliance?studio_id={studio_id}")

        assert resp.json()["overall_compliant"] is True

    @pytest.mark.asyncio
    async def test_not_compliant_dpa_not_accepted(self, app, studio_id):
        with (
            patch("app.api.v1.compliance.get_db", return_value=AsyncMock()),
            patch("app.api.v1.compliance._get_dpa_status", new_callable=AsyncMock) as mock_dpa,
            patch("app.api.v1.compliance._get_data_requests_status", new_callable=AsyncMock) as mock_dr,
            patch("app.api.v1.compliance._get_breach_status", new_callable=AsyncMock) as mock_breach,
        ):
            mock_dpa.return_value = {"accepted": False}
            mock_dr.return_value = {"overdue": 0}
            mock_breach.return_value = {"active_breaches": 0}

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get(f"/api/v1/compliance?studio_id={studio_id}")

        assert resp.json()["overall_compliant"] is False

    @pytest.mark.asyncio
    async def test_missing_studio_id_returns_422(self, app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/compliance")

        assert resp.status_code == 422
