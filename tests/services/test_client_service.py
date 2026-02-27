"""DEV-309: Tests for ClientService CRUD operations."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.client import Client, StatoCliente, TipoCliente
from app.services.client_service import ClientService


@pytest.fixture
def client_service() -> ClientService:
    return ClientService()


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
        comune="Roma",
        provincia="RM",
    )


class TestClientServiceCreate:
    """Test ClientService.create()."""

    @pytest.mark.asyncio
    async def test_create_client_success(self, client_service: ClientService, mock_db: AsyncMock, studio_id) -> None:
        """Happy path: create client with valid data."""
        # Mock count check (under limit)
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=5)
        # Mock duplicate CF check
        dup_result = MagicMock()
        dup_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(side_effect=[count_result, dup_result])

        result = await client_service.create(
            db=mock_db,
            studio_id=studio_id,
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )

        assert result.nome == "Mario Rossi"
        assert result.studio_id == studio_id
        assert result.stato_cliente == StatoCliente.ATTIVO
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_client_exceeds_limit(
        self, client_service: ClientService, mock_db: AsyncMock, studio_id
    ) -> None:
        """Error: studio has reached max clients (100)."""
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=100)
        mock_db.execute = AsyncMock(return_value=count_result)

        with pytest.raises(ValueError, match="limite.*100"):
            await client_service.create(
                db=mock_db,
                studio_id=studio_id,
                codice_fiscale="RSSMRA85M01H501Z",
                nome="Mario Rossi",
                tipo_cliente=TipoCliente.PERSONA_FISICA,
                comune="Roma",
                provincia="RM",
            )

    @pytest.mark.asyncio
    async def test_create_client_duplicate_cf(
        self, client_service: ClientService, mock_db: AsyncMock, studio_id
    ) -> None:
        """Error: duplicate codice_fiscale within same studio."""
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=5)
        existing = Client(
            id=99,
            studio_id=studio_id,
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Already Here",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
        )
        dup_result = MagicMock()
        dup_result.scalar_one_or_none = MagicMock(return_value=existing)
        mock_db.execute = AsyncMock(side_effect=[count_result, dup_result])

        with pytest.raises(ValueError, match="codice fiscale.*già presente"):
            await client_service.create(
                db=mock_db,
                studio_id=studio_id,
                codice_fiscale="RSSMRA85M01H501Z",
                nome="Duplicate",
                tipo_cliente=TipoCliente.PERSONA_FISICA,
                comune="Roma",
                provincia="RM",
            )


class TestClientServiceGetById:
    """Test ClientService.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        client_service: ClientService,
        mock_db: AsyncMock,
        sample_client: Client,
        studio_id,
    ) -> None:
        """Happy path: retrieve active client."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_client)))

        result = await client_service.get_by_id(db=mock_db, client_id=1, studio_id=studio_id)

        assert result is not None
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, client_service: ClientService, mock_db: AsyncMock, studio_id) -> None:
        """Error: non-existent client returns None."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await client_service.get_by_id(db=mock_db, client_id=999, studio_id=studio_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_wrong_studio(
        self,
        client_service: ClientService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: client exists but different studio returns None (tenant isolation)."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await client_service.get_by_id(db=mock_db, client_id=1, studio_id=uuid4())

        assert result is None


class TestClientServiceList:
    """Test ClientService.list()."""

    @pytest.mark.asyncio
    async def test_list_clients(
        self,
        client_service: ClientService,
        mock_db: AsyncMock,
        studio_id,
        sample_client: Client,
    ) -> None:
        """Happy path: list clients for a studio."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_client])))
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=1)
        mock_db.execute = AsyncMock(side_effect=[count_result, mock_result])

        clients, total = await client_service.list(db=mock_db, studio_id=studio_id)

        assert total == 1
        assert len(clients) == 1


class TestClientServiceSoftDelete:
    """Test ClientService.soft_delete()."""

    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self,
        client_service: ClientService,
        mock_db: AsyncMock,
        sample_client: Client,
        studio_id,
    ) -> None:
        """Happy path: soft delete sets deleted_at."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_client)))

        result = await client_service.soft_delete(db=mock_db, client_id=1, studio_id=studio_id)

        assert result is not None
        assert result.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_not_found(self, client_service: ClientService, mock_db: AsyncMock, studio_id) -> None:
        """Error: soft delete non-existent client returns None."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await client_service.soft_delete(db=mock_db, client_id=999, studio_id=studio_id)

        assert result is None
