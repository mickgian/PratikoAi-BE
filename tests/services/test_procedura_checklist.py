"""DEV-343: Tests for ProceduraService.update_checklist_item — Checklist tracking.

TDD RED phase: These tests define the expected behaviour of checklist item
toggling within procedura steps.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.procedura import Procedura, ProceduraCategory
from app.models.procedura_progress import ProceduraProgress
from app.services.procedura_service import ProceduraService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    session.delete = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def sample_procedura() -> Procedura:
    return Procedura(
        id=uuid4(),
        code="APERTURA_PIVA",
        title="Apertura Partita IVA",
        description="Procedura per apertura P.IVA.",
        category=ProceduraCategory.FISCALE,
        steps=[
            {"index": 0, "title": "Raccolta documenti", "checklist": ["CI", "CF", "Tessera sanitaria"]},
            {"index": 1, "title": "Compilazione modello AA9/12", "checklist": ["Modello compilato", "Firma"]},
            {"index": 2, "title": "Invio telematico", "checklist": ["Ricevuta invio"]},
        ],
        estimated_time_minutes=60,
        version=1,
        is_active=True,
    )


@pytest.fixture
def sample_progress(studio_id, sample_procedura) -> ProceduraProgress:
    """Progress with an empty checklist_state JSONB (default)."""
    return ProceduraProgress(
        id=uuid4(),
        user_id=1,
        studio_id=studio_id,
        procedura_id=sample_procedura.id,
        current_step=0,
        completed_steps=[],
        checklist_state={},
    )


def _mock_progress_and_proc(mock_db, progress, procedura):
    """Set up mock_db to return progress then procedura via db.execute and db.get."""
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=progress)))
    mock_db.get = AsyncMock(return_value=procedura)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProceduraChecklist:
    """Test ProceduraService.update_checklist_item()."""

    @pytest.mark.asyncio
    async def test_update_checklist_item_complete(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Happy path: mark a checklist item as complete."""
        _mock_progress_and_proc(mock_db, sample_progress, sample_procedura)

        result = await proc_service.update_checklist_item(
            db=mock_db,
            progress_id=sample_progress.id,
            step_index=0,
            item_index=0,
            completed=True,
        )

        assert result is not None
        assert result.checklist_state.get("0", {}).get("0") is True

    @pytest.mark.asyncio
    async def test_update_checklist_item_uncomplete(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Unmark a previously completed checklist item."""
        sample_progress.checklist_state = {"0": {"0": True}}
        _mock_progress_and_proc(mock_db, sample_progress, sample_procedura)

        result = await proc_service.update_checklist_item(
            db=mock_db,
            progress_id=sample_progress.id,
            step_index=0,
            item_index=0,
            completed=False,
        )

        assert result is not None
        assert result.checklist_state.get("0", {}).get("0") is False

    @pytest.mark.asyncio
    async def test_invalid_step_index_raises(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Error: step index out of bounds must raise ValueError."""
        _mock_progress_and_proc(mock_db, sample_progress, sample_procedura)

        with pytest.raises(ValueError, match="[Ii]ndice.*step.*non valido"):
            await proc_service.update_checklist_item(
                db=mock_db,
                progress_id=sample_progress.id,
                step_index=99,
                item_index=0,
                completed=True,
            )

    @pytest.mark.asyncio
    async def test_invalid_item_index_raises(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Error: item index out of bounds must raise ValueError."""
        _mock_progress_and_proc(mock_db, sample_progress, sample_procedura)

        with pytest.raises(ValueError, match="[Ii]ndice.*item.*checklist.*non valido"):
            await proc_service.update_checklist_item(
                db=mock_db,
                progress_id=sample_progress.id,
                step_index=0,
                item_index=99,
                completed=True,
            )

    @pytest.mark.asyncio
    async def test_checklist_state_persisted(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Checklist state must persist across multiple update calls."""
        _mock_progress_and_proc(mock_db, sample_progress, sample_procedura)

        # Complete item 0 of step 0
        await proc_service.update_checklist_item(
            db=mock_db,
            progress_id=sample_progress.id,
            step_index=0,
            item_index=0,
            completed=True,
        )

        # Complete item 1 of step 0 (re-mock since db.execute was consumed)
        _mock_progress_and_proc(mock_db, sample_progress, sample_procedura)

        result = await proc_service.update_checklist_item(
            db=mock_db,
            progress_id=sample_progress.id,
            step_index=0,
            item_index=1,
            completed=True,
        )

        assert result is not None
        assert result.checklist_state.get("0", {}).get("0") is True
        assert result.checklist_state.get("0", {}).get("1") is True
