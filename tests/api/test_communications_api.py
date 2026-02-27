"""Tests for Communication API endpoints (DEV-332).

TDD: Tests written FIRST before implementation validation.
Tests the full communication workflow: create, submit, approve, reject, send.

Endpoints tested:
- POST /communications              (create draft)
- GET  /communications               (list)
- GET  /communications/{id}          (get by id)
- POST /communications/{id}/submit   (DRAFT -> PENDING_REVIEW)
- POST /communications/{id}/approve  (PENDING_REVIEW -> APPROVED)
- POST /communications/{id}/reject   (PENDING_REVIEW -> REJECTED)
- POST /communications/{id}/send     (APPROVED -> SENT)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.models.communication import CanaleInvio, StatoComunicazione

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def studio_id() -> UUID:
    """Fixed studio UUID for tenant isolation."""
    return uuid4()


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock async database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def comm_id() -> UUID:
    """Fixed communication UUID."""
    return uuid4()


@pytest.fixture
def sample_draft(studio_id: UUID, comm_id: UUID) -> MagicMock:
    """Return a mock Communication in DRAFT status."""
    comm = MagicMock()
    comm.id = comm_id
    comm.studio_id = studio_id
    comm.client_id = 1
    comm.subject = "Scadenza IVA trimestrale"
    comm.content = "Gentile cliente, le ricordiamo la scadenza IVA del 16 marzo."
    comm.channel = CanaleInvio.EMAIL
    comm.status = StatoComunicazione.DRAFT
    comm.created_by = 1
    comm.approved_by = None
    comm.approved_at = None
    comm.sent_at = None
    comm.normativa_riferimento = "Art. 1, D.P.R. 633/1972"
    comm.matching_rule_id = None
    comm.created_at = datetime.now(UTC)
    comm.updated_at = None
    return comm


@pytest.fixture
def sample_pending(studio_id: UUID, comm_id: UUID) -> MagicMock:
    """Return a mock Communication in PENDING_REVIEW status."""
    comm = MagicMock()
    comm.id = comm_id
    comm.studio_id = studio_id
    comm.client_id = 1
    comm.subject = "Scadenza IVA trimestrale"
    comm.content = "Gentile cliente, le ricordiamo la scadenza IVA del 16 marzo."
    comm.channel = CanaleInvio.EMAIL
    comm.status = StatoComunicazione.PENDING_REVIEW
    comm.created_by = 1
    comm.approved_by = None
    comm.approved_at = None
    comm.sent_at = None
    comm.normativa_riferimento = None
    comm.matching_rule_id = None
    comm.created_at = datetime.now(UTC)
    comm.updated_at = None
    return comm


@pytest.fixture
def sample_approved(studio_id: UUID, comm_id: UUID) -> MagicMock:
    """Return a mock Communication in APPROVED status."""
    comm = MagicMock()
    comm.id = comm_id
    comm.studio_id = studio_id
    comm.client_id = 1
    comm.subject = "Scadenza IVA trimestrale"
    comm.content = "Gentile cliente, le ricordiamo la scadenza IVA del 16 marzo."
    comm.channel = CanaleInvio.EMAIL
    comm.status = StatoComunicazione.APPROVED
    comm.created_by = 1
    comm.approved_by = 2
    comm.approved_at = datetime.now(UTC)
    comm.sent_at = None
    comm.normativa_riferimento = None
    comm.matching_rule_id = None
    comm.created_at = datetime.now(UTC)
    comm.updated_at = None
    return comm


@pytest.fixture
def sample_sent(studio_id: UUID, comm_id: UUID) -> MagicMock:
    """Return a mock Communication in SENT status."""
    comm = MagicMock()
    comm.id = comm_id
    comm.studio_id = studio_id
    comm.client_id = 1
    comm.subject = "Scadenza IVA trimestrale"
    comm.content = "Gentile cliente, le ricordiamo la scadenza IVA del 16 marzo."
    comm.channel = CanaleInvio.EMAIL
    comm.status = StatoComunicazione.SENT
    comm.created_by = 1
    comm.approved_by = 2
    comm.approved_at = datetime.now(UTC)
    comm.sent_at = datetime.now(UTC)
    comm.normativa_riferimento = None
    comm.matching_rule_id = None
    comm.created_at = datetime.now(UTC)
    comm.updated_at = None
    return comm


# ---------------------------------------------------------------------------
# POST /communications — Create draft
# ---------------------------------------------------------------------------


class TestCreateCommunication:
    """Tests for POST /communications endpoint."""

    @pytest.mark.asyncio
    async def test_create_draft_success(self, mock_db: AsyncMock, studio_id: UUID, sample_draft: MagicMock) -> None:
        """Happy path: creates a communication draft."""
        from app.api.v1.communications import create_communication
        from app.schemas.communication import CommunicationCreate

        body = CommunicationCreate(
            subject="Scadenza IVA trimestrale",
            content="Gentile cliente, le ricordiamo la scadenza IVA del 16 marzo.",
            channel=CanaleInvio.EMAIL,
            client_id=1,
            normativa_riferimento="Art. 1, D.P.R. 633/1972",
        )

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.create_draft = AsyncMock(return_value=sample_draft)
            result = await create_communication(body=body, studio_id=studio_id, created_by=1, db=mock_db)

        assert result.subject == "Scadenza IVA trimestrale"
        assert result.status == StatoComunicazione.DRAFT
        assert result.created_by == 1
        mock_svc.create_draft.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_draft_without_client_id(
        self, mock_db: AsyncMock, studio_id: UUID, sample_draft: MagicMock
    ) -> None:
        """Edge case: communication without client_id (bulk communication)."""
        from app.api.v1.communications import create_communication
        from app.schemas.communication import CommunicationCreate

        sample_draft.client_id = None
        body = CommunicationCreate(
            subject="Comunicazione generale",
            content="Informativa per tutti i clienti dello studio.",
            channel=CanaleInvio.EMAIL,
        )

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.create_draft = AsyncMock(return_value=sample_draft)
            result = await create_communication(body=body, studio_id=studio_id, created_by=1, db=mock_db)

        assert result.client_id is None

    @pytest.mark.asyncio
    async def test_create_draft_whatsapp_channel(
        self, mock_db: AsyncMock, studio_id: UUID, sample_draft: MagicMock
    ) -> None:
        """Edge case: communication via WhatsApp channel."""
        from app.api.v1.communications import create_communication
        from app.schemas.communication import CommunicationCreate

        sample_draft.channel = CanaleInvio.WHATSAPP
        body = CommunicationCreate(
            subject="Promemoria",
            content="Promemoria scadenza.",
            channel=CanaleInvio.WHATSAPP,
        )

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.create_draft = AsyncMock(return_value=sample_draft)
            result = await create_communication(body=body, studio_id=studio_id, created_by=1, db=mock_db)

        assert result.channel == CanaleInvio.WHATSAPP


# ---------------------------------------------------------------------------
# GET /communications — List
# ---------------------------------------------------------------------------


class TestListCommunications:
    """Tests for GET /communications endpoint."""

    @pytest.mark.asyncio
    async def test_list_communications_success(
        self, mock_db: AsyncMock, studio_id: UUID, sample_draft: MagicMock
    ) -> None:
        """Happy path: returns list of communications."""
        from app.api.v1.communications import list_communications

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.list_by_studio = AsyncMock(return_value=[sample_draft])
            result = await list_communications(studio_id=studio_id, status=None, offset=0, limit=50, db=mock_db)

        assert len(result) == 1
        assert result[0].subject == "Scadenza IVA trimestrale"

    @pytest.mark.asyncio
    async def test_list_communications_with_status_filter(
        self, mock_db: AsyncMock, studio_id: UUID, sample_pending: MagicMock
    ) -> None:
        """Happy path: filter by status."""
        from app.api.v1.communications import list_communications

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.list_by_studio = AsyncMock(return_value=[sample_pending])
            result = await list_communications(
                studio_id=studio_id,
                status=StatoComunicazione.PENDING_REVIEW,
                offset=0,
                limit=50,
                db=mock_db,
            )

        assert len(result) == 1
        mock_svc.list_by_studio.assert_awaited_once_with(
            mock_db,
            studio_id=studio_id,
            status=StatoComunicazione.PENDING_REVIEW,
            offset=0,
            limit=50,
        )

    @pytest.mark.asyncio
    async def test_list_communications_empty(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Edge case: no communications returns empty list."""
        from app.api.v1.communications import list_communications

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.list_by_studio = AsyncMock(return_value=[])
            result = await list_communications(studio_id=studio_id, status=None, offset=0, limit=50, db=mock_db)

        assert result == []


# ---------------------------------------------------------------------------
# GET /communications/{id} — Get by ID
# ---------------------------------------------------------------------------


class TestGetCommunication:
    """Tests for GET /communications/{communication_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_communication_success(
        self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID, sample_draft: MagicMock
    ) -> None:
        """Happy path: returns communication when found."""
        from app.api.v1.communications import get_communication

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=sample_draft)
            result = await get_communication(communication_id=comm_id, studio_id=studio_id, db=mock_db)

        assert result.id == comm_id
        assert result.subject == "Scadenza IVA trimestrale"

    @pytest.mark.asyncio
    async def test_get_communication_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: nonexistent communication raises 404."""
        from app.api.v1.communications import get_communication

        fake_id = uuid4()

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await get_communication(communication_id=fake_id, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "non trovata" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# POST /communications/{id}/submit — Submit for review
# ---------------------------------------------------------------------------


class TestSubmitForReview:
    """Tests for POST /communications/{id}/submit endpoint."""

    @pytest.mark.asyncio
    async def test_submit_for_review_success(
        self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID, sample_pending: MagicMock
    ) -> None:
        """Happy path: DRAFT -> PENDING_REVIEW."""
        from app.api.v1.communications import submit_for_review

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.submit_for_review = AsyncMock(return_value=sample_pending)
            result = await submit_for_review(communication_id=comm_id, studio_id=studio_id, db=mock_db)

        assert result.status == StatoComunicazione.PENDING_REVIEW
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_for_review_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: nonexistent communication raises 404."""
        from app.api.v1.communications import submit_for_review

        fake_id = uuid4()

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.submit_for_review = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await submit_for_review(communication_id=fake_id, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_for_review_invalid_transition_returns_400(
        self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID
    ) -> None:
        """Error case: submitting an already-sent communication raises 400."""
        from app.api.v1.communications import submit_for_review

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.submit_for_review = AsyncMock(
                side_effect=ValueError("La transizione da 'sent' a 'pending_review' non e' valida.")
            )
            with pytest.raises(HTTPException) as exc_info:
                await submit_for_review(communication_id=comm_id, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "transizione" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# POST /communications/{id}/approve — Approve
# ---------------------------------------------------------------------------


class TestApproveCommunication:
    """Tests for POST /communications/{id}/approve endpoint."""

    @pytest.mark.asyncio
    async def test_approve_success(
        self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID, sample_approved: MagicMock
    ) -> None:
        """Happy path: PENDING_REVIEW -> APPROVED by a different user."""
        from app.api.v1.communications import approve_communication

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.approve = AsyncMock(return_value=sample_approved)
            result = await approve_communication(
                communication_id=comm_id,
                studio_id=studio_id,
                approved_by=2,
                db=mock_db,
            )

        assert result.status == StatoComunicazione.APPROVED
        assert result.approved_by == 2
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_approve_self_approval_returns_400(self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID) -> None:
        """Error case: self-approval (creator == approver) raises 400."""
        from app.api.v1.communications import approve_communication

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.approve = AsyncMock(
                side_effect=ValueError(
                    "L'auto-approvazione non e' consentita: il creatore non puo' approvare la propria comunicazione."
                )
            )
            with pytest.raises(HTTPException) as exc_info:
                await approve_communication(
                    communication_id=comm_id,
                    studio_id=studio_id,
                    approved_by=1,  # same as created_by
                    db=mock_db,
                )

        assert exc_info.value.status_code == 400
        assert "auto-approvazione" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_approve_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: nonexistent communication raises 404."""
        from app.api.v1.communications import approve_communication

        fake_id = uuid4()

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.approve = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await approve_communication(
                    communication_id=fake_id,
                    studio_id=studio_id,
                    approved_by=2,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_invalid_transition_returns_400(
        self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID
    ) -> None:
        """Error case: approving a DRAFT (should be PENDING_REVIEW first) raises 400."""
        from app.api.v1.communications import approve_communication

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.approve = AsyncMock(
                side_effect=ValueError("La transizione da 'draft' a 'approved' non e' valida.")
            )
            with pytest.raises(HTTPException) as exc_info:
                await approve_communication(
                    communication_id=comm_id,
                    studio_id=studio_id,
                    approved_by=2,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# POST /communications/{id}/reject — Reject
# ---------------------------------------------------------------------------


class TestRejectCommunication:
    """Tests for POST /communications/{id}/reject endpoint."""

    @pytest.mark.asyncio
    async def test_reject_success(self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID) -> None:
        """Happy path: PENDING_REVIEW -> REJECTED."""
        from app.api.v1.communications import reject_communication

        rejected = MagicMock()
        rejected.id = comm_id
        rejected.studio_id = studio_id
        rejected.client_id = 1
        rejected.subject = "Scadenza IVA"
        rejected.content = "Contenuto comunicazione."
        rejected.channel = CanaleInvio.EMAIL
        rejected.status = StatoComunicazione.REJECTED
        rejected.created_by = 1
        rejected.approved_by = None
        rejected.approved_at = None
        rejected.sent_at = None
        rejected.normativa_riferimento = None
        rejected.created_at = datetime.now(UTC)

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.reject = AsyncMock(return_value=rejected)
            result = await reject_communication(communication_id=comm_id, studio_id=studio_id, db=mock_db)

        assert result.status == StatoComunicazione.REJECTED
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reject_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: nonexistent communication raises 404."""
        from app.api.v1.communications import reject_communication

        fake_id = uuid4()

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.reject = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await reject_communication(communication_id=fake_id, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_invalid_transition_returns_400(
        self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID
    ) -> None:
        """Error case: rejecting a DRAFT (should be PENDING_REVIEW) raises 400."""
        from app.api.v1.communications import reject_communication

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.reject = AsyncMock(
                side_effect=ValueError("La transizione da 'draft' a 'rejected' non e' valida.")
            )
            with pytest.raises(HTTPException) as exc_info:
                await reject_communication(communication_id=comm_id, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# POST /communications/{id}/send — Mark as sent
# ---------------------------------------------------------------------------


class TestMarkSent:
    """Tests for POST /communications/{id}/send endpoint."""

    @pytest.mark.asyncio
    async def test_mark_sent_success(
        self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID, sample_sent: MagicMock
    ) -> None:
        """Happy path: APPROVED -> SENT."""
        from app.api.v1.communications import mark_sent

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.mark_sent = AsyncMock(return_value=sample_sent)
            result = await mark_sent(communication_id=comm_id, studio_id=studio_id, db=mock_db)

        assert result.status == StatoComunicazione.SENT
        assert result.sent_at is not None
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_sent_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: nonexistent communication raises 404."""
        from app.api.v1.communications import mark_sent

        fake_id = uuid4()

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.mark_sent = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await mark_sent(communication_id=fake_id, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_sent_invalid_transition_returns_400(
        self, mock_db: AsyncMock, studio_id: UUID, comm_id: UUID
    ) -> None:
        """Error case: sending a DRAFT (must be APPROVED first) raises 400."""
        from app.api.v1.communications import mark_sent

        with patch("app.api.v1.communications.communication_service") as mock_svc:
            mock_svc.mark_sent = AsyncMock(side_effect=ValueError("La transizione da 'draft' a 'sent' non e' valida."))
            with pytest.raises(HTTPException) as exc_info:
                await mark_sent(communication_id=comm_id, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "transizione" in exc_info.value.detail.lower()
