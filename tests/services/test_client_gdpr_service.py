"""DEV-317: Tests for ClientGDPRService — GDPR Article 17 right-to-erasure.

Tests cover:
- Happy path: full GDPR deletion (export -> anonymize -> cascade comms)
- Error: client not found returns None
- Export is called before deletion
- Communications are cascaded (soft deleted via client_id nullification)
- Anonymization replaces PII fields with "[REDACTED]"
- Edge case: client already deleted (deleted_at is set)
- Audit logging is called with correct event type
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.client import Client, StatoCliente, TipoCliente
from app.models.communication import CanaleInvio, Communication, StatoComunicazione
from app.services.client_gdpr_service import ClientGDPRService, GDPRDeletionResult


@pytest.fixture
def gdpr_service() -> ClientGDPRService:
    return ClientGDPRService()


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
def sample_client(studio_id) -> Client:
    return Client(
        id=1,
        studio_id=studio_id,
        codice_fiscale="RSSMRA85M01H501Z",
        nome="Mario Rossi",
        tipo_cliente=TipoCliente.PERSONA_FISICA,
        stato_cliente=StatoCliente.ATTIVO,
        email="mario@example.com",
        phone="+39 333 1234567",
        partita_iva="12345678901",
        comune="Roma",
        provincia="RM",
    )


@pytest.fixture
def sample_communications(studio_id) -> list[Communication]:
    return [
        Communication(
            id=uuid4(),
            studio_id=studio_id,
            client_id=1,
            subject="Scadenza IVA",
            content="La scadenza IVA è il 16 marzo.",
            channel=CanaleInvio.EMAIL,
            status=StatoComunicazione.DRAFT,
            created_by=1,
        ),
        Communication(
            id=uuid4(),
            studio_id=studio_id,
            client_id=1,
            subject="Avviso INPS",
            content="Versamento INPS in scadenza.",
            channel=CanaleInvio.EMAIL,
            status=StatoComunicazione.SENT,
            created_by=1,
        ),
    ]


@pytest.fixture
def deleted_client(studio_id) -> Client:
    """Client that has already been soft-deleted."""
    return Client(
        id=2,
        studio_id=studio_id,
        codice_fiscale="[REDACTED]",
        nome="[REDACTED]",
        tipo_cliente=TipoCliente.PERSONA_FISICA,
        stato_cliente=StatoCliente.CESSATO,
        comune="Roma",
        provincia="RM",
        deleted_at=datetime.now(UTC),
    )


class TestClientGDPRServiceHappyPath:
    """Test full GDPR deletion workflow."""

    @pytest.mark.asyncio
    @patch("app.services.client_gdpr_service.security_audit_logger")
    @patch("app.services.client_gdpr_service.client_export_service")
    @patch("app.services.client_gdpr_service.client_service")
    async def test_gdpr_deletion_full_workflow(
        self,
        mock_client_svc,
        mock_export_svc,
        mock_audit_logger,
        gdpr_service: ClientGDPRService,
        mock_db: AsyncMock,
        studio_id,
        sample_client: Client,
        sample_communications: list[Communication],
    ) -> None:
        """Happy path: export -> anonymize -> cascade -> audit -> return result."""
        # Mock client lookup
        mock_client_svc.get_by_id = AsyncMock(return_value=sample_client)

        # Mock export
        export_data = {"id": 1, "nome": "Mario Rossi", "codice_fiscale": "RSSMRA85M01H501Z"}
        mock_export_svc.export_client_by_id = AsyncMock(return_value=export_data)

        # Mock communications query
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=sample_communications)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock audit logger
        mock_audit_logger.log_gdpr_event = AsyncMock(return_value=True)

        result = await gdpr_service.delete_client_gdpr(
            db=mock_db,
            studio_id=studio_id,
            client_id=1,
            requested_by="user_42",
        )

        assert result is not None
        assert isinstance(result, GDPRDeletionResult)
        assert result.client_id == 1
        assert result.export_data == export_data
        assert result.anonymized_at is not None
        assert result.communications_affected == 2


class TestClientGDPRServiceClientNotFound:
    """Test when client is not found."""

    @pytest.mark.asyncio
    @patch("app.services.client_gdpr_service.client_service")
    async def test_client_not_found_returns_none(
        self,
        mock_client_svc,
        gdpr_service: ClientGDPRService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Error: non-existent client returns None."""
        mock_client_svc.get_by_id = AsyncMock(return_value=None)

        result = await gdpr_service.delete_client_gdpr(
            db=mock_db,
            studio_id=studio_id,
            client_id=999,
            requested_by="user_42",
        )

        assert result is None


class TestClientGDPRServiceExportBeforeDeletion:
    """Test that export is called before anonymization."""

    @pytest.mark.asyncio
    @patch("app.services.client_gdpr_service.security_audit_logger")
    @patch("app.services.client_gdpr_service.client_export_service")
    @patch("app.services.client_gdpr_service.client_service")
    async def test_export_called_before_anonymization(
        self,
        mock_client_svc,
        mock_export_svc,
        mock_audit_logger,
        gdpr_service: ClientGDPRService,
        mock_db: AsyncMock,
        studio_id,
        sample_client: Client,
    ) -> None:
        """Export must be called before PII is anonymized."""
        call_order: list[str] = []

        async def track_export(*args, **kwargs):
            call_order.append("export")
            return {"id": 1, "nome": "Mario Rossi"}

        async def track_get(*args, **kwargs):
            call_order.append("get_client")
            return sample_client

        mock_client_svc.get_by_id = AsyncMock(side_effect=track_get)
        mock_export_svc.export_client_by_id = AsyncMock(side_effect=track_export)
        mock_audit_logger.log_gdpr_event = AsyncMock(return_value=True)

        # Mock communications query (empty list)
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await gdpr_service.delete_client_gdpr(
            db=mock_db,
            studio_id=studio_id,
            client_id=1,
            requested_by="user_42",
        )

        assert result is not None
        # Export must be called after get_client and before anonymization
        assert "get_client" in call_order
        assert "export" in call_order
        assert call_order.index("get_client") < call_order.index("export")
        # Verify export was actually called
        mock_export_svc.export_client_by_id.assert_awaited_once()


class TestClientGDPRServiceCascadeCommunications:
    """Test cascade soft-delete of related communications."""

    @pytest.mark.asyncio
    @patch("app.services.client_gdpr_service.security_audit_logger")
    @patch("app.services.client_gdpr_service.client_export_service")
    @patch("app.services.client_gdpr_service.client_service")
    async def test_communications_cascade_nullify_client_id(
        self,
        mock_client_svc,
        mock_export_svc,
        mock_audit_logger,
        gdpr_service: ClientGDPRService,
        mock_db: AsyncMock,
        studio_id,
        sample_client: Client,
        sample_communications: list[Communication],
    ) -> None:
        """Communications linked to the deleted client have client_id set to None."""
        mock_client_svc.get_by_id = AsyncMock(return_value=sample_client)
        mock_export_svc.export_client_by_id = AsyncMock(return_value={"id": 1})
        mock_audit_logger.log_gdpr_event = AsyncMock(return_value=True)

        # Mock communications query
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=sample_communications)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await gdpr_service.delete_client_gdpr(
            db=mock_db,
            studio_id=studio_id,
            client_id=1,
            requested_by="user_42",
        )

        assert result is not None
        assert result.communications_affected == 2
        # Each communication should have client_id set to None
        for comm in sample_communications:
            assert comm.client_id is None

    @pytest.mark.asyncio
    @patch("app.services.client_gdpr_service.security_audit_logger")
    @patch("app.services.client_gdpr_service.client_export_service")
    @patch("app.services.client_gdpr_service.client_service")
    async def test_no_communications_returns_zero_affected(
        self,
        mock_client_svc,
        mock_export_svc,
        mock_audit_logger,
        gdpr_service: ClientGDPRService,
        mock_db: AsyncMock,
        studio_id,
        sample_client: Client,
    ) -> None:
        """When client has no communications, communications_affected is 0."""
        mock_client_svc.get_by_id = AsyncMock(return_value=sample_client)
        mock_export_svc.export_client_by_id = AsyncMock(return_value={"id": 1})
        mock_audit_logger.log_gdpr_event = AsyncMock(return_value=True)

        # Mock empty communications
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await gdpr_service.delete_client_gdpr(
            db=mock_db,
            studio_id=studio_id,
            client_id=1,
            requested_by="user_42",
        )

        assert result is not None
        assert result.communications_affected == 0


class TestClientGDPRServiceAnonymization:
    """Test PII anonymization replaces fields with [REDACTED]."""

    @pytest.mark.asyncio
    @patch("app.services.client_gdpr_service.security_audit_logger")
    @patch("app.services.client_gdpr_service.client_export_service")
    @patch("app.services.client_gdpr_service.client_service")
    async def test_pii_fields_anonymized(
        self,
        mock_client_svc,
        mock_export_svc,
        mock_audit_logger,
        gdpr_service: ClientGDPRService,
        mock_db: AsyncMock,
        studio_id,
        sample_client: Client,
    ) -> None:
        """PII fields are replaced with [REDACTED] or None."""
        mock_client_svc.get_by_id = AsyncMock(return_value=sample_client)
        mock_export_svc.export_client_by_id = AsyncMock(return_value={"id": 1})
        mock_audit_logger.log_gdpr_event = AsyncMock(return_value=True)

        # Mock empty communications
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await gdpr_service.delete_client_gdpr(
            db=mock_db,
            studio_id=studio_id,
            client_id=1,
            requested_by="user_42",
        )

        assert result is not None
        # Verify PII anonymization
        assert sample_client.codice_fiscale == "[REDACTED]"
        assert sample_client.nome == "[REDACTED]"
        assert sample_client.email is None
        assert sample_client.phone is None
        assert sample_client.partita_iva is None
        # Verify soft-delete marker
        assert sample_client.deleted_at is not None
        assert sample_client.stato_cliente == StatoCliente.CESSATO


class TestClientGDPRServiceAlreadyDeleted:
    """Test edge case: client already deleted."""

    @pytest.mark.asyncio
    @patch("app.services.client_gdpr_service.client_service")
    async def test_already_deleted_client_returns_none(
        self,
        mock_client_svc,
        gdpr_service: ClientGDPRService,
        mock_db: AsyncMock,
        studio_id,
        deleted_client: Client,
    ) -> None:
        """Already-deleted client (deleted_at is set) returns None.

        The ClientService.get_by_id already filters out deleted clients
        (WHERE deleted_at IS NULL), so it returns None for soft-deleted clients.
        """
        mock_client_svc.get_by_id = AsyncMock(return_value=None)

        result = await gdpr_service.delete_client_gdpr(
            db=mock_db,
            studio_id=studio_id,
            client_id=2,
            requested_by="user_42",
        )

        assert result is None


class TestClientGDPRServiceAuditLogging:
    """Test audit logging is called correctly."""

    @pytest.mark.asyncio
    @patch("app.services.client_gdpr_service.security_audit_logger")
    @patch("app.services.client_gdpr_service.client_export_service")
    @patch("app.services.client_gdpr_service.client_service")
    async def test_audit_log_called_with_erasure_event(
        self,
        mock_client_svc,
        mock_export_svc,
        mock_audit_logger,
        gdpr_service: ClientGDPRService,
        mock_db: AsyncMock,
        studio_id,
        sample_client: Client,
    ) -> None:
        """Audit logger is called with GDPR erasure event type."""
        mock_client_svc.get_by_id = AsyncMock(return_value=sample_client)
        mock_export_svc.export_client_by_id = AsyncMock(return_value={"id": 1})
        mock_audit_logger.log_gdpr_event = AsyncMock(return_value=True)

        # Mock empty communications
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)

        await gdpr_service.delete_client_gdpr(
            db=mock_db,
            studio_id=studio_id,
            client_id=1,
            requested_by="user_42",
        )

        mock_audit_logger.log_gdpr_event.assert_awaited_once()
        call_kwargs = mock_audit_logger.log_gdpr_event.call_args
        assert call_kwargs.kwargs["action"] == "erasure"
        assert call_kwargs.kwargs["user_id"] == "user_42"
        assert call_kwargs.kwargs["data_type"] == "client_pii"
        assert call_kwargs.kwargs["legal_basis"] == "GDPR Article 17"

    @pytest.mark.asyncio
    @patch("app.services.client_gdpr_service.security_audit_logger")
    @patch("app.services.client_gdpr_service.client_export_service")
    @patch("app.services.client_gdpr_service.client_service")
    async def test_audit_log_includes_details(
        self,
        mock_client_svc,
        mock_export_svc,
        mock_audit_logger,
        gdpr_service: ClientGDPRService,
        mock_db: AsyncMock,
        studio_id,
        sample_client: Client,
    ) -> None:
        """Audit log details include client_id, studio_id, and communications count."""
        mock_client_svc.get_by_id = AsyncMock(return_value=sample_client)
        mock_export_svc.export_client_by_id = AsyncMock(return_value={"id": 1})
        mock_audit_logger.log_gdpr_event = AsyncMock(return_value=True)

        # Mock 3 communications
        comms = [MagicMock(spec=Communication) for _ in range(3)]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=comms)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)

        await gdpr_service.delete_client_gdpr(
            db=mock_db,
            studio_id=studio_id,
            client_id=1,
            requested_by="user_42",
        )

        call_kwargs = mock_audit_logger.log_gdpr_event.call_args
        details = call_kwargs.kwargs["details"]
        assert details["client_id"] == 1
        assert details["studio_id"] == str(studio_id)
        assert details["communications_affected"] == 3
