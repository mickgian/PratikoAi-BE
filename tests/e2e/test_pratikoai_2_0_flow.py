"""DEV-371: Full User Journey E2E Test — PratikoAI 2.0

Comprehensive end-to-end test covering the entire PratikoAI 2.0 user journey:
1. Register → 2. Create Studio → 3. Import Clients → 4. Chat →
5. View Matches → 6. Create Communication → 7. Approve → 8. Send →
9. View Dashboard

Tests the service layer end-to-end with mocked DB to validate the full
workflow integrates correctly across all PratikoAI 2.0 components.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Pre-populate sys.modules BEFORE any app.services imports.
# app.services.__init__ imports database_service which tries to connect at load.
if "app.services.database" not in sys.modules:
    _mock_db = MagicMock()
    _mock_db.is_connected = True
    _mock_module = MagicMock()
    _mock_module.database_service = _mock_db
    sys.modules["app.services.database"] = _mock_module

from datetime import UTC, datetime  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402

from app.models.communication import CanaleInvio, StatoComunicazione  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def studio_id() -> UUID:
    return uuid4()


@pytest.fixture
def user_id() -> int:
    return 99900


@pytest.fixture
def approver_id() -> int:
    return 99901


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock async DB session for service-layer testing."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    db.get = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_audit():
    """Suppress audit logging during tests."""
    with patch("app.services.communication_service.security_audit_logger") as m:
        m.log_security_event = AsyncMock()
        yield m


# ---------------------------------------------------------------------------
# Step 1: Register
# ---------------------------------------------------------------------------


class TestStep1Register:
    """Step 1 — User registration: create user, hash password, verify fields."""

    def test_user_creation_with_hashed_password(self) -> None:
        """A new user can be created with a properly hashed password."""
        password = "SecureP@ss1"
        hashed = User.hash_password(password)

        user = User(
            id=99900,
            email="e2e_test@pratikoai.it",
            hashed_password=hashed,
            role=UserRole.REGULAR_USER.value,
            provider="email",
        )

        assert user.email == "e2e_test@pratikoai.it"
        assert user.role == UserRole.REGULAR_USER.value
        assert user.provider == "email"
        assert user.verify_password(password) is True

    def test_wrong_password_rejected(self) -> None:
        """Wrong password is rejected by verify_password."""
        hashed = User.hash_password("CorrectP@ss1")
        user = User(id=99900, email="e2e@pratikoai.it", hashed_password=hashed)

        assert user.verify_password("WrongP@ss1") is False

    def test_oauth_user_has_no_password(self) -> None:
        """OAuth users have no hashed_password and fail password verification."""
        user = User(
            id=99900,
            email="oauth@pratikoai.it",
            hashed_password=None,
            provider="google",
        )

        assert user.verify_password("anything") is False

    def test_user_studio_association(self) -> None:
        """User can be associated with a studio_id."""
        sid = str(uuid4())
        user = User(id=99900, email="e2e@pratikoai.it", studio_id=sid)
        assert user.studio_id == sid


# ---------------------------------------------------------------------------
# Step 2: Create Studio
# ---------------------------------------------------------------------------


class TestStep2CreateStudio:
    """Step 2 — Create professional studio via StudioService."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_studio_success(self, mock_db: AsyncMock) -> None:
        """StudioService.create() produces a Studio with correct fields."""
        from app.services.studio_service import StudioService

        svc = StudioService()

        # Mock slug uniqueness check
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        studio = await svc.create(
            mock_db,
            name="Studio Rossi",
            slug="studio-rossi",
            max_clients=100,
            settings={"locale": "it"},
        )

        assert studio.name == "Studio Rossi"
        assert studio.slug == "studio-rossi"
        assert studio.max_clients == 100
        assert studio.settings == {"locale": "it"}
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_duplicate_slug_raises(self, mock_db: AsyncMock) -> None:
        """Duplicate slug raises ValueError."""
        from app.services.studio_service import StudioService

        svc = StudioService()

        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="già in uso"):
            await svc.create(mock_db, name="Dup", slug="taken-slug")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_studio_by_slug(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """StudioService.get_by_slug() returns the studio."""
        from app.models.studio import Studio
        from app.services.studio_service import StudioService

        svc = StudioService()
        studio = Studio(id=studio_id, name="Test", slug="test-slug")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = studio
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_by_slug(mock_db, slug="test-slug")
        assert result is not None
        assert result.slug == "test-slug"


# ---------------------------------------------------------------------------
# Step 3: Import Clients
# ---------------------------------------------------------------------------


class TestStep3ImportClients:
    """Step 3 — Import clients into studio via ClientImportService."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_import_from_records_success(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Importing valid records produces a success report."""
        from app.services.client_import_service import ClientImportService

        svc = ClientImportService()

        # Mock the inner client_service.create
        mock_client = MagicMock(id=1)
        with patch.object(svc._client_service, "create", AsyncMock(return_value=mock_client)):
            report = await svc.import_from_records(
                mock_db,
                studio_id=studio_id,
                records=[
                    {
                        "codice_fiscale": "RSSMRA80A01H501Z",
                        "nome": "Mario Rossi",
                        "comune": "Roma",
                        "provincia": "RM",
                        "tipo_cliente": "persona_fisica",
                    },
                    {
                        "codice_fiscale": "VRDLGI85B02F205X",
                        "nome": "Luigi Verdi",
                        "comune": "Milano",
                        "provincia": "MI",
                        "tipo_cliente": "ditta_individuale",
                    },
                ],
            )

        assert report.total == 2
        assert report.success_count == 2
        assert report.error_count == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_import_missing_required_fields(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Rows with missing required fields are reported as errors."""
        from app.services.client_import_service import ClientImportService

        svc = ClientImportService()
        report = await svc.import_from_records(
            mock_db,
            studio_id=studio_id,
            records=[
                {"codice_fiscale": "ABC123", "nome": "Test"},  # missing comune, provincia
            ],
        )

        assert report.total == 1
        assert report.error_count == 1
        assert report.success_count == 0
        assert len(report.errors) == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_import_duplicate_cf_in_batch(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Duplicate codice_fiscale within a batch is detected."""
        from app.services.client_import_service import ClientImportService

        svc = ClientImportService()
        mock_client = MagicMock(id=1)
        with patch.object(svc._client_service, "create", AsyncMock(return_value=mock_client)):
            report = await svc.import_from_records(
                mock_db,
                studio_id=studio_id,
                records=[
                    {
                        "codice_fiscale": "DUP123",
                        "nome": "First",
                        "comune": "Roma",
                        "provincia": "RM",
                    },
                    {
                        "codice_fiscale": "DUP123",
                        "nome": "Second",
                        "comune": "Roma",
                        "provincia": "RM",
                    },
                ],
            )

        assert report.total == 2
        assert report.success_count == 1
        assert report.error_count == 1


# ---------------------------------------------------------------------------
# Step 4: Chat
# ---------------------------------------------------------------------------


class TestStep4Chat:
    """Step 4 — Save and retrieve chat interactions."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_save_chat_interaction(self, mock_db: AsyncMock, user_id: int) -> None:
        """ChatHistoryService saves a chat interaction and returns record ID."""
        from app.services.chat_history_service import ChatHistoryService

        svc = ChatHistoryService()
        session_id = f"e2e-session-{uuid4()}"

        with patch("app.services.chat_history_service.get_db"):
            record_id = await svc.save_chat_interaction(
                user_id=user_id,
                session_id=session_id,
                user_query="Qual è l'aliquota IVA ordinaria in Italia?",
                ai_response="L'aliquota IVA ordinaria in Italia è del 22%.",
                db=mock_db,
                model_used="claude-3-5-sonnet",
                tokens_used=200,
                cost_cents=3,
                response_time_ms=800,
                response_cached=False,
                italian_content=True,
            )

        assert record_id is not None
        assert isinstance(record_id, str)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_save_cached_response(self, mock_db: AsyncMock, user_id: int) -> None:
        """Cached responses are saved with response_cached=True."""
        from app.services.chat_history_service import ChatHistoryService

        svc = ChatHistoryService()
        session_id = f"e2e-session-{uuid4()}"

        with patch("app.services.chat_history_service.get_db"):
            record_id = await svc.save_chat_interaction(
                user_id=user_id,
                session_id=session_id,
                user_query="Test cached query",
                ai_response="Test cached response",
                db=mock_db,
                response_cached=True,
            )

        assert record_id is not None


# ---------------------------------------------------------------------------
# Step 5: View Matches
# ---------------------------------------------------------------------------


class TestStep5ViewMatches:
    """Step 5 — Proactive matching suggestions are created and queryable."""

    def test_proactive_suggestion_creation(self, studio_id: UUID) -> None:
        """ProactiveSuggestion can be constructed with correct fields."""
        from app.models.proactive_suggestion import ProactiveSuggestion

        suggestion = ProactiveSuggestion(
            studio_id=studio_id,
            knowledge_item_id=42,
            matched_client_ids=[1, 2, 3],
            match_score=0.87,
            suggestion_text="Nuova normativa IVA applicabile a 3 clienti.",
            is_read=False,
            is_dismissed=False,
        )

        assert suggestion.studio_id == studio_id
        assert suggestion.knowledge_item_id == 42
        assert suggestion.matched_client_ids == [1, 2, 3]
        assert suggestion.match_score == 0.87
        assert suggestion.is_read is False
        assert suggestion.is_dismissed is False

    def test_suggestion_mark_read(self, studio_id: UUID) -> None:
        """Suggestion can be marked as read."""
        from app.models.proactive_suggestion import ProactiveSuggestion

        suggestion = ProactiveSuggestion(
            studio_id=studio_id,
            knowledge_item_id=1,
            matched_client_ids=[],
            match_score=0.5,
            suggestion_text="Test",
        )
        suggestion.is_read = True
        assert suggestion.is_read is True

    def test_suggestion_dismiss(self, studio_id: UUID) -> None:
        """Suggestion can be dismissed."""
        from app.models.proactive_suggestion import ProactiveSuggestion

        suggestion = ProactiveSuggestion(
            studio_id=studio_id,
            knowledge_item_id=1,
            matched_client_ids=[],
            match_score=0.5,
            suggestion_text="Test",
        )
        suggestion.is_dismissed = True
        assert suggestion.is_dismissed is True


# ---------------------------------------------------------------------------
# Step 6: Create Communication
# ---------------------------------------------------------------------------


class TestStep6CreateCommunication:
    """Step 6 — Create communication draft via CommunicationService."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_draft(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: int,
        mock_audit: MagicMock,
    ) -> None:
        """CommunicationService creates a DRAFT communication."""
        from app.services.communication_service import CommunicationService

        svc = CommunicationService()
        comm = await svc.create_draft(
            mock_db,
            studio_id=studio_id,
            subject="Scadenza IVA trimestrale",
            content="Gentile cliente, la scadenza IVA trimestrale è il 16 maggio.",
            channel=CanaleInvio.EMAIL,
            created_by=user_id,
            client_id=1,
            normativa_riferimento="Art. 1 DPR 100/1998",
        )

        assert comm.subject == "Scadenza IVA trimestrale"
        assert comm.status == StatoComunicazione.DRAFT
        assert comm.created_by == user_id
        assert comm.client_id == 1
        assert comm.normativa_riferimento == "Art. 1 DPR 100/1998"
        assert comm.channel == CanaleInvio.EMAIL
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_draft_whatsapp(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: int,
        mock_audit: MagicMock,
    ) -> None:
        """Communication can target WhatsApp channel."""
        from app.services.communication_service import CommunicationService

        svc = CommunicationService()
        comm = await svc.create_draft(
            mock_db,
            studio_id=studio_id,
            subject="Promemoria",
            content="Promemoria scadenza.",
            channel=CanaleInvio.WHATSAPP,
            created_by=user_id,
        )

        assert comm.channel == CanaleInvio.WHATSAPP


# ---------------------------------------------------------------------------
# Step 7: Approve Communication
# ---------------------------------------------------------------------------


class TestStep7ApproveCommunication:
    """Step 7 — Communication approval workflow: submit → approve."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_submit_and_approve(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: int,
        approver_id: int,
        mock_audit: MagicMock,
    ) -> None:
        """DRAFT → PENDING_REVIEW → APPROVED workflow succeeds."""
        from app.services.communication_service import CommunicationService

        svc = CommunicationService()
        comm_id = uuid4()

        # Create a mock communication starting as DRAFT
        mock_comm = MagicMock()
        mock_comm.id = comm_id
        mock_comm.status = StatoComunicazione.DRAFT
        mock_comm.created_by = user_id
        mock_comm.approved_by = None
        mock_comm.approved_at = None

        # Step 7a: Submit for review
        with patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)):
            result = await svc.submit_for_review(mock_db, communication_id=comm_id, studio_id=studio_id)

        assert result is not None
        assert result.status == StatoComunicazione.PENDING_REVIEW

        # Step 7b: Approve (different user)
        with patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)):
            result = await svc.approve(
                mock_db,
                communication_id=comm_id,
                studio_id=studio_id,
                approved_by=approver_id,
            )

        assert result is not None
        assert result.status == StatoComunicazione.APPROVED
        assert result.approved_by == approver_id
        assert result.approved_at is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_self_approval_blocked(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: int,
        mock_audit: MagicMock,
    ) -> None:
        """Creator cannot approve their own communication."""
        from app.services.communication_service import CommunicationService

        svc = CommunicationService()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.PENDING_REVIEW
        mock_comm.created_by = user_id

        with (
            patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)),
            pytest.raises(ValueError, match="auto-approvazione"),
        ):
            await svc.approve(
                mock_db,
                communication_id=uuid4(),
                studio_id=studio_id,
                approved_by=user_id,
            )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_reject_workflow(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        mock_audit: MagicMock,
    ) -> None:
        """PENDING_REVIEW → REJECTED workflow succeeds."""
        from app.services.communication_service import CommunicationService

        svc = CommunicationService()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.PENDING_REVIEW

        with patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)):
            result = await svc.reject(mock_db, communication_id=uuid4(), studio_id=studio_id)

        assert result is not None
        assert result.status == StatoComunicazione.REJECTED


# ---------------------------------------------------------------------------
# Step 8: Send Communication
# ---------------------------------------------------------------------------


class TestStep8SendCommunication:
    """Step 8 — Mark communication as sent or send via email service."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_mark_sent(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        mock_audit: MagicMock,
    ) -> None:
        """APPROVED → SENT transition sets sent_at timestamp."""
        from app.services.communication_service import CommunicationService

        svc = CommunicationService()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.APPROVED
        mock_comm.sent_at = None

        with patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)):
            result = await svc.mark_sent(mock_db, communication_id=uuid4(), studio_id=studio_id)

        assert result is not None
        assert result.status == StatoComunicazione.SENT
        assert result.sent_at is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_email_service_send_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        mock_audit: MagicMock,
    ) -> None:
        """CommunicationEmailService sends email and marks as SENT."""
        from app.services.communication_email_service import CommunicationEmailService

        email_svc = CommunicationEmailService()
        comm_id = uuid4()

        # Mock the communication returned from communication_service
        mock_comm = MagicMock()
        mock_comm.id = comm_id
        mock_comm.status = StatoComunicazione.APPROVED
        mock_comm.subject = "Test Subject"
        mock_comm.content = "Test Body"

        # Mock the sent result
        mock_sent = MagicMock()
        mock_sent.status = StatoComunicazione.SENT

        with (
            patch("app.services.communication_email_service.communication_service") as mock_comm_svc,
            patch.object(email_svc, "_send_smtp") as mock_smtp,
        ):
            mock_comm_svc.get_by_id = AsyncMock(return_value=mock_comm)
            mock_comm_svc.mark_sent = AsyncMock(return_value=mock_sent)

            result = await email_svc.send_communication(
                mock_db,
                communication_id=comm_id,
                studio_id=studio_id,
                recipient_email="cliente@example.it",
            )

        assert result is not None
        assert result.status == StatoComunicazione.SENT
        mock_smtp.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_email_service_invalid_email(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        mock_audit: MagicMock,
    ) -> None:
        """Invalid recipient email raises ValueError."""
        from app.services.communication_email_service import CommunicationEmailService

        email_svc = CommunicationEmailService()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.APPROVED

        with (
            patch("app.services.communication_email_service.communication_service") as mock_comm_svc,
            pytest.raises(ValueError, match="email"),
        ):
            mock_comm_svc.get_by_id = AsyncMock(return_value=mock_comm)

            await email_svc.send_communication(
                mock_db,
                communication_id=uuid4(),
                studio_id=studio_id,
                recipient_email="invalid-no-at",
            )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_mark_failed_after_retries(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        mock_audit: MagicMock,
    ) -> None:
        """Communication is marked FAILED when SMTP retries are exhausted."""
        import smtplib

        from app.services.communication_email_service import CommunicationEmailService

        email_svc = CommunicationEmailService()

        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.APPROVED
        mock_comm.subject = "Fail Test"
        mock_comm.content = "Will fail"

        mock_failed = MagicMock()
        mock_failed.status = StatoComunicazione.FAILED

        with (
            patch("app.services.communication_email_service.communication_service") as mock_comm_svc,
            patch.object(
                email_svc,
                "_send_smtp",
                side_effect=smtplib.SMTPException("Connection refused"),
            ),
        ):
            mock_comm_svc.get_by_id = AsyncMock(return_value=mock_comm)
            mock_comm_svc.mark_failed = AsyncMock(return_value=mock_failed)

            result = await email_svc.send_communication(
                mock_db,
                communication_id=uuid4(),
                studio_id=studio_id,
                recipient_email="test@example.it",
            )

        assert result is not None
        assert result.status == StatoComunicazione.FAILED


# ---------------------------------------------------------------------------
# Step 9: View Dashboard
# ---------------------------------------------------------------------------


class TestStep9ViewDashboard:
    """Step 9 — Dashboard aggregation returns correct data structure."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dashboard_data_structure(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Dashboard returns all required sections."""
        from app.services.dashboard_service import DashboardService

        svc = DashboardService()

        with (
            patch.object(svc, "_get_from_cache", AsyncMock(return_value=None)),
            patch.object(svc, "_set_cache", AsyncMock()),
            patch.object(svc, "_get_client_stats", AsyncMock(return_value={"total": 10})),
            patch.object(
                svc,
                "_get_communication_stats",
                AsyncMock(return_value={"total": 5, "pending_review": 2}),
            ),
            patch.object(
                svc,
                "_get_procedure_stats",
                AsyncMock(return_value={"total": 3, "active": 1}),
            ),
            patch.object(svc, "_get_match_stats", AsyncMock(return_value={"active_rules": 7})),
            patch.object(
                svc,
                "_get_roi_stats",
                AsyncMock(return_value={"hours_saved": 15, "breakdown": {}}),
            ),
        ):
            result = await svc.get_dashboard_data(mock_db, studio_id=studio_id)

        assert "clients" in result
        assert "communications" in result
        assert "procedures" in result
        assert "matches" in result
        assert "roi" in result
        assert result["clients"]["total"] == 10
        assert result["communications"]["total"] == 5
        assert result["communications"]["pending_review"] == 2
        assert result["procedures"]["active"] == 1
        assert result["matches"]["active_rules"] == 7
        assert result["roi"]["hours_saved"] == 15

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dashboard_cache_hit(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Dashboard returns cached data without querying DB."""
        from app.services.dashboard_service import DashboardService

        svc = DashboardService()
        cached = {"clients": {"total": 42}, "communications": {"total": 0, "pending_review": 0}}

        with patch.object(svc, "_get_from_cache", AsyncMock(return_value=cached)):
            result = await svc.get_dashboard_data(mock_db, studio_id=studio_id)

        assert result == cached
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dashboard_roi_fallback(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """ROI section gracefully degrades when service is unavailable."""
        from app.services.dashboard_service import DashboardService

        svc = DashboardService()

        with patch("app.services.roi_metrics_service.roi_metrics_service") as mock_roi:
            mock_roi.get_studio_metrics = AsyncMock(side_effect=Exception("Service down"))
            result = await svc._get_roi_stats(mock_db, studio_id)

        assert result["hours_saved"] == 0


# ---------------------------------------------------------------------------
# Full Journey Integration Test
# ---------------------------------------------------------------------------


class TestFullJourneyE2E:
    """End-to-end test tying all 9 steps together in a single flow."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_complete_user_journey(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: int,
        approver_id: int,
        mock_audit: MagicMock,
    ) -> None:
        """Validate the complete PratikoAI 2.0 user journey end-to-end.

        Steps: Register → Create Studio → Import Clients → Chat →
        View Matches → Create Communication → Approve → Send → Dashboard
        """
        # --- Step 1: Register ---
        password = "JourneyP@ss1"
        hashed = User.hash_password(password)
        user = User(
            id=user_id,
            email="journey_user@pratikoai.it",
            hashed_password=hashed,
            role=UserRole.REGULAR_USER.value,
            provider="email",
            studio_id=str(studio_id),
        )
        assert user.verify_password(password)

        # --- Step 2: Create Studio ---
        from app.services.studio_service import StudioService

        studio_svc = StudioService()

        mock_slug_check = MagicMock()
        mock_slug_check.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_slug_check)

        studio = await studio_svc.create(
            mock_db,
            name="Studio Bianchi E2E",
            slug="studio-bianchi-e2e",
            max_clients=50,
        )
        assert studio.name == "Studio Bianchi E2E"

        # --- Step 3: Import Clients ---
        from app.services.client_import_service import ClientImportService

        import_svc = ClientImportService()
        mock_client = MagicMock(id=1)

        with patch.object(import_svc._client_service, "create", AsyncMock(return_value=mock_client)):
            report = await import_svc.import_from_records(
                mock_db,
                studio_id=studio_id,
                records=[
                    {
                        "codice_fiscale": "BNCMRA90A01H501Z",
                        "nome": "Maria Bianchi",
                        "comune": "Firenze",
                        "provincia": "FI",
                    },
                ],
            )
        assert report.success_count == 1

        # --- Step 4: Chat ---
        from app.services.chat_history_service import ChatHistoryService

        chat_svc = ChatHistoryService()
        with patch("app.services.chat_history_service.get_db"):
            record_id = await chat_svc.save_chat_interaction(
                user_id=user_id,
                session_id=f"e2e-journey-{uuid4()}",
                user_query="Quale scadenza ha l'IVA trimestrale?",
                ai_response="La scadenza IVA trimestrale è il 16 del secondo mese successivo.",
                db=mock_db,
                model_used="claude-3-5-sonnet",
                tokens_used=150,
                italian_content=True,
            )
        assert record_id is not None

        # --- Step 5: View Matches ---
        from app.models.proactive_suggestion import ProactiveSuggestion

        suggestion = ProactiveSuggestion(
            studio_id=studio_id,
            knowledge_item_id=99,
            matched_client_ids=[1],
            match_score=0.92,
            suggestion_text="Scadenza IVA applicabile a Maria Bianchi.",
        )
        assert suggestion.match_score == 0.92
        assert len(suggestion.matched_client_ids) == 1

        # --- Step 6: Create Communication ---
        from app.services.communication_service import CommunicationService

        comm_svc = CommunicationService()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        comm = await comm_svc.create_draft(
            mock_db,
            studio_id=studio_id,
            subject="Promemoria scadenza IVA",
            content="La scadenza IVA trimestrale è il 16 maggio.",
            channel=CanaleInvio.EMAIL,
            created_by=user_id,
            client_id=1,
        )
        comm_id = comm.id
        assert comm.status == StatoComunicazione.DRAFT

        # --- Step 7: Approve Communication ---
        # Submit for review
        with patch.object(comm_svc, "_get_communication", AsyncMock(return_value=comm)):
            await comm_svc.submit_for_review(mock_db, communication_id=comm_id, studio_id=studio_id)
        assert comm.status == StatoComunicazione.PENDING_REVIEW  # type: ignore[comparison-overlap]

        # Approve by different user
        with patch.object(comm_svc, "_get_communication", AsyncMock(return_value=comm)):
            await comm_svc.approve(
                mock_db,
                communication_id=comm_id,
                studio_id=studio_id,
                approved_by=approver_id,
            )
        assert comm.status == StatoComunicazione.APPROVED

        # --- Step 8: Send ---
        with patch.object(comm_svc, "_get_communication", AsyncMock(return_value=comm)):
            await comm_svc.mark_sent(mock_db, communication_id=comm_id, studio_id=studio_id)
        assert comm.status == StatoComunicazione.SENT
        assert comm.sent_at is not None

        # --- Step 9: View Dashboard ---
        from app.services.dashboard_service import DashboardService

        dash_svc = DashboardService()

        with (
            patch.object(dash_svc, "_get_from_cache", AsyncMock(return_value=None)),
            patch.object(dash_svc, "_set_cache", AsyncMock()),
            patch.object(dash_svc, "_get_client_stats", AsyncMock(return_value={"total": 1})),
            patch.object(
                dash_svc,
                "_get_communication_stats",
                AsyncMock(return_value={"total": 1, "pending_review": 0}),
            ),
            patch.object(
                dash_svc,
                "_get_procedure_stats",
                AsyncMock(return_value={"total": 0, "active": 0}),
            ),
            patch.object(dash_svc, "_get_match_stats", AsyncMock(return_value={"active_rules": 1})),
            patch.object(
                dash_svc,
                "_get_roi_stats",
                AsyncMock(return_value={"hours_saved": 2, "breakdown": {}}),
            ),
        ):
            dashboard = await dash_svc.get_dashboard_data(mock_db, studio_id=studio_id)

        assert dashboard["clients"]["total"] == 1
        assert dashboard["communications"]["total"] == 1
        assert dashboard["matches"]["active_rules"] == 1
        assert dashboard["roi"]["hours_saved"] == 2

    @pytest.mark.asyncio(loop_scope="function")
    async def test_invalid_transition_blocked_in_journey(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        mock_audit: MagicMock,
    ) -> None:
        """Cannot skip workflow steps (e.g. DRAFT directly to SENT)."""
        from app.services.communication_service import CommunicationService

        svc = CommunicationService()
        mock_comm = MagicMock()
        mock_comm.status = StatoComunicazione.DRAFT

        with (
            patch.object(svc, "_get_communication", AsyncMock(return_value=mock_comm)),
            pytest.raises(ValueError, match="non è valida"),
        ):
            await svc.approve(
                mock_db,
                communication_id=uuid4(),
                studio_id=studio_id,
                approved_by=99901,
            )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_journey_with_rejection_and_resend(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: int,
        approver_id: int,
        mock_audit: MagicMock,
    ) -> None:
        """Communication rejected → back to draft → resubmit → approve → send."""
        from app.services.communication_service import CommunicationService

        svc = CommunicationService()

        # Create draft
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        comm = await svc.create_draft(
            mock_db,
            studio_id=studio_id,
            subject="Rejected then resent",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=user_id,
        )
        comm_id = comm.id

        # Submit
        with patch.object(svc, "_get_communication", AsyncMock(return_value=comm)):
            await svc.submit_for_review(mock_db, communication_id=comm_id, studio_id=studio_id)
        assert comm.status == StatoComunicazione.PENDING_REVIEW

        # Reject
        with patch.object(svc, "_get_communication", AsyncMock(return_value=comm)):
            await svc.reject(mock_db, communication_id=comm_id, studio_id=studio_id)
        assert comm.status == StatoComunicazione.REJECTED  # type: ignore[comparison-overlap]

        # Revert to draft (REJECTED → DRAFT is valid)
        comm.status = StatoComunicazione.DRAFT

        # Resubmit
        with patch.object(svc, "_get_communication", AsyncMock(return_value=comm)):
            await svc.submit_for_review(mock_db, communication_id=comm_id, studio_id=studio_id)
        assert comm.status == StatoComunicazione.PENDING_REVIEW

        # Approve
        with patch.object(svc, "_get_communication", AsyncMock(return_value=comm)):
            await svc.approve(
                mock_db,
                communication_id=comm_id,
                studio_id=studio_id,
                approved_by=approver_id,
            )
        assert comm.status == StatoComunicazione.APPROVED

        # Send
        with patch.object(svc, "_get_communication", AsyncMock(return_value=comm)):
            await svc.mark_sent(mock_db, communication_id=comm_id, studio_id=studio_id)
        assert comm.status == StatoComunicazione.SENT
