"""DEV-434: Tests for Dashboard Client Distribution Charts."""

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


class TestClientDistributionByRegime:
    """Test get_client_distribution_by_regime()."""

    @pytest.mark.asyncio
    async def test_returns_grouped_data(self, svc, mock_db, studio_id) -> None:
        """Happy path: returns regime distribution."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("forfettario", 10),
            ("ordinario", 5),
            ("semplificato", 3),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_client_distribution_by_regime(mock_db, studio_id=studio_id)
        assert len(result) == 3
        assert result[0]["regime"] == "forfettario"
        assert result[0]["count"] == 10

    @pytest.mark.asyncio
    async def test_empty_studio(self, svc, mock_db, studio_id) -> None:
        """Edge case: no clients in studio."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_client_distribution_by_regime(mock_db, studio_id=studio_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_failure_returns_empty(self, svc, mock_db, studio_id) -> None:
        """Error: returns empty list on failure."""
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
        result = await svc.get_client_distribution_by_regime(mock_db, studio_id=studio_id)
        assert result == []


class TestClientDistributionByAteco:
    """Test get_client_distribution_by_ateco()."""

    @pytest.mark.asyncio
    async def test_returns_grouped_data(self, svc, mock_db, studio_id) -> None:
        """Happy path: returns ATECO distribution."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("62.01.00", 8),
            ("41.20.00", 4),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_client_distribution_by_ateco(mock_db, studio_id=studio_id)
        assert len(result) == 2
        assert result[0]["ateco"] == "62.01.00"

    @pytest.mark.asyncio
    async def test_empty_studio(self, svc, mock_db, studio_id) -> None:
        """Empty studio returns empty list."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_client_distribution_by_ateco(mock_db, studio_id=studio_id)
        assert result == []


class TestClientDistributionByStatus:
    """Test get_client_distribution_by_status()."""

    @pytest.mark.asyncio
    async def test_returns_grouped_data(self, svc, mock_db, studio_id) -> None:
        """Happy path: returns status distribution."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("attivo", 15),
            ("prospect", 5),
            ("cessato", 2),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_client_distribution_by_status(mock_db, studio_id=studio_id)
        assert len(result) == 3
        assert result[0]["status"] == "attivo"
        assert result[0]["count"] == 15

    @pytest.mark.asyncio
    async def test_failure_returns_empty(self, svc, mock_db, studio_id) -> None:
        """Error: returns empty list on failure."""
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
        result = await svc.get_client_distribution_by_status(mock_db, studio_id=studio_id)
        assert result == []
