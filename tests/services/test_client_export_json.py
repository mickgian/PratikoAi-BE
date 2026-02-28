"""DEV-420: Tests for GDPR JSON Export and Client Export Service.

Tests: JSON structure, export_to_json, export_client_by_id, export_to_rows, edge cases.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.client_export_service import ClientExportService


@pytest.fixture
def svc():
    return ClientExportService()


@pytest.fixture
def mock_db():
    return AsyncMock()


def _make_mock_client(**overrides):
    """Create a mock client with sensible defaults."""
    mock_client = MagicMock()
    mock_client.id = overrides.get("id", 1)
    mock_client.codice_fiscale = overrides.get("codice_fiscale", "RSSMRA80A01H501Z")
    mock_client.nome = overrides.get("nome", "Mario Rossi")
    mock_client.tipo_cliente = MagicMock(value="persona_fisica")
    mock_client.stato_cliente = MagicMock(value="attivo")
    mock_client.partita_iva = overrides.get("partita_iva")
    mock_client.email = overrides.get("email", "mario@test.com")
    mock_client.phone = overrides.get("phone", "+39 123 456")
    mock_client.indirizzo = "Via Roma 1"
    mock_client.cap = "00100"
    mock_client.comune = "Roma"
    mock_client.provincia = "RM"
    mock_client.note_studio = None
    mock_client.deleted_at = None
    return mock_client


def _make_mock_profile(**overrides):
    """Create a mock client profile."""
    profile = MagicMock()
    profile.codice_ateco_principale = overrides.get("codice_ateco", "62.01")
    profile.regime_fiscale = MagicMock(value="ordinario")
    profile.ccnl_applicato = overrides.get("ccnl", "commercio")
    profile.n_dipendenti = overrides.get("n_dipendenti", 5)
    profile.data_inizio_attivita = None
    return profile


class TestExportClients:
    @pytest.mark.asyncio
    async def test_export_single_client_no_profile(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = [(_make_mock_client(), None)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_clients(mock_db, studio_id=uuid.uuid4())
        assert len(data) == 1
        assert data[0]["codice_fiscale"] == "RSSMRA80A01H501Z"
        assert "codice_ateco_principale" not in data[0]

    @pytest.mark.asyncio
    async def test_export_client_with_profile(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = [(_make_mock_client(), _make_mock_profile())]
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_clients(mock_db, studio_id=uuid.uuid4())
        assert len(data) == 1
        assert data[0]["codice_ateco_principale"] == "62.01"
        assert data[0]["regime_fiscale"] == "ordinario"
        assert data[0]["n_dipendenti"] == 5

    @pytest.mark.asyncio
    async def test_export_empty(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_clients(mock_db, studio_id=uuid.uuid4())
        assert data == []

    @pytest.mark.asyncio
    async def test_json_serializable(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = [(_make_mock_client(), None)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_clients(mock_db, studio_id=uuid.uuid4())
        json_str = json.dumps(data, default=str)
        parsed = json.loads(json_str)
        assert parsed[0]["nome"] == "Mario Rossi"


class TestExportClientById:
    @pytest.mark.asyncio
    async def test_export_existing_client(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (_make_mock_client(id=42), None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_client_by_id(mock_db, studio_id=uuid.uuid4(), client_id=42)
        assert data is not None
        assert data["id"] == 42

    @pytest.mark.asyncio
    async def test_export_client_not_found(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_client_by_id(mock_db, studio_id=uuid.uuid4(), client_id=999)
        assert data is None

    @pytest.mark.asyncio
    async def test_export_client_with_profile(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (
            _make_mock_client(id=10),
            _make_mock_profile(codice_ateco="69.20"),
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_client_by_id(mock_db, studio_id=uuid.uuid4(), client_id=10)
        assert data is not None
        assert data["codice_ateco_principale"] == "69.20"


class TestExportToRows:
    @pytest.mark.asyncio
    async def test_export_to_rows(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = [(_make_mock_client(), None)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        headers, rows = await svc.export_to_rows(mock_db, studio_id=uuid.uuid4())
        assert len(headers) > 0
        assert len(rows) == 1
        assert "codice_fiscale" in headers

    @pytest.mark.asyncio
    async def test_export_to_rows_empty(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        headers, rows = await svc.export_to_rows(mock_db, studio_id=uuid.uuid4())
        assert headers == []
        assert rows == []


class TestExportToJson:
    @pytest.mark.asyncio
    async def test_export_to_json_format(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_to_json(mock_db, studio_id=uuid.uuid4())
        assert isinstance(data, str)
        parsed = json.loads(data)
        assert isinstance(parsed, dict)
        assert "clients" in parsed
        assert "export_date" in parsed
        assert "studio_id" in parsed
        assert "format_version" in parsed

    @pytest.mark.asyncio
    async def test_empty_export(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_to_json(mock_db, studio_id=uuid.uuid4())
        parsed = json.loads(data)
        assert parsed["clients"] == []

    @pytest.mark.asyncio
    async def test_export_to_json_with_data(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = [(_make_mock_client(), _make_mock_profile())]
        mock_db.execute = AsyncMock(return_value=mock_result)

        sid = uuid.uuid4()
        data = await svc.export_to_json(mock_db, studio_id=sid)
        parsed = json.loads(data)
        assert len(parsed["clients"]) == 1
        assert parsed["studio_id"] == str(sid)
        assert parsed["clients"][0]["codice_fiscale"] == "RSSMRA80A01H501Z"
