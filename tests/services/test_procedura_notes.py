"""DEV-344: Tests for ProceduraService notes and document checklist.

TDD RED phase: These tests define the expected behaviour of progress notes
and document-status management within ProceduraService.
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
            {
                "index": 0,
                "title": "Raccolta documenti",
                "checklist": ["CI", "CF"],
                "documents": ["Carta Identita", "Codice Fiscale"],
            },
            {
                "index": 1,
                "title": "Compilazione modello AA9/12",
                "checklist": ["Modello compilato"],
                "documents": ["Modello AA9/12"],
            },
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
        notes=None,
        document_status={},
    )


# ---------------------------------------------------------------------------
# Tests — update_notes
# ---------------------------------------------------------------------------


class TestProceduraUpdateNotes:
    """Test ProceduraService.update_notes()."""

    @pytest.mark.asyncio
    async def test_update_notes(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
    ) -> None:
        """Happy path: update free-text progress notes."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_progress)))

        result = await proc_service.update_notes(
            db=mock_db,
            progress_id=sample_progress.id,
            notes="Cliente ha consegnato CI e CF. Manca tessera sanitaria.",
        )

        assert result is not None
        assert result.notes == "Cliente ha consegnato CI e CF. Manca tessera sanitaria."
        mock_db.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_clear_notes(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
    ) -> None:
        """Edge case: set notes to None to clear them."""
        sample_progress.notes = "Note precedenti da cancellare."
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_progress)))

        result = await proc_service.update_notes(
            db=mock_db,
            progress_id=sample_progress.id,
            notes=None,
        )

        assert result is not None
        assert result.notes is None


# ---------------------------------------------------------------------------
# Tests — update_document_status
# ---------------------------------------------------------------------------


class TestProceduraDocumentStatus:
    """Test ProceduraService.update_document_status()."""

    @pytest.mark.asyncio
    async def test_update_document_status_verified(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Happy path: mark a required document as verified."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_progress)))
        mock_db.get = AsyncMock(return_value=sample_procedura)

        result = await proc_service.update_document_status(
            db=mock_db,
            progress_id=sample_progress.id,
            document_name="Carta Identita",
            verified=True,
        )

        assert result is not None
        assert result.document_status["Carta Identita"] is True

    @pytest.mark.asyncio
    async def test_update_document_status_unverified(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Unmark a previously verified document."""
        sample_progress.document_status = {"Carta Identita": True}

        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_progress)))
        mock_db.get = AsyncMock(return_value=sample_procedura)

        result = await proc_service.update_document_status(
            db=mock_db,
            progress_id=sample_progress.id,
            document_name="Carta Identita",
            verified=False,
        )

        assert result is not None
        assert result.document_status["Carta Identita"] is False

    @pytest.mark.asyncio
    async def test_document_not_in_procedure_raises(
        self,
        proc_service: ProceduraService,
        mock_db: AsyncMock,
        sample_progress: ProceduraProgress,
        sample_procedura: Procedura,
    ) -> None:
        """Error: document name not listed in any step must raise ValueError."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_progress)))
        mock_db.get = AsyncMock(return_value=sample_procedura)

        with pytest.raises(ValueError, match="documento.*non.*presente.*procedura"):
            await proc_service.update_document_status(
                db=mock_db,
                progress_id=sample_progress.id,
                document_name="Passaporto Intergalattico",
                verified=True,
            )
