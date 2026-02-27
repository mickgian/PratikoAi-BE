"""Tests for Client API endpoints (DEV-312).

TDD: Tests written FIRST before implementation validation.
Tests all Client CRUD endpoints with mocked ClientService.

Endpoints tested:
- POST /clients
- GET /clients  (list with pagination / filtering)
- GET /clients/{client_id}
- PUT /clients/{client_id}
- DELETE /clients/{client_id}
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


@pytest.fixture
def studio_id() -> UUID:
    """Fixed studio UUID for tenant isolation tests."""
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
def sample_client_list(studio_id: UUID) -> list[MagicMock]:
    """Return a list of mock Client objects for pagination tests."""
    clients = []
    for i in range(3):
        c = MagicMock()
        c.id = i + 1
        c.studio_id = studio_id
        c.codice_fiscale = f"CF{i:014d}"
        c.nome = f"Cliente {i + 1}"
        c.tipo_cliente = TipoCliente.PERSONA_FISICA
        c.stato_cliente = StatoCliente.ATTIVO
        c.comune = "Milano"
        c.provincia = "MI"
        c.partita_iva = None
        c.email = None
        c.phone = None
        c.indirizzo = None
        c.cap = None
        c.note_studio = None
        c.created_at = datetime.now(UTC)
        clients.append(c)
    return clients


# ---------------------------------------------------------------------------
# POST /clients — Create
# ---------------------------------------------------------------------------


class TestCreateClient:
    """Tests for POST /clients endpoint."""

    @pytest.mark.asyncio
    async def test_create_client_success(self, mock_db: AsyncMock, studio_id: UUID, sample_client: MagicMock) -> None:
        """Happy path: creates a client and returns 201."""
        from app.api.v1.clients import create_client
        from app.schemas.client import ClientCreate

        body = ClientCreate(
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.create = AsyncMock(return_value=sample_client)
            result = await create_client(body=body, studio_id=studio_id, db=mock_db)

        assert result.id == 1
        assert result.nome == "Mario Rossi"
        assert result.codice_fiscale == "RSSMRA85M01H501Z"
        mock_svc.create.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_client_limit_exceeded_returns_400(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: 100-client limit exceeded raises 400."""
        from app.api.v1.clients import create_client
        from app.schemas.client import ClientCreate

        body = ClientCreate(
            codice_fiscale="BNCLRA90A01F205X",
            nome="Laura Bianchi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Milano",
            provincia="MI",
        )

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.create = AsyncMock(side_effect=ValueError("Lo studio ha raggiunto il limite di 100 clienti."))
            with pytest.raises(HTTPException) as exc_info:
                await create_client(body=body, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "limite" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_client_duplicate_cf_returns_400(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: duplicate codice_fiscale raises 400."""
        from app.api.v1.clients import create_client
        from app.schemas.client import ClientCreate

        body = ClientCreate(
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi Duplicato",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.create = AsyncMock(side_effect=ValueError("Il codice fiscale e' gia' presente nello studio."))
            with pytest.raises(HTTPException) as exc_info:
                await create_client(body=body, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "codice fiscale" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_client_with_all_optional_fields(
        self, mock_db: AsyncMock, studio_id: UUID, sample_client: MagicMock
    ) -> None:
        """Edge case: all optional fields populated."""
        from app.api.v1.clients import create_client
        from app.schemas.client import ClientCreate

        body = ClientCreate(
            codice_fiscale="VRDLGI75T15L219P",
            nome="Luigi Verdi",
            tipo_cliente=TipoCliente.DITTA_INDIVIDUALE,
            comune="Napoli",
            provincia="NA",
            partita_iva="01234567890",
            email="luigi@example.com",
            phone="+39 081 1234567",
            indirizzo="Via Napoli 42",
            cap="80100",
            stato_cliente=StatoCliente.PROSPECT,
            note_studio="Nuovo cliente in fase di onboarding",
        )

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.create = AsyncMock(return_value=sample_client)
            result = await create_client(body=body, studio_id=studio_id, db=mock_db)

        mock_svc.create.assert_awaited_once()
        call_kwargs = mock_svc.create.call_args.kwargs
        assert call_kwargs["partita_iva"] == "01234567890"
        assert call_kwargs["stato_cliente"] == StatoCliente.PROSPECT


# ---------------------------------------------------------------------------
# GET /clients — List with pagination
# ---------------------------------------------------------------------------


class TestListClients:
    """Tests for GET /clients endpoint."""

    @pytest.mark.asyncio
    async def test_list_clients_success(
        self, mock_db: AsyncMock, studio_id: UUID, sample_client_list: list[MagicMock]
    ) -> None:
        """Happy path: returns paginated list of clients."""
        from app.api.v1.clients import list_clients

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.list = AsyncMock(return_value=(sample_client_list, 3))
            result = await list_clients(studio_id=studio_id, offset=0, limit=50, stato=None, db=mock_db)

        assert result.total == 3
        assert len(result.items) == 3
        assert result.offset == 0
        assert result.limit == 50

    @pytest.mark.asyncio
    async def test_list_clients_with_stato_filter(
        self, mock_db: AsyncMock, studio_id: UUID, sample_client_list: list[MagicMock]
    ) -> None:
        """Happy path: filter by stato_cliente."""
        from app.api.v1.clients import list_clients

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.list = AsyncMock(return_value=(sample_client_list[:1], 1))
            result = await list_clients(
                studio_id=studio_id,
                offset=0,
                limit=50,
                stato=StatoCliente.ATTIVO,
                db=mock_db,
            )

        assert result.total == 1
        mock_svc.list.assert_awaited_once_with(
            mock_db,
            studio_id=studio_id,
            offset=0,
            limit=50,
            stato=StatoCliente.ATTIVO,
        )

    @pytest.mark.asyncio
    async def test_list_clients_empty_result(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Edge case: no clients returns empty list with total=0."""
        from app.api.v1.clients import list_clients

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.list = AsyncMock(return_value=([], 0))
            result = await list_clients(studio_id=studio_id, offset=0, limit=50, stato=None, db=mock_db)

        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_list_clients_custom_pagination(
        self, mock_db: AsyncMock, studio_id: UUID, sample_client_list: list[MagicMock]
    ) -> None:
        """Edge case: custom offset and limit values."""
        from app.api.v1.clients import list_clients

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.list = AsyncMock(return_value=(sample_client_list[1:2], 3))
            result = await list_clients(studio_id=studio_id, offset=1, limit=1, stato=None, db=mock_db)

        assert result.offset == 1
        assert result.limit == 1
        assert result.total == 3
        assert len(result.items) == 1


# ---------------------------------------------------------------------------
# GET /clients/{client_id} — Read by ID
# ---------------------------------------------------------------------------


class TestGetClient:
    """Tests for GET /clients/{client_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_client_success(self, mock_db: AsyncMock, studio_id: UUID, sample_client: MagicMock) -> None:
        """Happy path: returns client when found."""
        from app.api.v1.clients import get_client

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=sample_client)
            result = await get_client(client_id=1, studio_id=studio_id, db=mock_db)

        assert result.id == 1
        assert result.nome == "Mario Rossi"
        mock_svc.get_by_id.assert_awaited_once_with(mock_db, client_id=1, studio_id=studio_id)

    @pytest.mark.asyncio
    async def test_get_client_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: nonexistent client raises 404."""
        from app.api.v1.clients import get_client

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await get_client(client_id=999, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_client_enforces_tenant_isolation(self, mock_db: AsyncMock, sample_client: MagicMock) -> None:
        """Edge case: client from a different studio is not returned."""
        from app.api.v1.clients import get_client

        different_studio = uuid4()

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await get_client(client_id=1, studio_id=different_studio, db=mock_db)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# PUT /clients/{client_id} — Update
# ---------------------------------------------------------------------------


class TestUpdateClient:
    """Tests for PUT /clients/{client_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_client_success(self, mock_db: AsyncMock, studio_id: UUID, sample_client: MagicMock) -> None:
        """Happy path: update client fields."""
        from app.api.v1.clients import update_client
        from app.schemas.client import ClientUpdate

        sample_client.nome = "Mario Rossi Aggiornato"
        body = ClientUpdate(nome="Mario Rossi Aggiornato")

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.update = AsyncMock(return_value=sample_client)
            result = await update_client(client_id=1, body=body, studio_id=studio_id, db=mock_db)

        assert result.nome == "Mario Rossi Aggiornato"
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_client_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: update on nonexistent client raises 404."""
        from app.api.v1.clients import update_client
        from app.schemas.client import ClientUpdate

        body = ClientUpdate(nome="Nuovo Nome")

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.update = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await update_client(client_id=999, body=body, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_client_change_stato(
        self, mock_db: AsyncMock, studio_id: UUID, sample_client: MagicMock
    ) -> None:
        """Edge case: change client stato from ATTIVO to SOSPESO."""
        from app.api.v1.clients import update_client
        from app.schemas.client import ClientUpdate

        sample_client.stato_cliente = StatoCliente.SOSPESO
        body = ClientUpdate(stato_cliente=StatoCliente.SOSPESO)

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.update = AsyncMock(return_value=sample_client)
            result = await update_client(client_id=1, body=body, studio_id=studio_id, db=mock_db)

        assert result.stato_cliente == StatoCliente.SOSPESO


# ---------------------------------------------------------------------------
# DELETE /clients/{client_id} — Soft delete
# ---------------------------------------------------------------------------


class TestDeleteClient:
    """Tests for DELETE /clients/{client_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_client_success(self, mock_db: AsyncMock, studio_id: UUID, sample_client: MagicMock) -> None:
        """Happy path: soft-delete returns 204 (None)."""
        from app.api.v1.clients import delete_client

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.soft_delete = AsyncMock(return_value=sample_client)
            result = await delete_client(client_id=1, studio_id=studio_id, db=mock_db)

        assert result is None
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_client_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: soft-delete nonexistent client raises 404."""
        from app.api.v1.clients import delete_client

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.soft_delete = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await delete_client(client_id=999, studio_id=studio_id, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_delete_client_commits_transaction(
        self, mock_db: AsyncMock, studio_id: UUID, sample_client: MagicMock
    ) -> None:
        """Edge case: verify db.commit() is called after successful deletion."""
        from app.api.v1.clients import delete_client

        with patch("app.api.v1.clients.client_service") as mock_svc:
            mock_svc.soft_delete = AsyncMock(return_value=sample_client)
            await delete_client(client_id=1, studio_id=studio_id, db=mock_db)

        mock_db.commit.assert_awaited_once()
