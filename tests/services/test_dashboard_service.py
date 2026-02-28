"""Tests for DEV-355 + DEV-358: Dashboard Data Aggregation + Caching."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.dashboard_service import DashboardService


@pytest.fixture
def service():
    return DashboardService()


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Default: all counts return 0
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 0
    mock_result.scalars.return_value.first.return_value = None
    db.execute.return_value = mock_result
    return db


class TestGetDashboardData:
    """Tests for dashboard data aggregation."""

    @pytest.mark.asyncio
    async def test_returns_all_sections(self, service, mock_db, studio_id):
        """Dashboard returns all required sections."""
        with (
            patch.object(service, "_get_from_cache", return_value=None),
            patch.object(service, "_set_cache", return_value=None),
        ):
            data = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        assert "clients" in data
        assert "communications" in data
        assert "procedures" in data
        assert "matches" in data
        assert "roi" in data

    @pytest.mark.asyncio
    async def test_client_stats_structure(self, service, mock_db, studio_id):
        with (
            patch.object(service, "_get_from_cache", return_value=None),
            patch.object(service, "_set_cache", return_value=None),
        ):
            data = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        assert "total" in data["clients"]

    @pytest.mark.asyncio
    async def test_communication_stats_structure(self, service, mock_db, studio_id):
        with (
            patch.object(service, "_get_from_cache", return_value=None),
            patch.object(service, "_set_cache", return_value=None),
        ):
            data = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        assert "total" in data["communications"]
        assert "pending_review" in data["communications"]

    @pytest.mark.asyncio
    async def test_procedure_stats_structure(self, service, mock_db, studio_id):
        with (
            patch.object(service, "_get_from_cache", return_value=None),
            patch.object(service, "_set_cache", return_value=None),
        ):
            data = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        assert "total" in data["procedures"]
        assert "active" in data["procedures"]


class TestDashboardCaching:
    """Tests for DEV-358: Dashboard caching."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(self, service, mock_db, studio_id):
        """When cache has data, return it without DB queries."""
        cached_data = {"clients": {"total": 5}, "cached": True}
        with patch.object(service, "_get_from_cache", return_value=cached_data):
            data = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        assert data == cached_data
        # DB should not be called when cache hit
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_queries_db(self, service, mock_db, studio_id):
        """When cache is empty, query DB and cache result."""
        with (
            patch.object(service, "_get_from_cache", return_value=None),
            patch.object(service, "_set_cache", return_value=None) as mock_set,
        ):
            data = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        # DB was queried
        assert mock_db.execute.called
        # Result was cached
        mock_set.assert_called_once_with(studio_id, data)

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, service, studio_id):
        """invalidate_cache calls redis delete."""
        mock_redis = AsyncMock()
        mock_cache = MagicMock()
        mock_cache._get_redis = AsyncMock(return_value=mock_redis)
        with patch("app.services.cache.cache_service", mock_cache):
            await service.invalidate_cache(studio_id)

        mock_redis.delete.assert_called_once()


class TestROIStatsError:
    """Edge case: ROI service failure."""

    @pytest.mark.asyncio
    async def test_roi_failure_returns_defaults(self, service, mock_db, studio_id):
        """If ROI metrics fail, return zero defaults."""
        mock_roi = MagicMock()
        mock_roi.get_studio_metrics = AsyncMock(side_effect=Exception("DB down"))
        with (
            patch.object(service, "_get_from_cache", return_value=None),
            patch.object(service, "_set_cache", return_value=None),
            patch("app.services.roi_metrics_service.roi_metrics_service", mock_roi),
        ):
            data = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        assert data["roi"]["hours_saved"] == 0
