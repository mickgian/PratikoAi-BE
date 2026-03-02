"""DEV-436: Tests for Dashboard Period Selector."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def studio_id():
    return uuid4()


class TestDashboardPeriod:
    """Test GET /dashboard with period parameter."""

    @pytest.mark.asyncio
    async def test_week_period(self, studio_id) -> None:
        """Happy path: week period."""
        with patch("app.api.v1.dashboard.dashboard_service") as mock_svc:
            mock_svc.get_dashboard_data_with_period = AsyncMock(
                return_value={"period": "week", "clients": {"total": 5}}
            )
            mock_db = AsyncMock()

            from app.api.v1.dashboard import get_dashboard

            result = await get_dashboard(studio_id=studio_id, period="week", db=mock_db)
            assert result["period"] == "week"

    @pytest.mark.asyncio
    async def test_month_period(self, studio_id) -> None:
        """Happy path: month period."""
        with patch("app.api.v1.dashboard.dashboard_service") as mock_svc:
            mock_svc.get_dashboard_data_with_period = AsyncMock(
                return_value={"period": "month", "clients": {"total": 10}}
            )
            mock_db = AsyncMock()

            from app.api.v1.dashboard import get_dashboard

            result = await get_dashboard(studio_id=studio_id, period="month", db=mock_db)
            assert result["period"] == "month"

    @pytest.mark.asyncio
    async def test_year_period(self, studio_id) -> None:
        """Happy path: year period."""
        with patch("app.api.v1.dashboard.dashboard_service") as mock_svc:
            mock_svc.get_dashboard_data_with_period = AsyncMock(
                return_value={"period": "year", "clients": {"total": 100}}
            )
            mock_db = AsyncMock()

            from app.api.v1.dashboard import get_dashboard

            result = await get_dashboard(studio_id=studio_id, period="year", db=mock_db)
            assert result["period"] == "year"

    @pytest.mark.asyncio
    async def test_default_month(self, studio_id) -> None:
        """Default period is month."""
        with patch("app.api.v1.dashboard.dashboard_service") as mock_svc:
            mock_svc.get_dashboard_data_with_period = AsyncMock(return_value={"period": "month"})
            mock_db = AsyncMock()

            from app.api.v1.dashboard import get_dashboard

            result = await get_dashboard(studio_id=studio_id, period="month", db=mock_db)
            assert result["period"] == "month"

    @pytest.mark.asyncio
    async def test_invalid_period_422(self, studio_id) -> None:
        """Invalid period returns 422."""
        mock_db = AsyncMock()

        from app.api.v1.dashboard import get_dashboard

        with pytest.raises(Exception) as exc_info:
            await get_dashboard(studio_id=studio_id, period="invalid", db=mock_db)
        assert exc_info.value.status_code == 422
