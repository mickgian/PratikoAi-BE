"""DEV-338: Tests for CommunicationService audit logging integration.

Verifies that all state transitions in CommunicationService trigger
SecurityAuditLogger.log_security_event with the correct event details.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.communication import CanaleInvio, Communication, StatoComunicazione
from app.services.communication_service import CommunicationService


@pytest.fixture
def mock_audit_logger() -> AsyncMock:
    """Create a mock SecurityAuditLogger."""
    audit = AsyncMock()
    audit.log_security_event = AsyncMock(return_value=True)
    return audit


@pytest.fixture
def comm_service(mock_audit_logger: AsyncMock) -> CommunicationService:
    """CommunicationService with injected mock audit logger."""
    svc = CommunicationService()
    svc._audit_logger = mock_audit_logger
    return svc


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
def sample_comm(studio_id) -> Communication:
    return Communication(
        id=uuid4(),
        studio_id=studio_id,
        client_id=1,
        subject="Scadenza IVA",
        content="Gentile cliente, la scadenza IVA e il 16 marzo.",
        channel=CanaleInvio.EMAIL,
        status=StatoComunicazione.DRAFT,
        created_by=1,
    )


class TestCommunicationAuditCreateDraft:
    """Test that create_draft triggers audit log."""

    @pytest.mark.asyncio
    async def test_create_draft_triggers_audit_log(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        mock_audit_logger: AsyncMock,
        studio_id,
    ) -> None:
        """Happy path: creating a draft logs a COMMUNICATION_CREATED audit event."""
        result = await comm_service.create_draft(
            db=mock_db,
            studio_id=studio_id,
            subject="Scadenza IVA",
            content="La scadenza IVA e il 16 marzo.",
            channel=CanaleInvio.EMAIL,
            created_by=1,
            client_id=1,
        )

        mock_audit_logger.log_security_event.assert_called_once()
        call_kwargs = mock_audit_logger.log_security_event.call_args
        assert call_kwargs.kwargs["action"] == "communication_created"
        assert str(studio_id) in str(call_kwargs.kwargs["details"])

    @pytest.mark.asyncio
    async def test_create_draft_audit_contains_communication_id(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        mock_audit_logger: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: audit details include the new communication ID."""
        result = await comm_service.create_draft(
            db=mock_db,
            studio_id=studio_id,
            subject="Avviso",
            content="Contenuto.",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )

        call_kwargs = mock_audit_logger.log_security_event.call_args.kwargs
        assert "communication_id" in call_kwargs["details"]
        assert call_kwargs["details"]["communication_id"] == str(result.id)


class TestCommunicationAuditApprove:
    """Test that approve triggers audit log with correct details."""

    @pytest.mark.asyncio
    async def test_approve_triggers_audit_log(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        mock_audit_logger: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Happy path: approval logs a COMMUNICATION_APPROVED audit event."""
        sample_comm.status = StatoComunicazione.PENDING_REVIEW
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        await comm_service.approve(
            db=mock_db,
            communication_id=sample_comm.id,
            studio_id=sample_comm.studio_id,
            approved_by=2,
        )

        mock_audit_logger.log_security_event.assert_called_once()
        call_kwargs = mock_audit_logger.log_security_event.call_args.kwargs
        assert call_kwargs["action"] == "communication_approved"
        assert call_kwargs["details"]["approved_by"] == 2
        assert call_kwargs["details"]["communication_id"] == str(sample_comm.id)

    @pytest.mark.asyncio
    async def test_approve_audit_not_triggered_on_not_found(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        mock_audit_logger: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: no audit log when communication not found."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await comm_service.approve(
            db=mock_db,
            communication_id=uuid4(),
            studio_id=studio_id,
            approved_by=2,
        )

        assert result is None
        mock_audit_logger.log_security_event.assert_not_called()


class TestCommunicationAuditMarkSent:
    """Test that mark_sent triggers audit log."""

    @pytest.mark.asyncio
    async def test_mark_sent_triggers_audit_log(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        mock_audit_logger: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Happy path: marking as sent logs a COMMUNICATION_SENT audit event."""
        sample_comm.status = StatoComunicazione.APPROVED
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        await comm_service.mark_sent(
            db=mock_db,
            communication_id=sample_comm.id,
            studio_id=sample_comm.studio_id,
        )

        mock_audit_logger.log_security_event.assert_called_once()
        call_kwargs = mock_audit_logger.log_security_event.call_args.kwargs
        assert call_kwargs["action"] == "communication_sent"
        assert call_kwargs["details"]["communication_id"] == str(sample_comm.id)


class TestCommunicationAuditReject:
    """Test that reject triggers audit log."""

    @pytest.mark.asyncio
    async def test_reject_triggers_audit_log(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        mock_audit_logger: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Happy path: rejection logs a COMMUNICATION_REJECTED audit event."""
        sample_comm.status = StatoComunicazione.PENDING_REVIEW
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        await comm_service.reject(
            db=mock_db,
            communication_id=sample_comm.id,
            studio_id=sample_comm.studio_id,
        )

        mock_audit_logger.log_security_event.assert_called_once()
        call_kwargs = mock_audit_logger.log_security_event.call_args.kwargs
        assert call_kwargs["action"] == "communication_rejected"
        assert call_kwargs["details"]["communication_id"] == str(sample_comm.id)


class TestCommunicationAuditMarkFailed:
    """Test that mark_failed triggers audit log."""

    @pytest.mark.asyncio
    async def test_mark_failed_triggers_audit_log(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        mock_audit_logger: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Happy path: marking as failed logs a COMMUNICATION_FAILED audit event."""
        sample_comm.status = StatoComunicazione.APPROVED
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        await comm_service.mark_failed(
            db=mock_db,
            communication_id=sample_comm.id,
            studio_id=sample_comm.studio_id,
        )

        mock_audit_logger.log_security_event.assert_called_once()
        call_kwargs = mock_audit_logger.log_security_event.call_args.kwargs
        assert call_kwargs["action"] == "communication_failed"
        assert call_kwargs["details"]["communication_id"] == str(sample_comm.id)

    @pytest.mark.asyncio
    async def test_mark_failed_audit_not_triggered_on_not_found(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        mock_audit_logger: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: no audit log when communication not found."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await comm_service.mark_failed(
            db=mock_db,
            communication_id=uuid4(),
            studio_id=studio_id,
        )

        assert result is None
        mock_audit_logger.log_security_event.assert_not_called()
