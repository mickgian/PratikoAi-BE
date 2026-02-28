"""DEV-359: Dashboard E2E Test Suite.

Tests DashboardService data aggregation, Redis caching, and cache invalidation.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service():
    from app.services.dashboard_service import DashboardService

    return DashboardService()


@pytest.fixture
def studio_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------


class TestDashboardCache:
    """Tests for _get_from_cache and _set_cache."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cache_hit(self, service, studio_id) -> None:
        cached_data = {"clients": {"total": 10}}
        with patch.object(service, "_get_from_cache", AsyncMock(return_value=cached_data)):
            mock_db = AsyncMock()
            result = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        assert result == cached_data
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cache_miss_queries_db(self, service, mock_db, studio_id) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch.object(service, "_get_from_cache", AsyncMock(return_value=None)),
            patch.object(service, "_set_cache", AsyncMock()),
            patch.object(service, "_get_client_stats", AsyncMock(return_value={"total": 5})),
            patch.object(
                service,
                "_get_communication_stats",
                AsyncMock(return_value={"total": 3, "pending_review": 1}),
            ),
            patch.object(
                service,
                "_get_procedure_stats",
                AsyncMock(return_value={"total": 2, "active": 1}),
            ),
            patch.object(service, "_get_match_stats", AsyncMock(return_value={"active_rules": 4})),
            patch.object(
                service,
                "_get_roi_stats",
                AsyncMock(return_value={"hours_saved": 10, "breakdown": {}}),
            ),
        ):
            result = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        assert result["clients"]["total"] == 5
        assert result["communications"]["total"] == 3
        assert result["procedures"]["total"] == 2
        assert result["matches"]["active_rules"] == 4

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_from_cache_returns_none_on_error(self, service, studio_id) -> None:
        with patch("app.services.cache.cache_service") as mock_cache:
            mock_cache._get_redis = AsyncMock(side_effect=Exception("Redis down"))
            result = await service._get_from_cache(studio_id)
        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_set_cache_swallows_errors(self, service, studio_id) -> None:
        with patch("app.services.cache.cache_service") as mock_cache:
            mock_cache._get_redis = AsyncMock(side_effect=Exception("Redis down"))
            await service._set_cache(studio_id, {"data": "test"})


# ---------------------------------------------------------------------------
# Aggregation section tests
# ---------------------------------------------------------------------------


class TestDashboardSections:
    """Tests for individual dashboard data sections."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_client_stats(self, service, mock_db, studio_id) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 42
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.dashboard_service.select"), patch("app.services.dashboard_service.func"):
            result = await service._get_client_stats(mock_db, studio_id)

        assert result["total"] == 42

    @pytest.mark.asyncio(loop_scope="function")
    async def test_communication_stats(self, service, mock_db, studio_id) -> None:
        mock_total = MagicMock()
        mock_total.scalar_one_or_none.return_value = 10
        mock_pending = MagicMock()
        mock_pending.scalar_one_or_none.return_value = 3
        mock_db.execute = AsyncMock(side_effect=[mock_total, mock_pending])

        with patch("app.services.dashboard_service.select"), patch("app.services.dashboard_service.func"):
            result = await service._get_communication_stats(mock_db, studio_id)

        assert result["total"] == 10
        assert result["pending_review"] == 3

    @pytest.mark.asyncio(loop_scope="function")
    async def test_procedure_stats(self, service, mock_db, studio_id) -> None:
        mock_total = MagicMock()
        mock_total.scalar_one_or_none.return_value = 8
        mock_active = MagicMock()
        mock_active.scalar_one_or_none.return_value = 5
        mock_db.execute = AsyncMock(side_effect=[mock_total, mock_active])

        with patch("app.services.dashboard_service.select"), patch("app.services.dashboard_service.func"):
            result = await service._get_procedure_stats(mock_db, studio_id)

        assert result["total"] == 8
        assert result["active"] == 5

    @pytest.mark.asyncio(loop_scope="function")
    async def test_match_stats(self, service, mock_db, studio_id) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 6
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.dashboard_service.select"), patch("app.services.dashboard_service.func"):
            result = await service._get_match_stats(mock_db, studio_id)

        assert result["active_rules"] == 6

    @pytest.mark.asyncio(loop_scope="function")
    async def test_roi_stats_fallback_on_error(self, service, mock_db, studio_id) -> None:
        with patch(
            "app.services.roi_metrics_service.roi_metrics_service",
        ) as mock_roi:
            mock_roi.get_studio_metrics = AsyncMock(side_effect=Exception("Not available"))
            result = await service._get_roi_stats(mock_db, studio_id)

        assert result["hours_saved"] == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_invalidate_cache(self, service, studio_id) -> None:
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock()

        with patch("app.services.cache.cache_service") as mock_cache:
            mock_cache._get_redis = AsyncMock(return_value=mock_redis)
            await service.invalidate_cache(studio_id)

        mock_redis.delete.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dashboard_data_structure(self, service, mock_db, studio_id) -> None:
        with (
            patch.object(service, "_get_from_cache", AsyncMock(return_value=None)),
            patch.object(service, "_set_cache", AsyncMock()),
            patch.object(service, "_get_client_stats", AsyncMock(return_value={"total": 0})),
            patch.object(
                service,
                "_get_communication_stats",
                AsyncMock(return_value={"total": 0, "pending_review": 0}),
            ),
            patch.object(
                service,
                "_get_procedure_stats",
                AsyncMock(return_value={"total": 0, "active": 0}),
            ),
            patch.object(service, "_get_match_stats", AsyncMock(return_value={"active_rules": 0})),
            patch.object(
                service,
                "_get_roi_stats",
                AsyncMock(return_value={"hours_saved": 0, "breakdown": {}}),
            ),
        ):
            result = await service.get_dashboard_data(mock_db, studio_id=studio_id)

        assert "clients" in result
        assert "communications" in result
        assert "procedures" in result
        assert "matches" in result
        assert "roi" in result
