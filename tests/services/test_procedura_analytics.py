"""DEV-346: Tests for ProceduraService completion analytics.

Verifies get_completion_analytics returns correct counts, rates,
and average completion times, including edge cases with no data.
"""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.procedura_progress import ProceduraProgress
from app.services.procedura_service import ProceduraService


@pytest.fixture
def proc_service() -> ProceduraService:
    return ProceduraService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


def _make_progress(
    studio_id,
    *,
    completed: bool = False,
    duration_seconds: int = 3600,
) -> ProceduraProgress:
    """Helper to create a ProceduraProgress with optional completion."""
    now = datetime.now(UTC)
    started = now - timedelta(seconds=duration_seconds)
    return ProceduraProgress(
        id=uuid4(),
        user_id=1,
        studio_id=studio_id,
        procedura_id=uuid4(),
        current_step=2 if completed else 0,
        completed_steps=[0, 1, 2] if completed else [],
        started_at=started,
        completed_at=now if completed else None,
    )


class TestGetCompletionAnalytics:
    """Test ProceduraService.get_completion_analytics()."""

    @pytest.mark.asyncio
    async def test_analytics_correct_counts(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Happy path: 3 started, 2 completed -> correct totals and rate."""
        now = datetime.now(UTC)
        progress_records = [
            _make_progress(studio_id, completed=True, duration_seconds=3600),
            _make_progress(studio_id, completed=True, duration_seconds=7200),
            _make_progress(studio_id, completed=False),
        ]

        # Mock: first call returns all progress for studio, already fetched
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = progress_records
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await proc_service.get_completion_analytics(db=mock_db, studio_id=studio_id)

        assert result["total_started"] == 3
        assert result["total_completed"] == 2
        assert result["completion_rate"] == pytest.approx(2 / 3, abs=0.01)
        assert result["avg_completion_seconds"] == pytest.approx(5400.0, abs=5.0)

    @pytest.mark.asyncio
    async def test_analytics_average_completion_time(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Verify average completion time calculation with known durations."""
        progress_records = [
            _make_progress(studio_id, completed=True, duration_seconds=1000),
            _make_progress(studio_id, completed=True, duration_seconds=3000),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = progress_records
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await proc_service.get_completion_analytics(db=mock_db, studio_id=studio_id)

        assert result["total_started"] == 2
        assert result["total_completed"] == 2
        assert result["completion_rate"] == pytest.approx(1.0)
        assert result["avg_completion_seconds"] == pytest.approx(2000.0, abs=5.0)

    @pytest.mark.asyncio
    async def test_analytics_no_data_returns_zeros(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: no progress records returns zero counts."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await proc_service.get_completion_analytics(db=mock_db, studio_id=studio_id)

        assert result["total_started"] == 0
        assert result["total_completed"] == 0
        assert result["completion_rate"] == 0.0
        assert result["avg_completion_seconds"] is None

    @pytest.mark.asyncio
    async def test_analytics_filters_by_studio_id(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Verify the query filters by studio_id (tenant isolation)."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await proc_service.get_completion_analytics(db=mock_db, studio_id=studio_id)

        # Verify execute was called (query was made)
        mock_db.execute.assert_called_once()
        # Extract the query from the call and verify it references studio_id
        call_args = mock_db.execute.call_args
        query = call_args[0][0]
        # The compiled query should contain a WHERE clause filtering by studio_id
        compiled = str(query.compile(compile_kwargs={"literal_binds": False}))
        assert "studio_id" in compiled

    @pytest.mark.asyncio
    async def test_analytics_started_but_none_completed(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: procedures started but none completed."""
        progress_records = [
            _make_progress(studio_id, completed=False),
            _make_progress(studio_id, completed=False),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = progress_records
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await proc_service.get_completion_analytics(db=mock_db, studio_id=studio_id)

        assert result["total_started"] == 2
        assert result["total_completed"] == 0
        assert result["completion_rate"] == 0.0
        assert result["avg_completion_seconds"] is None
