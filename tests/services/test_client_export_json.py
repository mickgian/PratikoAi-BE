"""DEV-420: Tests for GDPR JSON Export.

Tests: JSON structure, all fields present, valid JSON schema.
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


class TestExportToJson:
    @pytest.mark.asyncio
    async def test_json_structure(self, svc, mock_db):
        mock_client = MagicMock()
        mock_client.id = 1
        mock_client.codice_fiscale = "RSSMRA80A01H501Z"
        mock_client.nome = "Mario Rossi"
        mock_client.tipo_cliente = MagicMock(value="persona_fisica")
        mock_client.stato_cliente = MagicMock(value="attivo")
        mock_client.partita_iva = None
        mock_client.email = "mario@test.com"
        mock_client.phone = "+39 123 456"
        mock_client.indirizzo = "Via Roma 1"
        mock_client.cap = "00100"
        mock_client.comune = "Roma"
        mock_client.provincia = "RM"
        mock_client.note_studio = None
        mock_client.deleted_at = None

        mock_result = MagicMock()
        mock_result.all.return_value = [(mock_client, None)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_clients(mock_db, studio_id=uuid.uuid4())
        assert len(data) == 1

        # Validate JSON-serializable
        json_str = json.dumps(data, default=str)
        parsed = json.loads(json_str)
        assert parsed[0]["codice_fiscale"] == "RSSMRA80A01H501Z"
        assert parsed[0]["nome"] == "Mario Rossi"

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

    @pytest.mark.asyncio
    async def test_empty_export(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await svc.export_to_json(mock_db, studio_id=uuid.uuid4())
        parsed = json.loads(data)
        assert parsed["clients"] == []
