"""DEV-347: E2E Tests for Procedura Flow.

Tests ProceduraService lifecycle: retrieval, progress tracking,
checklist management, notes, document status, and completion analytics.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.procedura import ProceduraCategory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service():
    from app.services.procedura_service import ProceduraService

    return ProceduraService()


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def sample_procedura():
    proc = MagicMock()
    proc.id = uuid4()
    proc.code = "APERTURA_PIVA"
    proc.title = "Apertura Partita IVA"
    proc.description = "Procedura per aprire P.IVA"
    proc.category = ProceduraCategory.FISCALE
    proc.steps = [
        {"title": "Step 1", "checklist": ["item1", "item2"], "documents": ["doc1"]},
        {"title": "Step 2", "checklist": ["item3"], "documents": ["doc2"]},
        {"title": "Step 3", "checklist": [], "documents": []},
    ]
    proc.estimated_time_minutes = 60
    proc.is_active = True
    proc.to_dict.return_value = {"code": "APERTURA_PIVA", "title": "Apertura Partita IVA"}
    return proc


@pytest.fixture
def sample_progress():
    p = MagicMock()
    p.id = uuid4()
    p.user_id = 1
    p.studio_id = uuid4()
    p.procedura_id = uuid4()
    p.client_id = None
    p.current_step = 0
    p.completed_steps = []
    p.started_at = datetime.now(UTC)
    p.completed_at = None
    p.checklist_state = {}
    p.document_status = {}
    p.notes = None
    return p


# ---------------------------------------------------------------------------
# Procedure retrieval tests
# ---------------------------------------------------------------------------


class TestProceduraRetrieval:
    """Tests for get_by_code, get_by_id, list_active."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_by_code_found(self, service, mock_db, sample_procedura) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_procedura
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.procedura_service.select"), patch("app.services.procedura_service.and_"):
            result = await service.get_by_code(mock_db, code="APERTURA_PIVA")

        assert result is sample_procedura

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_by_code_not_found(self, service, mock_db) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.procedura_service.select"):
            result = await service.get_by_code(mock_db, code="NONEXISTENT")

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_by_id_found(self, service, mock_db, sample_procedura) -> None:
        mock_db.get = AsyncMock(return_value=sample_procedura)
        result = await service.get_by_id(mock_db, procedura_id=sample_procedura.id)
        assert result is sample_procedura

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_by_id_not_found(self, service, mock_db) -> None:
        mock_db.get = AsyncMock(return_value=None)
        result = await service.get_by_id(mock_db, procedura_id=uuid4())
        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_active(self, service, mock_db, sample_procedura) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_procedura]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.procedura_service.select"):
            result = await service.list_active(mock_db)

        assert len(result) == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_active_with_category(self, service, mock_db) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.procedura_service.select"):
            result = await service.list_active(mock_db, category=ProceduraCategory.LAVORO)

        assert result == []


# ---------------------------------------------------------------------------
# Progress tracking tests
# ---------------------------------------------------------------------------


class TestProgressTracking:
    """Tests for start_progress, advance_step, get_progress."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_start_progress(self, service, mock_db, studio_id) -> None:
        proc_id = uuid4()

        # No existing progress
        with (
            patch.object(service, "_get_active_progress", AsyncMock(return_value=None)),
            patch("app.services.procedura_service.ProceduraProgress") as mock_pp,
        ):
            mock_instance = MagicMock()
            mock_instance.user_id = 1
            mock_instance.procedura_id = proc_id
            mock_instance.current_step = 0
            mock_pp.return_value = mock_instance

            result = await service.start_progress(mock_db, user_id=1, studio_id=studio_id, procedura_id=proc_id)

        assert result.user_id == 1
        assert result.current_step == 0
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_start_progress_already_exists(self, service, mock_db, studio_id) -> None:
        existing = MagicMock()

        with (
            patch.object(service, "_get_active_progress", AsyncMock(return_value=existing)),
            pytest.raises(ValueError, match="già esistente"),
        ):
            await service.start_progress(mock_db, user_id=1, studio_id=studio_id, procedura_id=uuid4())

    @pytest.mark.asyncio(loop_scope="function")
    async def test_advance_step(self, service, mock_db, sample_progress, sample_procedura) -> None:
        sample_progress.current_step = 0
        sample_progress.completed_steps = []
        sample_progress.procedura_id = sample_procedura.id

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = sample_progress
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = sample_procedura
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        with patch("app.services.procedura_service.select"):
            result = await service.advance_step(mock_db, progress_id=sample_progress.id)

        assert result is sample_progress
        assert sample_progress.current_step == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_advance_step_completes(self, service, mock_db, sample_progress, sample_procedura) -> None:
        sample_progress.current_step = 2  # Last step
        sample_progress.completed_steps = [0, 1]
        sample_progress.procedura_id = sample_procedura.id

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = sample_progress
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = sample_procedura
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        with patch("app.services.procedura_service.select"):
            result = await service.advance_step(mock_db, progress_id=sample_progress.id)

        assert result.completed_at is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_advance_step_not_found(self, service, mock_db) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.procedura_service.select"):
            result = await service.advance_step(mock_db, progress_id=uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# Checklist and notes tests
# ---------------------------------------------------------------------------


class TestChecklistAndNotes:
    """Tests for update_checklist_item, update_notes, update_document_status."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_checklist_item(self, service, mock_db, sample_progress, sample_procedura) -> None:
        sample_progress.checklist_state = {}
        sample_progress.procedura_id = sample_procedura.id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_progress
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.get = AsyncMock(return_value=sample_procedura)

        with patch("app.services.procedura_service.select"):
            result = await service.update_checklist_item(
                mock_db, progress_id=sample_progress.id, step_index=0, item_index=0, completed=True
            )

        assert result is sample_progress
        assert sample_progress.checklist_state == {"0": {"0": True}}

    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_checklist_invalid_step(self, service, mock_db, sample_progress, sample_procedura) -> None:
        sample_progress.procedura_id = sample_procedura.id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_progress
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.get = AsyncMock(return_value=sample_procedura)

        with (
            patch("app.services.procedura_service.select"),
            pytest.raises(ValueError, match="step non valido"),
        ):
            await service.update_checklist_item(
                mock_db, progress_id=sample_progress.id, step_index=99, item_index=0, completed=True
            )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_notes(self, service, mock_db, sample_progress) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_progress
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.procedura_service.select"):
            result = await service.update_notes(mock_db, progress_id=sample_progress.id, notes="Nota importante")

        assert result.notes == "Nota importante"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_document_status(self, service, mock_db, sample_progress, sample_procedura) -> None:
        sample_progress.document_status = {}
        sample_progress.procedura_id = sample_procedura.id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_progress
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.get = AsyncMock(return_value=sample_procedura)

        with patch("app.services.procedura_service.select"):
            result = await service.update_document_status(
                mock_db, progress_id=sample_progress.id, document_name="doc1", verified=True
            )

        assert result.document_status == {"doc1": True}

    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_document_status_invalid_name(
        self, service, mock_db, sample_progress, sample_procedura
    ) -> None:
        sample_progress.document_status = {}
        sample_progress.procedura_id = sample_procedura.id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_progress
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.get = AsyncMock(return_value=sample_procedura)

        with (
            patch("app.services.procedura_service.select"),
            pytest.raises(ValueError, match="non è presente"),
        ):
            await service.update_document_status(
                mock_db, progress_id=sample_progress.id, document_name="nonexistent", verified=True
            )


# ---------------------------------------------------------------------------
# Completion analytics tests
# ---------------------------------------------------------------------------


class TestCompletionAnalytics:
    """Tests for get_completion_analytics."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_analytics_with_completed_records(self, service, mock_db, studio_id) -> None:
        now = datetime.now(UTC)
        record1 = MagicMock()
        record1.completed_at = now
        record1.started_at = now - timedelta(hours=2)
        record2 = MagicMock()
        record2.completed_at = None
        record2.started_at = now - timedelta(hours=1)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [record1, record2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.procedura_service.select"):
            result = await service.get_completion_analytics(mock_db, studio_id=studio_id)

        assert result["total_started"] == 2
        assert result["total_completed"] == 1
        assert result["completion_rate"] == 0.5
        assert result["avg_completion_seconds"] is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_analytics_empty_studio(self, service, mock_db, studio_id) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.procedura_service.select"):
            result = await service.get_completion_analytics(mock_db, studio_id=studio_id)

        assert result["total_started"] == 0
        assert result["completion_rate"] == 0.0
        assert result["avg_completion_seconds"] is None
