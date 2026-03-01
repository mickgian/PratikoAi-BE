"""DEV-435: Tests for Dashboard Matching Statistics."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.dashboard_service import DashboardService


@pytest.fixture
def svc() -> DashboardService:
    return DashboardService()


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def studio_id():
    return uuid4()


class TestMatchingStatistics:
    """Test get_matching_statistics()."""

    @pytest.mark.asyncio
    async def test_total_count(self, svc, mock_db, studio_id) -> None:
        """Happy path: returns total matches."""
        # Three queries: total, actioned, pending
        results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=100)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=75)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=25)),
        ]
        mock_db.execute = AsyncMock(side_effect=results)

        result = await svc.get_matching_statistics(mock_db, studio_id=studio_id)
        assert result["total_matches"] == 100
        assert result["conversion_rate"] == 75.0
        assert result["pending_reviews"] == 25

    @pytest.mark.asyncio
    async def test_empty_returns_zeros(self, svc, mock_db, studio_id) -> None:
        """Edge case: no matches returns zeros."""
        results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=0)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=0)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=0)),
        ]
        mock_db.execute = AsyncMock(side_effect=results)

        result = await svc.get_matching_statistics(mock_db, studio_id=studio_id)
        assert result["total_matches"] == 0
        assert result["conversion_rate"] == 0.0
        assert result["pending_reviews"] == 0

    @pytest.mark.asyncio
    async def test_failure_returns_defaults(self, svc, mock_db, studio_id) -> None:
        """Error: returns default values on failure."""
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))

        result = await svc.get_matching_statistics(mock_db, studio_id=studio_id)
        assert result["total_matches"] == 0
        assert result["conversion_rate"] == 0.0
        assert result["pending_reviews"] == 0

    @pytest.mark.asyncio
    async def test_conversion_rate_calculation(self, svc, mock_db, studio_id) -> None:
        """Conversion rate is actioned/total * 100."""
        results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=200)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=50)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=150)),
        ]
        mock_db.execute = AsyncMock(side_effect=results)

        result = await svc.get_matching_statistics(mock_db, studio_id=studio_id)
        assert result["conversion_rate"] == 25.0
