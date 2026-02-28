"""DEV-339: E2E Tests for Communication Workflow.

Tests the CommunicationService state machine:
DRAFT -> PENDING_REVIEW -> APPROVED -> SENT (or REJECTED / FAILED).
Self-approval prevention, bulk draft creation, and audit logging.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.communication import CanaleInvio, StatoComunicazione

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def mock_audit():
    with patch("app.services.communication_service.security_audit_logger") as m:
        m.log_security_event = AsyncMock()
        yield m


def _make_service():
    """Import and create service inside test to use mock_audit context."""
    from app.services.communication_service import CommunicationService

    return CommunicationService()


def _make_comm_factory():
    """Create a factory for Communication mock objects."""

    def factory(**kwargs):
        obj = MagicMock()
        for k, v in kwargs.items():
            setattr(obj, k, v)
        if "id" not in kwargs:
            obj.id = uuid4()
        if "created_at" not in kwargs:
            obj.created_at = datetime.now(UTC)
        return obj

    return factory


# ---------------------------------------------------------------------------
# Draft creation tests
# ---------------------------------------------------------------------------


class TestCommunicationDraftCreation:
    """Tests for CommunicationService.create_draft."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_draft_success(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        with patch(
            "app.services.communication_service.Communication",
            side_effect=_make_comm_factory(),
        ):
            svc = _make_service()
            result = await svc.create_draft(
                mock_db,
                studio_id=studio_id,
                subject="Test",
                content="Body",
                channel=CanaleInvio.EMAIL,
                created_by=1,
            )

        assert result.subject == "Test"
        assert result.status == StatoComunicazione.DRAFT
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_draft_whatsapp_channel(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        with patch(
            "app.services.communication_service.Communication",
            side_effect=_make_comm_factory(),
        ):
            svc = _make_service()
            result = await svc.create_draft(
                mock_db,
                studio_id=studio_id,
                subject="WhatsApp Test",
                content="Messaggio",
                channel=CanaleInvio.WHATSAPP,
                created_by=2,
            )

        assert result.channel == CanaleInvio.WHATSAPP
        assert result.created_by == 2

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_draft_with_normativa_reference(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        with patch(
            "app.services.communication_service.Communication",
            side_effect=_make_comm_factory(),
        ):
            svc = _make_service()
            result = await svc.create_draft(
                mock_db,
                studio_id=studio_id,
                subject="Normativa",
                content="Riferimento normativo",
                channel=CanaleInvio.EMAIL,
                created_by=1,
                normativa_riferimento="Art. 119 DL 34/2020",
            )

        assert result.normativa_riferimento == "Art. 119 DL 34/2020"


# ---------------------------------------------------------------------------
# State transition tests
# ---------------------------------------------------------------------------


class TestCommunicationWorkflow:
    """Tests for state machine transitions."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_submit_for_review(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        svc = _make_service()
        comm_id = uuid4()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.DRAFT

        with patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)):
            result = await svc.submit_for_review(mock_db, communication_id=comm_id, studio_id=studio_id)

        assert result.status == StatoComunicazione.PENDING_REVIEW
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_approve_success(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        svc = _make_service()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.PENDING_REVIEW
        mock_comm.created_by = 1

        with patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)):
            result = await svc.approve(
                mock_db,
                communication_id=uuid4(),
                studio_id=studio_id,
                approved_by=2,
            )

        assert result.status == StatoComunicazione.APPROVED
        assert result.approved_by == 2
        assert result.approved_at is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_approve_self_approval_forbidden(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        svc = _make_service()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.PENDING_REVIEW
        mock_comm.created_by = 1

        with (
            patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)),
            pytest.raises(ValueError, match="auto-approvazione"),
        ):
            await svc.approve(
                mock_db,
                communication_id=uuid4(),
                studio_id=studio_id,
                approved_by=1,
            )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_reject(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        svc = _make_service()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.PENDING_REVIEW

        with patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)):
            result = await svc.reject(mock_db, communication_id=uuid4(), studio_id=studio_id)

        assert result.status == StatoComunicazione.REJECTED

    @pytest.mark.asyncio(loop_scope="function")
    async def test_mark_sent(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        svc = _make_service()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.APPROVED

        with patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)):
            result = await svc.mark_sent(mock_db, communication_id=uuid4(), studio_id=studio_id)

        assert result.status == StatoComunicazione.SENT
        assert result.sent_at is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_mark_failed(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        svc = _make_service()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.APPROVED

        with patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)):
            result = await svc.mark_failed(mock_db, communication_id=uuid4(), studio_id=studio_id)

        assert result.status == StatoComunicazione.FAILED

    @pytest.mark.asyncio(loop_scope="function")
    async def test_invalid_transition_raises(self, mock_audit) -> None:
        from app.services.communication_service import CommunicationService

        with pytest.raises(ValueError, match="non è valida"):
            CommunicationService._validate_transition(StatoComunicazione.DRAFT, StatoComunicazione.SENT)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_communication_not_found_returns_none(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        svc = _make_service()

        with patch.object(svc, "_get_communication", AsyncMock(return_value=None)):
            result = await svc.submit_for_review(mock_db, communication_id=uuid4(), studio_id=studio_id)

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_full_lifecycle_draft_to_sent(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        """Full lifecycle: create -> submit -> approve -> send."""
        svc = _make_service()
        comm_id = uuid4()

        # Create draft
        with patch(
            "app.services.communication_service.Communication",
            side_effect=_make_comm_factory(),
        ):
            draft = await svc.create_draft(
                mock_db,
                studio_id=studio_id,
                subject="Lifecycle",
                content="Test",
                channel=CanaleInvio.EMAIL,
                created_by=1,
            )

        # Submit -> Approve -> Send using patched _get_communication
        draft.status = StatoComunicazione.DRAFT

        with patch.object(svc, "_get_communication", AsyncMock(return_value=draft)):
            await svc.submit_for_review(mock_db, communication_id=comm_id, studio_id=studio_id)
        assert draft.status == StatoComunicazione.PENDING_REVIEW

        with patch.object(svc, "_get_communication", AsyncMock(return_value=draft)):
            await svc.approve(
                mock_db,
                communication_id=comm_id,
                studio_id=studio_id,
                approved_by=99,
            )
        assert draft.status == StatoComunicazione.APPROVED

        with patch.object(svc, "_get_communication", AsyncMock(return_value=draft)):
            await svc.mark_sent(mock_db, communication_id=comm_id, studio_id=studio_id)
        assert draft.status == StatoComunicazione.SENT


# ---------------------------------------------------------------------------
# Bulk draft tests
# ---------------------------------------------------------------------------


class TestBulkDrafts:
    """Tests for CommunicationService.create_bulk_drafts."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_bulk_drafts_success(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        client1 = MagicMock(id=1)
        client2 = MagicMock(id=2)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [client1, client2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch(
                "app.services.communication_service.Communication",
                side_effect=_make_comm_factory(),
            ),
            patch("app.services.communication_service.select"),
            patch("app.services.communication_service.and_"),
        ):
            svc = _make_service()
            result = await svc.create_bulk_drafts(
                mock_db,
                studio_id=studio_id,
                client_ids=[1, 2],
                subject="Bulk",
                content="Test",
                channel=CanaleInvio.EMAIL,
                created_by=1,
            )

        assert len(result) == 2
        assert mock_db.add.call_count == 2

    @pytest.mark.asyncio(loop_scope="function")
    async def test_bulk_drafts_empty_list_raises(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        svc = _make_service()

        with pytest.raises(ValueError, match="vuota"):
            await svc.create_bulk_drafts(
                mock_db,
                studio_id=studio_id,
                client_ids=[],
                subject="Test",
                content="Body",
                channel=CanaleInvio.EMAIL,
                created_by=1,
            )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_bulk_drafts_skips_invalid_clients(self, mock_db: AsyncMock, studio_id, mock_audit) -> None:
        valid_client = MagicMock(id=1)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [valid_client]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch(
                "app.services.communication_service.Communication",
                side_effect=_make_comm_factory(),
            ),
            patch("app.services.communication_service.select"),
            patch("app.services.communication_service.and_"),
        ):
            svc = _make_service()
            result = await svc.create_bulk_drafts(
                mock_db,
                studio_id=studio_id,
                client_ids=[1, 999],
                subject="Bulk",
                content="Test",
                channel=CanaleInvio.EMAIL,
                created_by=1,
            )

        assert len(result) == 1
