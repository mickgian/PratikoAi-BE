"""DEV-340: Tests for ProceduraService with Progress Tracking."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.procedura import Procedura, ProceduraCategory
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


@pytest.fixture
def sample_procedura() -> Procedura:
    return Procedura(
        id=uuid4(),
        code="APERTURA_PIVA",
        title="Apertura Partita IVA",
        description="Procedura per apertura P.IVA.",
        category=ProceduraCategory.FISCALE,
        steps=[
            {"index": 0, "title": "Raccolta documenti", "checklist": ["CI", "CF"]},
            {"index": 1, "title": "Compilazione modello AA9/12", "checklist": ["Modello compilato"]},
            {"index": 2, "title": "Invio telematico", "checklist": ["Ricevuta invio"]},
        ],
        estimated_time_minutes=60,
        version=1,
        is_active=True,
    )


@pytest.fixture
def sample_progress(studio_id, sample_procedura) -> ProceduraProgress:
    return ProceduraProgress(
        id=uuid4(),
        user_id=1,
        studio_id=studio_id,
        procedura_id=sample_procedura.id,
        current_step=0,
        completed_steps=[],
    )


class TestProceduraServiceGetProcedure:
    """Test ProceduraService procedure retrieval."""

    @pytest.mark.asyncio
    async def test_get_by_code_found(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_procedura: Procedura,
    ) -> None:
        """Happy path: get procedure by code."""
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_procedura))
        )

        result = await proc_service.get_by_code(db=mock_db, code="APERTURA_PIVA")

        assert result is not None
        assert result.code == "APERTURA_PIVA"

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self, proc_service: ProceduraService, mock_db: AsyncMock) -> None:
        """Error: non-existent code returns None."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await proc_service.get_by_code(db=mock_db, code="NON_ESISTE")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_active(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_procedura: Procedura,
    ) -> None:
        """Happy path: list active procedures."""
        mock_db.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_procedura])))
            )
        )

        result = await proc_service.list_active(db=mock_db)

        assert len(result) == 1


class TestProceduraServiceProgress:
    """Test ProceduraService progress tracking."""

    @pytest.mark.asyncio
    async def test_start_progress(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_procedura: Procedura,
        studio_id,
    ) -> None:
        """Happy path: start a new progress record."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await proc_service.start_progress(
            db=mock_db,
            user_id=1,
            studio_id=studio_id,
            procedura_id=sample_procedura.id,
        )

        assert result.current_step == 0
        assert result.completed_steps == []
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_progress_already_exists(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        studio_id,
    ) -> None:
        """Error: user already has progress for this procedure."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_progress)))

        with pytest.raises(ValueError, match="progresso.*già esistente"):
            await proc_service.start_progress(
                db=mock_db,
                user_id=1,
                studio_id=studio_id,
                procedura_id=sample_progress.procedura_id,
            )

    @pytest.mark.asyncio
    async def test_advance_step(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Happy path: advance to next step."""
        # First call for progress, second for procedura
        mock_db.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=sample_progress)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=sample_procedura)),
            ]
        )

        result = await proc_service.advance_step(db=mock_db, progress_id=sample_progress.id)

        assert result is not None
        assert result.current_step == 1
        assert 0 in result.completed_steps

    @pytest.mark.asyncio
    async def test_advance_step_completes_procedure(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Edge case: advancing past last step completes the procedure."""
        sample_progress.current_step = 2
        sample_progress.completed_steps = [0, 1]

        mock_db.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=sample_progress)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=sample_procedura)),
            ]
        )

        result = await proc_service.advance_step(db=mock_db, progress_id=sample_progress.id)

        assert result is not None
        assert result.completed_at is not None
        assert result.is_completed

    @pytest.mark.asyncio
    async def test_get_progress(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        studio_id,
    ) -> None:
        """Happy path: get user progress."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_progress)))

        result = await proc_service.get_progress(
            db=mock_db,
            user_id=1,
            studio_id=studio_id,
            procedura_id=sample_progress.procedura_id,
        )

        assert result is not None
        assert result.user_id == 1
