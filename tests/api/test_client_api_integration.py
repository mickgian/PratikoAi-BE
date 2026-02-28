"""DEV-319: Client API Integration Test Suite.

Tests client CRUD endpoints: create, list, get, update, delete.
Verifies status codes, response shapes, error handling, pagination,
and tenant isolation at the API layer.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STUDIO_ID = uuid4()


def _make_mock_client(**kwargs: object) -> MagicMock:
    """Create a MagicMock that behaves like a Client ORM instance."""
    from datetime import UTC, datetime

    defaults = {
        "id": 1,
        "studio_id": STUDIO_ID,
        "codice_fiscale": "RSSMRA85M01H501Z",
        "nome": "Mario Rossi",
        "tipo_cliente": "persona_fisica",
        "stato_cliente": "attivo",
        "comune": "Roma",
        "provincia": "RM",
        "partita_iva": None,
        "email": "mario@test.it",
        "phone": None,
        "indirizzo": None,
        "cap": None,
        "note_studio": None,
        "deleted_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": None,
    }
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


# ---------------------------------------------------------------------------
# Create client (POST)
# ---------------------------------------------------------------------------


class TestCreateClientEndpoint:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_success(self) -> None:
        mock_client = _make_mock_client()

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.create = AsyncMock(return_value=mock_client)

            from app.api.v1.clients import create_client
            from app.schemas.client import ClientCreate

            body = ClientCreate(
                codice_fiscale="RSSMRA85M01H501Z",
                nome="Mario Rossi",
                tipo_cliente="persona_fisica",
                comune="Roma",
                provincia="RM",
            )
            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()

            result = await create_client(body=body, studio_id=STUDIO_ID, db=mock_db)

        assert result.id == 1
        assert result.nome == "Mario Rossi"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_duplicate_cf_returns_400(self) -> None:
        from fastapi import HTTPException

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.create = AsyncMock(side_effect=ValueError("Il codice fiscale è già presente nello studio."))

            from app.api.v1.clients import create_client
            from app.schemas.client import ClientCreate

            body = ClientCreate(
                codice_fiscale="RSSMRA85M01H501Z",
                nome="Mario Rossi",
                tipo_cliente="persona_fisica",
                comune="Roma",
                provincia="RM",
            )
            mock_db = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await create_client(body=body, studio_id=STUDIO_ID, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "codice fiscale" in str(exc_info.value.detail)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_limit_exceeded_returns_400(self) -> None:
        from fastapi import HTTPException

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.create = AsyncMock(side_effect=ValueError("limite di 100 clienti"))

            from app.api.v1.clients import create_client
            from app.schemas.client import ClientCreate

            body = ClientCreate(
                codice_fiscale="RSSMRA85M01H501Z",
                nome="Test",
                tipo_cliente="persona_fisica",
                comune="Roma",
                provincia="RM",
            )
            mock_db = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await create_client(body=body, studio_id=STUDIO_ID, db=mock_db)

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# List clients (GET)
# ---------------------------------------------------------------------------


class TestListClientsEndpoint:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_returns_paginated_results(self) -> None:
        mock_clients = [
            _make_mock_client(id=1, nome="Client 1"),
            _make_mock_client(id=2, nome="Client 2"),
        ]

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.list = AsyncMock(return_value=(mock_clients, 2))

            from app.api.v1.clients import list_clients

            mock_db = AsyncMock()
            result = await list_clients(studio_id=STUDIO_ID, offset=0, limit=50, stato=None, db=mock_db)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.offset == 0
        assert result.limit == 50

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_empty_studio(self) -> None:
        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.list = AsyncMock(return_value=([], 0))

            from app.api.v1.clients import list_clients

            mock_db = AsyncMock()
            result = await list_clients(studio_id=STUDIO_ID, offset=0, limit=50, stato=None, db=mock_db)

        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_with_stato_filter(self) -> None:
        mock_client = _make_mock_client(stato_cliente="prospect")

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.list = AsyncMock(return_value=([mock_client], 1))

            from app.api.v1.clients import list_clients

            mock_db = AsyncMock()
            result = await list_clients(studio_id=STUDIO_ID, offset=0, limit=50, stato="prospect", db=mock_db)

        assert result.total == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_pagination_offset(self) -> None:
        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.list = AsyncMock(return_value=([], 100))

            from app.api.v1.clients import list_clients

            mock_db = AsyncMock()
            result = await list_clients(studio_id=STUDIO_ID, offset=90, limit=10, stato=None, db=mock_db)

        assert result.offset == 90
        assert result.limit == 10
        assert result.total == 100


# ---------------------------------------------------------------------------
# Get client (GET /{id})
# ---------------------------------------------------------------------------


class TestGetClientEndpoint:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_returns_client(self) -> None:
        mock_client = _make_mock_client()

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.get_by_id = AsyncMock(return_value=mock_client)

            from app.api.v1.clients import get_client

            mock_db = AsyncMock()
            result = await get_client(client_id=1, studio_id=STUDIO_ID, db=mock_db)

        assert result.id == 1
        assert result.nome == "Mario Rossi"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_not_found_returns_404(self) -> None:
        from fastapi import HTTPException

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.get_by_id = AsyncMock(return_value=None)

            from app.api.v1.clients import get_client

            mock_db = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await get_client(client_id=999, studio_id=STUDIO_ID, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_wrong_studio_returns_404(self) -> None:
        """Client exists in Studio A but request is for Studio B."""
        from fastapi import HTTPException

        other_studio = uuid4()

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.get_by_id = AsyncMock(return_value=None)

            from app.api.v1.clients import get_client

            mock_db = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await get_client(client_id=1, studio_id=other_studio, db=mock_db)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Update client (PUT /{id})
# ---------------------------------------------------------------------------


class TestUpdateClientEndpoint:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_success(self) -> None:
        mock_client = _make_mock_client(nome="Mario Rossi Updated")

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.update = AsyncMock(return_value=mock_client)

            from app.api.v1.clients import update_client
            from app.schemas.client import ClientUpdate

            body = ClientUpdate(nome="Mario Rossi Updated")
            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()

            result = await update_client(client_id=1, body=body, studio_id=STUDIO_ID, db=mock_db)

        assert result.nome == "Mario Rossi Updated"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_not_found_returns_404(self) -> None:
        from fastapi import HTTPException

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.update = AsyncMock(return_value=None)

            from app.api.v1.clients import update_client
            from app.schemas.client import ClientUpdate

            body = ClientUpdate(nome="Test")
            mock_db = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await update_client(client_id=999, body=body, studio_id=STUDIO_ID, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_partial_fields(self) -> None:
        mock_client = _make_mock_client(email="new@email.it")

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.update = AsyncMock(return_value=mock_client)

            from app.api.v1.clients import update_client
            from app.schemas.client import ClientUpdate

            body = ClientUpdate(email="new@email.it")
            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()

            result = await update_client(client_id=1, body=body, studio_id=STUDIO_ID, db=mock_db)

        assert result.email == "new@email.it"


# ---------------------------------------------------------------------------
# Delete client (DELETE /{id})
# ---------------------------------------------------------------------------


class TestDeleteClientEndpoint:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_delete_success(self) -> None:
        mock_client = _make_mock_client()

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.soft_delete = AsyncMock(return_value=mock_client)

            from app.api.v1.clients import delete_client

            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()

            result = await delete_client(client_id=1, studio_id=STUDIO_ID, db=mock_db)

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_delete_not_found_returns_404(self) -> None:
        from fastapi import HTTPException

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.soft_delete = AsyncMock(return_value=None)

            from app.api.v1.clients import delete_client

            mock_db = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await delete_client(client_id=1, studio_id=STUDIO_ID, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio(loop_scope="function")
    async def test_delete_wrong_studio_returns_404(self) -> None:
        """Attempting to delete from wrong studio should return 404."""
        from fastapi import HTTPException

        other_studio = uuid4()

        with (
            patch("app.api.v1.clients.client_service") as mock_svc,
            patch("app.api.v1.clients.get_db"),
        ):
            mock_svc.soft_delete = AsyncMock(return_value=None)

            from app.api.v1.clients import delete_client

            mock_db = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await delete_client(client_id=1, studio_id=other_studio, db=mock_db)

        assert exc_info.value.status_code == 404
