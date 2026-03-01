"""DEV-430: Tests for Quick Action Counts API."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def studio_id():
    return uuid4()


class TestGetQuickActionCounts:
    """Test GET /quick-actions/counts."""

    @pytest.mark.asyncio
    async def test_returns_six_counts(self, studio_id) -> None:
        """Happy path: returns 6 count categories."""
        expected = {
            "modelli_formulari": 7,
            "scadenze_fiscali": 3,
            "aggiornamenti_urgenti": 2,
            "normative_recenti": 15,
            "domande_pronte": 5,
            "faq": 42,
        }
        with patch("app.api.v1.quick_actions.quick_action_counts_service") as mock_svc:
            mock_svc.get_counts = AsyncMock(return_value=expected)
            mock_db = AsyncMock()

            from app.api.v1.quick_actions import get_quick_action_counts

            result = await get_quick_action_counts(x_studio_id=studio_id, db=mock_db)
            assert len(result) == 6
            assert result["modelli_formulari"] == 7
            assert result["faq"] == 42

    @pytest.mark.asyncio
    async def test_empty_studio_all_zeros(self, studio_id) -> None:
        """Edge case: empty studio returns all zeros."""
        expected = {
            "modelli_formulari": 0,
            "scadenze_fiscali": 0,
            "aggiornamenti_urgenti": 0,
            "normative_recenti": 0,
            "domande_pronte": 0,
            "faq": 0,
        }
        with patch("app.api.v1.quick_actions.quick_action_counts_service") as mock_svc:
            mock_svc.get_counts = AsyncMock(return_value=expected)
            mock_db = AsyncMock()

            from app.api.v1.quick_actions import get_quick_action_counts

            result = await get_quick_action_counts(x_studio_id=studio_id, db=mock_db)
            assert all(v == 0 for v in result.values())


class TestQuickActionCountsService:
    """Test QuickActionCountsService partial failure graceful degradation."""

    @pytest.mark.asyncio
    async def test_partial_failure_returns_zero(self) -> None:
        """Partial service failure returns 0 for that category."""
        from app.services.quick_action_counts_service import QuickActionCountsService

        svc = QuickActionCountsService()
        mock_db = AsyncMock()
        # All db.execute calls raise
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
        studio_id = uuid4()

        with (
            patch.object(svc, "_get_from_cache", return_value=None),
            patch.object(svc, "_set_cache", return_value=None),
        ):
            result = await svc.get_counts(mock_db, studio_id=studio_id)

        assert len(result) == 6
        assert all(v == 0 for v in result.values())

    @pytest.mark.asyncio
    async def test_cache_hit(self) -> None:
        """Cache hit returns cached data without DB queries."""
        from app.services.quick_action_counts_service import QuickActionCountsService

        svc = QuickActionCountsService()
        mock_db = AsyncMock()
        studio_id = uuid4()
        cached = {
            "modelli_formulari": 5,
            "scadenze_fiscali": 3,
            "aggiornamenti_urgenti": 0,
            "normative_recenti": 10,
            "domande_pronte": 2,
            "faq": 20,
        }

        with patch.object(svc, "_get_from_cache", return_value=cached):
            result = await svc.get_counts(mock_db, studio_id=studio_id)

        assert result == cached
        mock_db.execute.assert_not_called()
