"""DEV-333: Tests for CommunicationEmailService — Email sending integration.

TDD RED phase: These tests define the expected behaviour of the email sending
service for approved communications.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.communication import CanaleInvio, Communication, StatoComunicazione

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def approved_comm(studio_id) -> Communication:
    """An APPROVED communication ready to be sent via email."""
    return Communication(
        id=uuid4(),
        studio_id=studio_id,
        client_id=1,
        subject="Scadenza IVA trimestrale",
        content="Gentile cliente, le ricordiamo la scadenza IVA del 16 marzo.",
        channel=CanaleInvio.EMAIL,
        status=StatoComunicazione.APPROVED,
        created_by=1,
        approved_by=2,
        approved_at=datetime.now(UTC),
    )


@pytest.fixture
def email_service():
    from app.services.communication_email_service import CommunicationEmailService

    return CommunicationEmailService()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCommunicationEmailSending:
    """Test CommunicationEmailService email delivery."""

    @pytest.mark.asyncio
    async def test_send_communication_success(
        self,
        email_service,
        mock_db: AsyncMock,
        approved_comm: Communication,
    ) -> None:
        """Happy path: send an approved communication via email successfully."""
        sent_comm = MagicMock(spec=Communication)
        sent_comm.status = StatoComunicazione.SENT
        sent_comm.sent_at = datetime.now(UTC)

        with (
            patch("app.services.communication_email_service.communication_service") as mock_comm_svc,
            patch.object(email_service, "_send_smtp") as mock_smtp,
        ):
            mock_comm_svc.get_by_id = AsyncMock(return_value=approved_comm)
            mock_comm_svc.mark_sent = AsyncMock(return_value=sent_comm)

            result = await email_service.send_communication(
                db=mock_db,
                communication_id=approved_comm.id,
                studio_id=approved_comm.studio_id,
                recipient_email="cliente@example.com",
            )

        assert result is not None
        assert result.status == StatoComunicazione.SENT
        mock_smtp.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_communication_retry_on_failure(
        self,
        email_service,
        mock_db: AsyncMock,
        approved_comm: Communication,
    ) -> None:
        """Retry logic: SMTP fails on first attempt, succeeds on second."""
        sent_comm = MagicMock(spec=Communication)
        sent_comm.status = StatoComunicazione.SENT

        with (
            patch("app.services.communication_email_service.communication_service") as mock_comm_svc,
            patch.object(
                email_service,
                "_send_smtp",
                side_effect=[OSError("SMTP timeout"), None],
            ) as mock_smtp,
        ):
            mock_comm_svc.get_by_id = AsyncMock(return_value=approved_comm)
            mock_comm_svc.mark_sent = AsyncMock(return_value=sent_comm)

            result = await email_service.send_communication(
                db=mock_db,
                communication_id=approved_comm.id,
                studio_id=approved_comm.studio_id,
                recipient_email="cliente@example.com",
            )

        assert result is not None
        assert result.status == StatoComunicazione.SENT
        assert mock_smtp.call_count == 2

    @pytest.mark.asyncio
    async def test_send_communication_marks_failed(
        self,
        email_service,
        mock_db: AsyncMock,
        approved_comm: Communication,
    ) -> None:
        """After exhausting all retries the communication status must be FAILED."""
        failed_comm = MagicMock(spec=Communication)
        failed_comm.status = StatoComunicazione.FAILED

        with (
            patch("app.services.communication_email_service.communication_service") as mock_comm_svc,
            patch.object(
                email_service,
                "_send_smtp",
                side_effect=OSError("SMTP permanente non raggiungibile"),
            ),
        ):
            mock_comm_svc.get_by_id = AsyncMock(return_value=approved_comm)
            mock_comm_svc.mark_failed = AsyncMock(return_value=failed_comm)

            result = await email_service.send_communication(
                db=mock_db,
                communication_id=approved_comm.id,
                studio_id=approved_comm.studio_id,
                recipient_email="cliente@example.com",
            )

        assert result is not None
        assert result.status == StatoComunicazione.FAILED

    @pytest.mark.asyncio
    async def test_send_communication_invalid_recipient(
        self,
        email_service,
        mock_db: AsyncMock,
        approved_comm: Communication,
    ) -> None:
        """Invalid email address must raise ValueError."""
        with (
            patch("app.services.communication_email_service.communication_service") as mock_comm_svc,
        ):
            mock_comm_svc.get_by_id = AsyncMock(return_value=approved_comm)

            with pytest.raises(ValueError, match="[Ii]ndirizzo email.*non valido"):
                await email_service.send_communication(
                    db=mock_db,
                    communication_id=approved_comm.id,
                    studio_id=approved_comm.studio_id,
                    recipient_email="non-una-email",
                )

    @pytest.mark.asyncio
    async def test_send_communication_not_found(
        self,
        email_service,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Communication not found returns None."""
        with patch("app.services.communication_email_service.communication_service") as mock_comm_svc:
            mock_comm_svc.get_by_id = AsyncMock(return_value=None)

            result = await email_service.send_communication(
                db=mock_db,
                communication_id=uuid4(),
                studio_id=studio_id,
                recipient_email="test@example.com",
            )

        assert result is None
