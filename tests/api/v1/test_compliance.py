"""Tests for DEV-378: GDPR Compliance Dashboard API."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.compliance import (
    _get_breach_status,
    _get_data_requests_status,
    _get_dpa_status,
    router,
)


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def mock_db():
    return AsyncMock()


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


class TestGetDpaStatus:
    """Tests for _get_dpa_status helper function."""

    @pytest.mark.asyncio
    async def test_dpa_accepted(self, mock_db, studio_id):
        """Happy path: studio has accepted the active DPA."""
        mock_dpa = MagicMock()
        mock_dpa.id = uuid4()
        mock_dpa.version = "2.0"

        dpa_result = MagicMock()
        dpa_result.scalars.return_value.first.return_value = mock_dpa

        acceptance_result = MagicMock()
        acceptance_result.scalars.return_value.first.return_value = MagicMock()

        mock_db.execute = AsyncMock(side_effect=[dpa_result, acceptance_result])

        result = await _get_dpa_status(mock_db, studio_id)

        assert result["accepted"] is True
        assert result["dpa_version"] == "2.0"

    @pytest.mark.asyncio
    async def test_dpa_no_active(self, mock_db, studio_id):
        """Edge case: no active DPA exists."""
        dpa_result = MagicMock()
        dpa_result.scalars.return_value.first.return_value = None

        mock_db.execute = AsyncMock(return_value=dpa_result)

        result = await _get_dpa_status(mock_db, studio_id)

        assert result["accepted"] is False
        assert "Nessun DPA attivo" in result["reason"]

    @pytest.mark.asyncio
    async def test_dpa_not_accepted(self, mock_db, studio_id):
        """Edge case: studio has NOT accepted the DPA."""
        mock_dpa = MagicMock()
        mock_dpa.id = uuid4()
        mock_dpa.version = "1.0"

        dpa_result = MagicMock()
        dpa_result.scalars.return_value.first.return_value = mock_dpa

        acceptance_result = MagicMock()
        acceptance_result.scalars.return_value.first.return_value = None

        mock_db.execute = AsyncMock(side_effect=[dpa_result, acceptance_result])

        result = await _get_dpa_status(mock_db, studio_id)

        assert result["accepted"] is False

    @pytest.mark.asyncio
    async def test_dpa_exception_returns_fallback(self, mock_db, studio_id):
        """Error case: DB error returns safe fallback."""
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))

        result = await _get_dpa_status(mock_db, studio_id)

        assert result["accepted"] is False
        assert "Impossibile" in result["reason"]


class TestGetDataRequestsStatus:
    """Tests for _get_data_requests_status helper function."""

    @pytest.mark.asyncio
    async def test_data_requests_with_pending(self, mock_db, studio_id):
        """Happy path: returns total and pending counts via patched model."""
        total_result = MagicMock()
        total_result.scalar_one_or_none.return_value = 5

        pending_result = MagicMock()
        pending_result.scalar_one_or_none.return_value = 2

        mock_db.execute = AsyncMock(side_effect=[total_result, pending_result])

        mock_model = MagicMock()
        mock_module = MagicMock()
        mock_module.DataExportRequest = mock_model

        with patch.dict("sys.modules", {"app.models.data_export": mock_module}):
            result = await _get_data_requests_status(mock_db, studio_id)

        assert result["total"] == 5
        assert result["pending"] == 2
        assert result["overdue"] == 0

    @pytest.mark.asyncio
    async def test_data_requests_none_counts(self, mock_db, studio_id):
        """Edge case: NULL counts default to 0."""
        total_result = MagicMock()
        total_result.scalar_one_or_none.return_value = None

        pending_result = MagicMock()
        pending_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[total_result, pending_result])

        mock_model = MagicMock()
        mock_module = MagicMock()
        mock_module.DataExportRequest = mock_model

        with patch.dict("sys.modules", {"app.models.data_export": mock_module}):
            result = await _get_data_requests_status(mock_db, studio_id)

        assert result["total"] == 0
        assert result["pending"] == 0

    @pytest.mark.asyncio
    async def test_data_requests_exception_returns_fallback(self, mock_db, studio_id):
        """Error case: DB error returns safe fallback."""
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))

        result = await _get_data_requests_status(mock_db, studio_id)

        assert result == {"total": 0, "pending": 0, "overdue": 0}


class TestGetBreachStatus:
    """Tests for _get_breach_status helper function."""

    @pytest.mark.asyncio
    async def test_breach_status_with_breaches(self, mock_db, studio_id):
        """Happy path: returns total breach count."""
        total_result = MagicMock()
        total_result.scalar_one_or_none.return_value = 3

        mock_db.execute = AsyncMock(return_value=total_result)

        result = await _get_breach_status(mock_db, studio_id)

        assert result["total_breaches"] == 3
        assert result["active_breaches"] == 0

    @pytest.mark.asyncio
    async def test_breach_status_none_count(self, mock_db, studio_id):
        """Edge case: NULL count defaults to 0."""
        total_result = MagicMock()
        total_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=total_result)

        result = await _get_breach_status(mock_db, studio_id)

        assert result["total_breaches"] == 0

    @pytest.mark.asyncio
    async def test_breach_status_exception_returns_fallback(self, mock_db, studio_id):
        """Error case: DB error returns safe fallback."""
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))

        result = await _get_breach_status(mock_db, studio_id)

        assert result == {"total_breaches": 0, "active_breaches": 0}
