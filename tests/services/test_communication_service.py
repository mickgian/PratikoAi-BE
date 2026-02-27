"""DEV-330: Tests for CommunicationService with Draft/Approve Workflow."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.communication import CanaleInvio, Communication, StatoComunicazione
from app.services.communication_service import CommunicationService


@pytest.fixture
def comm_service() -> CommunicationService:
    return CommunicationService()


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
        content="Gentile cliente, la scadenza IVA è il 16 marzo.",
        channel=CanaleInvio.EMAIL,
        status=StatoComunicazione.DRAFT,
        created_by=1,
    )


class TestCommunicationServiceCreate:
    """Test CommunicationService.create_draft()."""

    @pytest.mark.asyncio
    async def test_create_draft_success(
        self, comm_service: CommunicationService, mock_db: AsyncMock, studio_id
    ) -> None:
        """Happy path: create a communication draft."""
        result = await comm_service.create_draft(
            db=mock_db,
            studio_id=studio_id,
            subject="Scadenza IVA",
            content="La scadenza IVA è il 16 marzo.",
            channel=CanaleInvio.EMAIL,
            created_by=1,
            client_id=1,
        )

        assert result.status == StatoComunicazione.DRAFT
        assert result.subject == "Scadenza IVA"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_draft_no_client(
        self, comm_service: CommunicationService, mock_db: AsyncMock, studio_id
    ) -> None:
        """Edge case: create draft without a client (bulk)."""
        result = await comm_service.create_draft(
            db=mock_db,
            studio_id=studio_id,
            subject="Avviso generale",
            content="Comunicazione per tutti i clienti.",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )

        assert result.client_id is None
        assert result.status == StatoComunicazione.DRAFT


class TestCommunicationServiceWorkflow:
    """Test CommunicationService state transitions."""

    @pytest.mark.asyncio
    async def test_submit_for_review(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Happy path: DRAFT → PENDING_REVIEW."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        result = await comm_service.submit_for_review(
            db=mock_db, communication_id=sample_comm.id, studio_id=sample_comm.studio_id
        )

        assert result is not None
        assert result.status == StatoComunicazione.PENDING_REVIEW

    @pytest.mark.asyncio
    async def test_approve_success(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Happy path: PENDING_REVIEW → APPROVED."""
        sample_comm.status = StatoComunicazione.PENDING_REVIEW
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        result = await comm_service.approve(
            db=mock_db,
            communication_id=sample_comm.id,
            studio_id=sample_comm.studio_id,
            approved_by=2,
        )

        assert result is not None
        assert result.status == StatoComunicazione.APPROVED
        assert result.approved_by == 2
        assert result.approved_at is not None

    @pytest.mark.asyncio
    async def test_approve_self_approval_raises(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Error: creator cannot approve their own communication."""
        sample_comm.status = StatoComunicazione.PENDING_REVIEW
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        with pytest.raises(ValueError, match="auto-approvazione"):
            await comm_service.approve(
                db=mock_db,
                communication_id=sample_comm.id,
                studio_id=sample_comm.studio_id,
                approved_by=sample_comm.created_by,
            )

    @pytest.mark.asyncio
    async def test_approve_wrong_status_raises(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Error: cannot approve a DRAFT (must be PENDING_REVIEW)."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        with pytest.raises(ValueError, match="transizione.*non.*valida"):
            await comm_service.approve(
                db=mock_db,
                communication_id=sample_comm.id,
                studio_id=sample_comm.studio_id,
                approved_by=2,
            )

    @pytest.mark.asyncio
    async def test_reject_success(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Happy path: PENDING_REVIEW → REJECTED."""
        sample_comm.status = StatoComunicazione.PENDING_REVIEW
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        result = await comm_service.reject(
            db=mock_db,
            communication_id=sample_comm.id,
            studio_id=sample_comm.studio_id,
        )

        assert result is not None
        assert result.status == StatoComunicazione.REJECTED

    @pytest.mark.asyncio
    async def test_mark_sent_success(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Happy path: APPROVED → SENT."""
        sample_comm.status = StatoComunicazione.APPROVED
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        result = await comm_service.mark_sent(
            db=mock_db,
            communication_id=sample_comm.id,
            studio_id=sample_comm.studio_id,
        )

        assert result is not None
        assert result.status == StatoComunicazione.SENT
        assert result.sent_at is not None

    @pytest.mark.asyncio
    async def test_mark_failed(
        self,
        comm_service: CommunicationService,
        mock_db: AsyncMock,
        sample_comm: Communication,
    ) -> None:
        """Edge case: APPROVED → FAILED."""
        sample_comm.status = StatoComunicazione.APPROVED
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_comm)))

        result = await comm_service.mark_failed(
            db=mock_db,
            communication_id=sample_comm.id,
            studio_id=sample_comm.studio_id,
        )

        assert result is not None
        assert result.status == StatoComunicazione.FAILED
