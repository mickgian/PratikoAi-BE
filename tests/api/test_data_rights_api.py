"""Tests for DEV-377: Enhanced Client Data Rights API — GDPR data rights endpoints.

TDD: Tests written FIRST before implementation.
Tests all GDPR data rights endpoints with mocked services.

Endpoints tested:
- GET /data-rights/access/{client_id}    (Article 15 — Access)
- GET /data-rights/export/{client_id}    (Article 20 — Portability)
- PUT /data-rights/rectify/{client_id}   (Article 16 — Rectification)
- DELETE /data-rights/erase/{client_id}  (Article 17 — Erasure)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.models.client import StatoCliente, TipoCliente

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STUDIO_ID = uuid4()
USER_ID = "user-abc-123"


@pytest.fixture
def studio_id() -> UUID:
    """Fixed studio UUID for tenant isolation tests."""
    return STUDIO_ID


@pytest.fixture
def user_id() -> str:
    """Fixed user ID for audit trail tests."""
    return USER_ID


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock async database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def sample_client(studio_id: UUID) -> MagicMock:
    """Return a mock Client object with standard fields."""
    client = MagicMock()
    client.id = 1
    client.studio_id = studio_id
    client.codice_fiscale = "RSSMRA85M01H501Z"
    client.nome = "Mario Rossi"
    client.tipo_cliente = TipoCliente.PERSONA_FISICA
    client.stato_cliente = StatoCliente.ATTIVO
    client.comune = "Roma"
    client.provincia = "RM"
    client.partita_iva = None
    client.email = "mario@example.com"
    client.phone = "+39 333 1234567"
    client.indirizzo = "Via Roma 1"
    client.cap = "00100"
    client.note_studio = None
    client.created_at = datetime.now(UTC)
    client.updated_at = None
    client.deleted_at = None
    return client


@pytest.fixture
def sample_export_data() -> dict:
    """Return sample export data as returned by ClientExportService."""
    return {
        "id": 1,
        "codice_fiscale": "RSSMRA85M01H501Z",
        "nome": "Mario Rossi",
        "tipo_cliente": "persona_fisica",
        "stato_cliente": "attivo",
        "partita_iva": None,
        "email": "mario@example.com",
        "phone": "+39 333 1234567",
        "indirizzo": "Via Roma 1",
        "cap": "00100",
        "comune": "Roma",
        "provincia": "RM",
        "note_studio": None,
    }


@pytest.fixture
def sample_gdpr_deletion_result() -> MagicMock:
    """Return a mock GDPRDeletionResult."""
    result = MagicMock()
    result.client_id = 1
    result.export_data = {"id": 1, "nome": "Mario Rossi"}
    result.anonymized_at = datetime.now(UTC)
    result.communications_affected = 2
    return result


# ---------------------------------------------------------------------------
# GET /data-rights/access/{client_id} — Article 15 Access
# ---------------------------------------------------------------------------


class TestAccessRight:
    """Tests for GET /data-rights/access/{client_id} endpoint."""

    @pytest.mark.asyncio
    async def test_access_right_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
        sample_client: MagicMock,
    ) -> None:
        """Happy path: returns full client data for GDPR access right."""
        from app.api.v1.data_rights import access_client_data

        with patch("app.api.v1.data_rights.client_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=sample_client)
            result = await access_client_data(
                client_id=1,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        assert result["client"]["id"] == 1
        assert result["client"]["nome"] == "Mario Rossi"
        assert result["gdpr_article"] == "Article 15 — Right of Access"
        mock_svc.get_by_id.assert_awaited_once_with(mock_db, client_id=1, studio_id=studio_id)

    @pytest.mark.asyncio
    async def test_access_right_not_found_returns_404(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
    ) -> None:
        """Error case: nonexistent client raises 404."""
        from app.api.v1.data_rights import access_client_data

        with patch("app.api.v1.data_rights.client_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await access_client_data(
                    client_id=999,
                    db=mock_db,
                    x_studio_id=studio_id,
                    x_user_id=user_id,
                )

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_access_right_logs_audit(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
        sample_client: MagicMock,
    ) -> None:
        """Audit: access action is logged with structured logger."""
        from app.api.v1.data_rights import access_client_data

        with (
            patch("app.api.v1.data_rights.client_service") as mock_svc,
            patch("app.api.v1.data_rights.logger") as mock_logger,
        ):
            mock_svc.get_by_id = AsyncMock(return_value=sample_client)
            await access_client_data(
                client_id=1,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "gdpr_access_right_exercised"


# ---------------------------------------------------------------------------
# GET /data-rights/export/{client_id} — Article 20 Portability
# ---------------------------------------------------------------------------


class TestPortabilityRight:
    """Tests for GET /data-rights/export/{client_id} endpoint."""

    @pytest.mark.asyncio
    async def test_export_right_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
        sample_export_data: dict,
    ) -> None:
        """Happy path: returns exported client data for GDPR portability."""
        from app.api.v1.data_rights import export_client_data

        with patch("app.api.v1.data_rights.client_export_service") as mock_svc:
            mock_svc.export_client_by_id = AsyncMock(return_value=sample_export_data)
            result = await export_client_data(
                client_id=1,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        assert result["data"] == sample_export_data
        assert result["gdpr_article"] == "Article 20 — Right to Data Portability"
        assert result["format"] == "application/json"
        mock_svc.export_client_by_id.assert_awaited_once_with(mock_db, studio_id=studio_id, client_id=1)

    @pytest.mark.asyncio
    async def test_export_right_not_found_returns_404(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
    ) -> None:
        """Error case: nonexistent client raises 404."""
        from app.api.v1.data_rights import export_client_data

        with patch("app.api.v1.data_rights.client_export_service") as mock_svc:
            mock_svc.export_client_by_id = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await export_client_data(
                    client_id=999,
                    db=mock_db,
                    x_studio_id=studio_id,
                    x_user_id=user_id,
                )

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_export_right_logs_audit(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
        sample_export_data: dict,
    ) -> None:
        """Audit: export action is logged with structured logger."""
        from app.api.v1.data_rights import export_client_data

        with (
            patch("app.api.v1.data_rights.client_export_service") as mock_svc,
            patch("app.api.v1.data_rights.logger") as mock_logger,
        ):
            mock_svc.export_client_by_id = AsyncMock(return_value=sample_export_data)
            await export_client_data(
                client_id=1,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "gdpr_portability_right_exercised"


# ---------------------------------------------------------------------------
# PUT /data-rights/rectify/{client_id} — Article 16 Rectification
# ---------------------------------------------------------------------------


class TestRectificationRight:
    """Tests for PUT /data-rights/rectify/{client_id} endpoint."""

    @pytest.mark.asyncio
    async def test_rectify_right_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
        sample_client: MagicMock,
    ) -> None:
        """Happy path: updates client fields for GDPR rectification."""
        from app.api.v1.data_rights import RectificationRequest, rectify_client_data

        sample_client.nome = "Mario Rossi Corretto"
        sample_client.email = "mario.corretto@example.com"

        body = RectificationRequest(
            nome="Mario Rossi Corretto",
            email="mario.corretto@example.com",
        )

        with patch("app.api.v1.data_rights.client_service") as mock_svc:
            mock_svc.update = AsyncMock(return_value=sample_client)
            result = await rectify_client_data(
                client_id=1,
                body=body,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        assert result["gdpr_article"] == "Article 16 — Right to Rectification"
        assert result["client"]["nome"] == "Mario Rossi Corretto"
        assert result["rectified_fields"] == ["nome", "email"]
        mock_svc.update.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rectify_right_not_found_returns_404(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
    ) -> None:
        """Error case: nonexistent client raises 404."""
        from app.api.v1.data_rights import RectificationRequest, rectify_client_data

        body = RectificationRequest(nome="Nuovo Nome")

        with patch("app.api.v1.data_rights.client_service") as mock_svc:
            mock_svc.update = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await rectify_client_data(
                    client_id=999,
                    body=body,
                    db=mock_db,
                    x_studio_id=studio_id,
                    x_user_id=user_id,
                )

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rectify_right_no_fields_returns_400(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
    ) -> None:
        """Edge case: no fields provided raises 400."""
        from app.api.v1.data_rights import RectificationRequest, rectify_client_data

        body = RectificationRequest()

        with pytest.raises(HTTPException) as exc_info:
            await rectify_client_data(
                client_id=1,
                body=body,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        assert exc_info.value.status_code == 400
        assert "campo" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rectify_right_logs_audit(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
        sample_client: MagicMock,
    ) -> None:
        """Audit: rectification action is logged with structured logger."""
        from app.api.v1.data_rights import RectificationRequest, rectify_client_data

        sample_client.phone = "+39 333 9999999"
        body = RectificationRequest(phone="+39 333 9999999")

        with (
            patch("app.api.v1.data_rights.client_service") as mock_svc,
            patch("app.api.v1.data_rights.logger") as mock_logger,
        ):
            mock_svc.update = AsyncMock(return_value=sample_client)
            await rectify_client_data(
                client_id=1,
                body=body,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "gdpr_rectification_right_exercised"


# ---------------------------------------------------------------------------
# DELETE /data-rights/erase/{client_id} — Article 17 Erasure
# ---------------------------------------------------------------------------


class TestErasureRight:
    """Tests for DELETE /data-rights/erase/{client_id} endpoint."""

    @pytest.mark.asyncio
    async def test_erase_right_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
        sample_gdpr_deletion_result: MagicMock,
    ) -> None:
        """Happy path: triggers GDPR erasure and returns result."""
        from app.api.v1.data_rights import erase_client_data

        with patch("app.api.v1.data_rights.client_gdpr_service") as mock_svc:
            mock_svc.delete_client_gdpr = AsyncMock(return_value=sample_gdpr_deletion_result)
            result = await erase_client_data(
                client_id=1,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        assert result["gdpr_article"] == "Article 17 — Right to Erasure"
        assert result["client_id"] == 1
        assert result["communications_affected"] == 2
        mock_svc.delete_client_gdpr.assert_awaited_once_with(
            mock_db,
            studio_id=studio_id,
            client_id=1,
            requested_by=user_id,
        )
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_erase_right_not_found_returns_404(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
    ) -> None:
        """Error case: nonexistent client raises 404."""
        from app.api.v1.data_rights import erase_client_data

        with patch("app.api.v1.data_rights.client_gdpr_service") as mock_svc:
            mock_svc.delete_client_gdpr = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await erase_client_data(
                    client_id=999,
                    db=mock_db,
                    x_studio_id=studio_id,
                    x_user_id=user_id,
                )

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_erase_right_logs_audit(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
        sample_gdpr_deletion_result: MagicMock,
    ) -> None:
        """Audit: erasure action is logged with structured logger."""
        from app.api.v1.data_rights import erase_client_data

        with (
            patch("app.api.v1.data_rights.client_gdpr_service") as mock_svc,
            patch("app.api.v1.data_rights.logger") as mock_logger,
        ):
            mock_svc.delete_client_gdpr = AsyncMock(return_value=sample_gdpr_deletion_result)
            await erase_client_data(
                client_id=1,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "gdpr_erasure_right_exercised"

    @pytest.mark.asyncio
    async def test_erase_right_returns_export_data(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        user_id: str,
        sample_gdpr_deletion_result: MagicMock,
    ) -> None:
        """Edge case: erasure response includes exported data before deletion."""
        from app.api.v1.data_rights import erase_client_data

        with patch("app.api.v1.data_rights.client_gdpr_service") as mock_svc:
            mock_svc.delete_client_gdpr = AsyncMock(return_value=sample_gdpr_deletion_result)
            result = await erase_client_data(
                client_id=1,
                db=mock_db,
                x_studio_id=studio_id,
                x_user_id=user_id,
            )

        assert "export_data" in result
        assert result["export_data"] == {"id": 1, "nome": "Mario Rossi"}
