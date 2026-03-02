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

    @pytest.mark.asyncio
    async def test_count_formulari_success(self) -> None:
        """_count_formulari returns count on success."""
        from unittest.mock import MagicMock

        from app.services.quick_action_counts_service import QuickActionCountsService

        svc = QuickActionCountsService()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 12
        mock_db.execute.return_value = mock_result

        result = await svc._count_formulari(mock_db)
        assert result == 12

    @pytest.mark.asyncio
    async def test_count_deadlines_success(self) -> None:
        """_count_deadlines returns count on success."""
        from unittest.mock import MagicMock

        from app.services.quick_action_counts_service import QuickActionCountsService

        svc = QuickActionCountsService()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 5
        mock_db.execute.return_value = mock_result

        result = await svc._count_deadlines(mock_db, uuid4())
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_urgent_notifications_success(self) -> None:
        """_count_urgent_notifications returns count on success."""
        from unittest.mock import MagicMock

        from app.services.quick_action_counts_service import QuickActionCountsService

        svc = QuickActionCountsService()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 3
        mock_db.execute.return_value = mock_result

        result = await svc._count_urgent_notifications(mock_db, uuid4())
        assert result == 3

    @pytest.mark.asyncio
    async def test_count_recent_normative_success(self) -> None:
        """_count_recent_normative returns count on success."""
        from unittest.mock import MagicMock

        from app.services.quick_action_counts_service import QuickActionCountsService

        svc = QuickActionCountsService()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 20
        mock_db.execute.return_value = mock_result

        result = await svc._count_recent_normative(mock_db)
        assert result == 20

    @pytest.mark.asyncio
    async def test_count_ready_questions_success(self) -> None:
        """_count_ready_questions returns count on success."""
        from unittest.mock import MagicMock

        from app.services.quick_action_counts_service import QuickActionCountsService

        svc = QuickActionCountsService()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 8
        mock_db.execute.return_value = mock_result

        result = await svc._count_ready_questions(mock_db, uuid4())
        assert result == 8

    @pytest.mark.asyncio
    async def test_count_faq_success(self) -> None:
        """_count_faq returns count on success."""
        from unittest.mock import MagicMock

        from app.services.quick_action_counts_service import QuickActionCountsService

        svc = QuickActionCountsService()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 42
        mock_db.execute.return_value = mock_result

        mock_faq = MagicMock()
        mock_faq.id = MagicMock()
        mock_faq.is_active = MagicMock()
        mock_faq.is_active.is_ = MagicMock(return_value=True)

        with patch("app.models.faq.FAQEntry", mock_faq):
            result = await svc._count_faq(mock_db)
        assert result == 42
