"""Tests for DEV-377: Enhanced Client Data Rights API — coverage for endpoint functions.

These tests call the endpoint handler functions directly with mocked services,
avoiding the DB-dependent import chain that makes tests/api/test_data_rights_api.py
fail in environments without a running PostgreSQL instance.
"""

import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

# Pre-mock the database service module to prevent DB connection during import
# of app.services (which is triggered by data_rights importing client_service).
_original_db_module = sys.modules.get("app.services.database")
if _original_db_module is None:
    sys.modules["app.services.database"] = MagicMock()

# Now we can safely import data_rights endpoints
from app.api.v1.data_rights import (  # noqa: E402
    RectificationRequest,
    access_client_data,
    erase_client_data,
    export_client_data,
    rectify_client_data,
)


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def user_id():
    return "user-test-123"


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def sample_client():
    """Mock client object with all fields."""
    client = MagicMock()
    client.id = 1
    client.codice_fiscale = "RSSMRA85M01H501Z"
    client.nome = "Mario Rossi"
    client.tipo_cliente = MagicMock()
    client.tipo_cliente.value = "persona_fisica"
    client.stato_cliente = MagicMock()
    client.stato_cliente.value = "attivo"
    client.partita_iva = None
    client.email = "mario@example.com"
    client.phone = "+39 333 1234567"
    client.indirizzo = "Via Roma 1"
    client.cap = "00100"
    client.comune = "Roma"
    client.provincia = "RM"
    client.note_studio = None
    return client


class TestAccessClientData:
    """Tests for GET /data-rights/access/{client_id} — Article 15."""

    @pytest.mark.asyncio
    async def test_access_success(self, mock_db, studio_id, user_id, sample_client):
        """Happy path: returns full client data."""
        with (
            patch("app.api.v1.data_rights.client_service") as mock_svc,
            patch("app.api.v1.data_rights.logger"),
        ):
            mock_svc.get_by_id = AsyncMock(return_value=sample_client)
            result = await access_client_data(client_id=1, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        assert result["gdpr_article"] == "Article 15 — Right of Access"
        assert result["client"]["id"] == 1
        assert result["client"]["nome"] == "Mario Rossi"
        assert result["client"]["codice_fiscale"] == "RSSMRA85M01H501Z"

    @pytest.mark.asyncio
    async def test_access_not_found(self, mock_db, studio_id, user_id):
        """Error case: client not found returns 404."""
        with patch("app.api.v1.data_rights.client_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await access_client_data(client_id=999, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_access_logs_audit(self, mock_db, studio_id, user_id, sample_client):
        """Audit trail: access action is logged."""
        with (
            patch("app.api.v1.data_rights.client_service") as mock_svc,
            patch("app.api.v1.data_rights.logger") as mock_logger,
        ):
            mock_svc.get_by_id = AsyncMock(return_value=sample_client)
            await access_client_data(client_id=1, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        mock_logger.info.assert_called_once()
        assert mock_logger.info.call_args[0][0] == "gdpr_access_right_exercised"


class TestExportClientData:
    """Tests for GET /data-rights/export/{client_id} — Article 20."""

    @pytest.mark.asyncio
    async def test_export_success(self, mock_db, studio_id, user_id):
        """Happy path: returns exported client data."""
        export_data = {"id": 1, "nome": "Mario Rossi", "email": "mario@example.com"}

        with (
            patch("app.api.v1.data_rights.client_export_service") as mock_svc,
            patch("app.api.v1.data_rights.logger"),
        ):
            mock_svc.export_client_by_id = AsyncMock(return_value=export_data)
            result = await export_client_data(client_id=1, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        assert result["gdpr_article"] == "Article 20 — Right to Data Portability"
        assert result["format"] == "application/json"
        assert result["data"] == export_data

    @pytest.mark.asyncio
    async def test_export_not_found(self, mock_db, studio_id, user_id):
        """Error case: client not found returns 404."""
        with patch("app.api.v1.data_rights.client_export_service") as mock_svc:
            mock_svc.export_client_by_id = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await export_client_data(client_id=999, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_export_logs_audit(self, mock_db, studio_id, user_id):
        """Audit trail: export action is logged."""
        export_data = {"id": 1, "nome": "Mario Rossi"}

        with (
            patch("app.api.v1.data_rights.client_export_service") as mock_svc,
            patch("app.api.v1.data_rights.logger") as mock_logger,
        ):
            mock_svc.export_client_by_id = AsyncMock(return_value=export_data)
            await export_client_data(client_id=1, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        mock_logger.info.assert_called_once()
        assert mock_logger.info.call_args[0][0] == "gdpr_portability_right_exercised"


class TestRectifyClientData:
    """Tests for PUT /data-rights/rectify/{client_id} — Article 16."""

    @pytest.mark.asyncio
    async def test_rectify_success(self, mock_db, studio_id, user_id, sample_client):
        """Happy path: updates client fields."""
        sample_client.nome = "Mario Rossi Corretto"

        with (
            patch("app.api.v1.data_rights.client_service") as mock_svc,
            patch("app.api.v1.data_rights.logger"),
        ):
            mock_svc.update = AsyncMock(return_value=sample_client)
            body = RectificationRequest(nome="Mario Rossi Corretto")
            result = await rectify_client_data(
                client_id=1, body=body, db=mock_db, x_studio_id=studio_id, x_user_id=user_id
            )

        assert result["gdpr_article"] == "Article 16 — Right to Rectification"
        assert result["rectified_fields"] == ["nome"]
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rectify_not_found(self, mock_db, studio_id, user_id):
        """Error case: client not found returns 404."""
        with patch("app.api.v1.data_rights.client_service") as mock_svc:
            mock_svc.update = AsyncMock(return_value=None)
            body = RectificationRequest(nome="Nuovo Nome")
            with pytest.raises(HTTPException) as exc_info:
                await rectify_client_data(
                    client_id=999, body=body, db=mock_db, x_studio_id=studio_id, x_user_id=user_id
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rectify_empty_fields_returns_400(self, mock_db, studio_id, user_id):
        """Edge case: no fields provided returns 400."""
        body = RectificationRequest()
        with pytest.raises(HTTPException) as exc_info:
            await rectify_client_data(client_id=1, body=body, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rectify_logs_audit(self, mock_db, studio_id, user_id, sample_client):
        """Audit trail: rectification action is logged."""
        with (
            patch("app.api.v1.data_rights.client_service") as mock_svc,
            patch("app.api.v1.data_rights.logger") as mock_logger,
        ):
            mock_svc.update = AsyncMock(return_value=sample_client)
            body = RectificationRequest(email="new@example.com")
            await rectify_client_data(client_id=1, body=body, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        mock_logger.info.assert_called_once()
        assert mock_logger.info.call_args[0][0] == "gdpr_rectification_right_exercised"


class TestEraseClientData:
    """Tests for DELETE /data-rights/erase/{client_id} — Article 17."""

    @pytest.mark.asyncio
    async def test_erase_success(self, mock_db, studio_id, user_id):
        """Happy path: triggers GDPR erasure and returns result."""
        deletion_result = MagicMock()
        deletion_result.client_id = 1
        deletion_result.export_data = {"id": 1, "nome": "Mario Rossi"}
        deletion_result.anonymized_at = datetime.now(UTC)
        deletion_result.communications_affected = 3

        with (
            patch("app.api.v1.data_rights.client_gdpr_service") as mock_svc,
            patch("app.api.v1.data_rights.logger"),
        ):
            mock_svc.delete_client_gdpr = AsyncMock(return_value=deletion_result)
            result = await erase_client_data(client_id=1, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        assert result["gdpr_article"] == "Article 17 — Right to Erasure"
        assert result["client_id"] == 1
        assert result["communications_affected"] == 3
        assert "anonymized_at" in result
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_erase_not_found(self, mock_db, studio_id, user_id):
        """Error case: client not found returns 404."""
        with patch("app.api.v1.data_rights.client_gdpr_service") as mock_svc:
            mock_svc.delete_client_gdpr = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await erase_client_data(client_id=999, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_erase_logs_audit(self, mock_db, studio_id, user_id):
        """Audit trail: erasure action is logged."""
        deletion_result = MagicMock()
        deletion_result.client_id = 1
        deletion_result.export_data = {"id": 1}
        deletion_result.anonymized_at = datetime.now(UTC)
        deletion_result.communications_affected = 0

        with (
            patch("app.api.v1.data_rights.client_gdpr_service") as mock_svc,
            patch("app.api.v1.data_rights.logger") as mock_logger,
        ):
            mock_svc.delete_client_gdpr = AsyncMock(return_value=deletion_result)
            await erase_client_data(client_id=1, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        mock_logger.info.assert_called_once()
        assert mock_logger.info.call_args[0][0] == "gdpr_erasure_right_exercised"

    @pytest.mark.asyncio
    async def test_erase_returns_export_data(self, mock_db, studio_id, user_id):
        """Edge case: erasure response includes pre-deletion export data."""
        deletion_result = MagicMock()
        deletion_result.client_id = 42
        deletion_result.export_data = {"id": 42, "nome": "Test", "email": "t@t.com"}
        deletion_result.anonymized_at = datetime.now(UTC)
        deletion_result.communications_affected = 5

        with (
            patch("app.api.v1.data_rights.client_gdpr_service") as mock_svc,
            patch("app.api.v1.data_rights.logger"),
        ):
            mock_svc.delete_client_gdpr = AsyncMock(return_value=deletion_result)
            result = await erase_client_data(client_id=42, db=mock_db, x_studio_id=studio_id, x_user_id=user_id)

        assert result["export_data"] == {"id": 42, "nome": "Test", "email": "t@t.com"}
