"""DEV-301: Tests for Client SQLModel."""

import sys
from datetime import date, datetime
from types import ModuleType
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Mock the database service to avoid needing a live PostgreSQL connection
# during test collection.  ``app.services.__init__`` eagerly imports
# ``database_service`` which calls ``create_engine`` on import.
if "app.services.database" not in sys.modules:
    _db_stub = ModuleType("app.services.database")
    _db_stub.database_service = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.database"] = _db_stub

from app.models.client import Client, StatoCliente, TipoCliente


class TestClientCreation:
    """Test Client model creation and field defaults."""

    def test_client_creation_valid(self) -> None:
        """Valid client with all required fields."""
        studio_id = uuid4()
        client = Client(
            studio_id=studio_id,
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )

        assert client.studio_id == studio_id
        assert client.codice_fiscale == "RSSMRA85M01H501Z"
        assert client.nome == "Mario Rossi"
        assert client.tipo_cliente == TipoCliente.PERSONA_FISICA

    def test_client_tipo_cliente_enum_values(self) -> None:
        """All TipoCliente enum values are valid."""
        assert TipoCliente.PERSONA_FISICA == "persona_fisica"
        assert TipoCliente.DITTA_INDIVIDUALE == "ditta_individuale"
        assert TipoCliente.SOCIETA == "societa"
        assert TipoCliente.ENTE == "ente"

    def test_client_stato_cliente_enum_values(self) -> None:
        """All StatoCliente enum values are valid."""
        assert StatoCliente.ATTIVO == "attivo"
        assert StatoCliente.PROSPECT == "prospect"
        assert StatoCliente.CESSATO == "cessato"
        assert StatoCliente.SOSPESO == "sospeso"

    def test_client_stato_default_attivo(self) -> None:
        """stato_cliente defaults to ATTIVO."""
        client = Client(
            studio_id=uuid4(),
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )
        assert client.stato_cliente == StatoCliente.ATTIVO

    def test_client_optional_fields(self) -> None:
        """Optional fields default to None."""
        client = Client(
            studio_id=uuid4(),
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )
        assert client.partita_iva is None
        assert client.email is None
        assert client.phone is None
        assert client.indirizzo is None
        assert client.cap is None
        assert client.data_nascita_titolare is None
        assert client.note_studio is None
        assert client.deleted_at is None

    def test_client_with_partita_iva(self) -> None:
        """Client with P.IVA."""
        client = Client(
            studio_id=uuid4(),
            codice_fiscale="RSSMRA85M01H501Z",
            partita_iva="12345678901",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.DITTA_INDIVIDUALE,
            comune="Milano",
            provincia="MI",
        )
        assert client.partita_iva == "12345678901"

    def test_client_with_contact_info(self) -> None:
        """Client with email and phone (encrypted fields)."""
        client = Client(
            studio_id=uuid4(),
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            email="mario@example.com",
            phone="+39 333 1234567",
            comune="Roma",
            provincia="RM",
        )
        assert client.email == "mario@example.com"
        assert client.phone == "+39 333 1234567"

    def test_client_soft_delete(self) -> None:
        """Soft delete sets deleted_at."""
        client = Client(
            studio_id=uuid4(),
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )
        assert client.deleted_at is None
        assert client.is_deleted is False

        now = datetime.utcnow()
        client.deleted_at = now
        assert client.is_deleted is True
        assert client.deleted_at == now

    def test_client_studio_fk(self) -> None:
        """studio_id is set and refers to a studio UUID."""
        studio_id = uuid4()
        client = Client(
            studio_id=studio_id,
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )
        assert client.studio_id == studio_id

    def test_client_with_full_address(self) -> None:
        """Client with complete address information."""
        client = Client(
            studio_id=uuid4(),
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            indirizzo="Via Roma 1",
            cap="00100",
            comune="Roma",
            provincia="RM",
        )
        assert client.indirizzo == "Via Roma 1"
        assert client.cap == "00100"
        assert client.comune == "Roma"
        assert client.provincia == "RM"

    def test_client_data_nascita(self) -> None:
        """Client with date of birth."""
        client = Client(
            studio_id=uuid4(),
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
            data_nascita_titolare=date(1985, 8, 1),
        )
        assert client.data_nascita_titolare == date(1985, 8, 1)

    def test_client_repr(self) -> None:
        """__repr__ includes nome and tipo."""
        client = Client(
            studio_id=uuid4(),
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )
        r = repr(client)
        assert "Mario Rossi" in r
        assert "persona_fisica" in r
