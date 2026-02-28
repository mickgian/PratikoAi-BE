"""Tests for DEV-404: Generic vs Client-Specific Procedure Logic Split."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock
from uuid import uuid4

import pytest

from app.services.procedura_service import ProceduraService


@pytest.fixture
def service():
    return ProceduraService()


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def studio_id():
    return uuid4()


class TestGenericConsultationMode:
    """Generic mode: read-only, no side effects (no ProceduraProgress)."""

    @pytest.mark.asyncio
    async def test_get_by_code_is_readonly(self, service, mock_db):
        """get_by_code does not create progress records."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(code="TEST")
        mock_db.execute.return_value = mock_result

        proc = await service.get_by_code(mock_db, code="TEST")
        assert proc is not None
        # Ensure no flush/commit (no side effects)
        mock_db.add.assert_not_called()
        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_active_is_readonly(self, service, mock_db):
        """list_active does not create progress records."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        procs = await service.list_active(mock_db)
        assert isinstance(procs, list)
        mock_db.add.assert_not_called()
        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_id_is_readonly(self, service, mock_db):
        """get_by_id does not create progress records."""
        mock_db.get.return_value = MagicMock()
        await service.get_by_id(mock_db, procedura_id=uuid4())
        mock_db.add.assert_not_called()


class TestClientSpecificTrackingMode:
    """Client-specific mode: creates ProceduraProgress records."""

    @pytest.mark.asyncio
    async def test_start_progress_creates_record(self, service, mock_db, studio_id):
        """start_progress creates a ProceduraProgress (tracking mode)."""
        proc_id = uuid4()
        # No existing progress
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        progress = await service.start_progress(
            mock_db,
            user_id=1,
            studio_id=studio_id,
            procedura_id=proc_id,
            client_id=42,
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        assert progress.client_id == 42

    @pytest.mark.asyncio
    async def test_start_progress_without_client(self, service, mock_db, studio_id):
        """start_progress works without client_id (generic tracking)."""
        proc_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        progress = await service.start_progress(
            mock_db,
            user_id=1,
            studio_id=studio_id,
            procedura_id=proc_id,
        )

        assert progress.client_id is None

    @pytest.mark.asyncio
    async def test_duplicate_progress_raises(self, service, mock_db, studio_id):
        """Cannot start duplicate progress for same user/procedure."""
        proc_id = uuid4()
        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="già esistente"):
            await service.start_progress(
                mock_db,
                user_id=1,
                studio_id=studio_id,
                procedura_id=proc_id,
            )


class TestLogicSplitIntegration:
    """Verify clear separation between generic and tracking modes."""

    def test_read_only_methods_exist(self, service):
        """Verify all read-only methods exist."""
        assert hasattr(service, "get_by_code")
        assert hasattr(service, "get_by_id")
        assert hasattr(service, "list_active")

    def test_tracking_methods_exist(self, service):
        """Verify all tracking methods exist."""
        assert hasattr(service, "start_progress")
        assert hasattr(service, "advance_step")
        assert hasattr(service, "get_progress")
        assert hasattr(service, "list_user_progress")
        assert hasattr(service, "update_checklist_item")
        assert hasattr(service, "update_notes")
        assert hasattr(service, "update_document_status")

    def test_analytics_methods_exist(self, service):
        """Verify analytics method exists."""
        assert hasattr(service, "get_completion_analytics")
