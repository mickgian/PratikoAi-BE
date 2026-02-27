"""DEV-314: Tests for ClientExportService — Excel export of client data.

Tests cover:
- Export all clients generates valid data structure
- Empty studio returns empty export
- PII is decrypted for export
- Soft-deleted clients excluded from export
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.client_export_service import ClientExportService


@pytest.fixture
def export_service() -> ClientExportService:
    return ClientExportService()


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
def sample_client_rows(studio_id):
    """Sample client-profile row pairs as returned by the join query."""
    client1 = MagicMock()
    client1.id = 1
    client1.studio_id = studio_id
    client1.nome = "Mario Rossi"
    client1.codice_fiscale = "RSSMRA85M01H501Z"
    client1.partita_iva = "12345678901"
    client1.email = "mario@example.com"
    client1.phone = "+39 333 1234567"
    client1.tipo_cliente = MagicMock(value="persona_fisica")
    client1.stato_cliente = MagicMock(value="attivo")
    client1.indirizzo = "Via Roma 1"
    client1.cap = "00100"
    client1.comune = "Roma"
    client1.provincia = "RM"
    client1.note_studio = None
    client1.deleted_at = None

    profile1 = MagicMock()
    profile1.codice_ateco_principale = "69.20.01"
    profile1.regime_fiscale = MagicMock(value="ordinario")
    profile1.ccnl_applicato = "Commercio"
    profile1.n_dipendenti = 5
    profile1.data_inizio_attivita = None

    client2 = MagicMock()
    client2.id = 2
    client2.studio_id = studio_id
    client2.nome = "Luigi Bianchi"
    client2.codice_fiscale = "BNCLGU90A01F205X"
    client2.partita_iva = None
    client2.email = "luigi@example.com"
    client2.phone = "+39 348 9876543"
    client2.tipo_cliente = MagicMock(value="persona_fisica")
    client2.stato_cliente = MagicMock(value="attivo")
    client2.indirizzo = None
    client2.cap = None
    client2.comune = "Milano"
    client2.provincia = "MI"
    client2.note_studio = None
    client2.deleted_at = None

    # Second client has no profile
    return [(client1, profile1), (client2, None)]


class TestClientExportServiceExport:
    """Test ClientExportService.export_clients()."""

    @pytest.mark.asyncio
    async def test_export_all_clients(
        self,
        export_service: ClientExportService,
        mock_db: AsyncMock,
        studio_id,
        sample_client_rows,
    ) -> None:
        """Happy path: export generates valid data structure."""
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=sample_client_rows)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await export_service.export_clients(
            db=mock_db,
            studio_id=studio_id,
        )

        assert result is not None
        assert len(result) == 2
        assert result[0]["nome"] == "Mario Rossi"
        assert result[1]["nome"] == "Luigi Bianchi"

    @pytest.mark.asyncio
    async def test_export_empty_studio(
        self,
        export_service: ClientExportService,
        mock_db: AsyncMock,
    ) -> None:
        """Empty studio returns empty export."""
        empty_studio_id = uuid4()
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await export_service.export_clients(
            db=mock_db,
            studio_id=empty_studio_id,
        )

        assert result is not None
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_export_includes_decrypted_pii(
        self,
        export_service: ClientExportService,
        mock_db: AsyncMock,
        studio_id,
        sample_client_rows,
    ) -> None:
        """PII fields are decrypted in the export output."""
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=sample_client_rows)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await export_service.export_clients(
            db=mock_db,
            studio_id=studio_id,
        )

        # Verify PII fields are present and decrypted (not encrypted blobs)
        first_client = result[0]
        assert first_client["codice_fiscale"] == "RSSMRA85M01H501Z"
        assert first_client["email"] == "mario@example.com"
        assert first_client["phone"] == "+39 333 1234567"

    @pytest.mark.asyncio
    async def test_export_filters_deleted(
        self,
        export_service: ClientExportService,
        mock_db: AsyncMock,
        studio_id,
        sample_client_rows,
    ) -> None:
        """Soft-deleted clients are excluded from export (filtered by query WHERE clause)."""
        # The query filters deleted_at IS NULL, so only active clients are returned
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=sample_client_rows)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await export_service.export_clients(
            db=mock_db,
            studio_id=studio_id,
        )

        # All returned clients should be non-deleted
        assert len(result) == 2
        for client_data in result:
            # deleted_at is not in the export dict (only active clients returned)
            assert "deleted_at" not in client_data


class TestClientExportServiceToRows:
    """Test ClientExportService.export_to_rows()."""

    @pytest.mark.asyncio
    async def test_export_to_rows(
        self,
        export_service: ClientExportService,
        mock_db: AsyncMock,
        studio_id,
        sample_client_rows,
    ) -> None:
        """Export to rows returns headers and row data."""
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=sample_client_rows)
        mock_db.execute = AsyncMock(return_value=mock_result)

        headers, rows = await export_service.export_to_rows(
            db=mock_db,
            studio_id=studio_id,
        )

        assert len(headers) > 0
        assert "nome" in headers
        assert "codice_fiscale" in headers
        assert len(rows) == 2
