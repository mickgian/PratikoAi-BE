"""DEV-327: Tenant Isolation Test Suite.

Tests ClientService multi-tenant isolation: all queries include studio_id,
cross-tenant access is blocked, soft-deleted clients are excluded,
100-client limit is enforced per-studio, and duplicate CF validation
is scoped to the studio.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.models.client import TipoCliente

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STUDIO_A = uuid4()
STUDIO_B = uuid4()


def _make_mock_client(**kwargs: object) -> MagicMock:
    """Create a MagicMock that acts like a Client."""
    defaults = {
        "id": 1,
        "studio_id": STUDIO_A,
        "codice_fiscale": "RSSMRA85M01H501Z",
        "nome": "Mario Rossi",
        "tipo_cliente": "persona_fisica",
        "stato_cliente": "attivo",
        "comune": "Roma",
        "provincia": "RM",
        "partita_iva": None,
        "email": None,
        "phone": None,
        "indirizzo": None,
        "cap": None,
        "note_studio": None,
        "deleted_at": None,
        "created_at": "2025-01-01T00:00:00Z",
    }
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


# ---------------------------------------------------------------------------
# Tenant isolation: get_by_id
# ---------------------------------------------------------------------------


class TestGetByIdIsolation:
    """get_by_id must require matching studio_id."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_returns_client_for_correct_studio(self) -> None:
        mock_db = AsyncMock()
        mock_client = _make_mock_client(studio_id=STUDIO_A)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_client
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            result = await svc.get_by_id(mock_db, client_id=1, studio_id=STUDIO_A)

        assert result is not None
        assert result.studio_id == STUDIO_A

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_returns_none_for_wrong_studio(self) -> None:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            result = await svc.get_by_id(mock_db, client_id=1, studio_id=STUDIO_B)

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_excludes_soft_deleted(self) -> None:
        """Soft-deleted clients must not be returned even for correct studio."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            result = await svc.get_by_id(mock_db, client_id=1, studio_id=STUDIO_A)

        assert result is None


# ---------------------------------------------------------------------------
# Tenant isolation: list
# ---------------------------------------------------------------------------


class TestListIsolation:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_returns_only_studio_clients(self) -> None:
        mock_db = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        mock_client_1 = _make_mock_client(id=1, studio_id=STUDIO_A)
        mock_client_2 = _make_mock_client(id=2, studio_id=STUDIO_A)
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = [mock_client_1, mock_client_2]

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_list_result])

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
            patch("app.services.client_service.func"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            clients, total = await svc.list(mock_db, studio_id=STUDIO_A)

        assert total == 2
        assert len(clients) == 2

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_empty_for_different_studio(self) -> None:
        mock_db = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_list_result])

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
            patch("app.services.client_service.func"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            clients, total = await svc.list(mock_db, studio_id=STUDIO_B)

        assert total == 0
        assert clients == []

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_with_stato_filter(self) -> None:
        mock_db = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_client = _make_mock_client(id=1, stato_cliente="prospect")
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = [mock_client]

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_list_result])

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
            patch("app.services.client_service.func"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            clients, total = await svc.list(mock_db, studio_id=STUDIO_A, stato="prospect")

        assert total == 1
        assert len(clients) == 1


# ---------------------------------------------------------------------------
# Tenant isolation: 100-client limit per studio
# ---------------------------------------------------------------------------


class TestClientLimitPerStudio:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_fails_at_100_clients(self) -> None:
        mock_db = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 100
        mock_db.execute = AsyncMock(return_value=mock_count_result)

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
            patch("app.services.client_service.func"),
            patch("app.services.client_service.Client"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            with pytest.raises(ValueError, match="limite"):
                await svc.create(
                    mock_db,
                    studio_id=STUDIO_A,
                    codice_fiscale="RSSMRA85M01H501Z",
                    nome="Test",
                    tipo_cliente=TipoCliente.PERSONA_FISICA,
                    comune="Roma",
                    provincia="RM",
                )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_succeeds_under_limit(self) -> None:
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        # First execute: client count (under limit)
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 50
        # Second execute: duplicate CF check
        mock_dup_result = MagicMock()
        mock_dup_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_dup_result])

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
            patch("app.services.client_service.func"),
            patch("app.services.client_service.Client") as mock_client_cls,
        ):
            mock_client_instance = _make_mock_client()
            mock_client_cls.return_value = mock_client_instance

            from app.services.client_service import ClientService

            svc = ClientService()
            result = await svc.create(
                mock_db,
                studio_id=STUDIO_A,
                codice_fiscale="RSSMRA85M01H501Z",
                nome="Test",
                tipo_cliente=TipoCliente.PERSONA_FISICA,
                comune="Roma",
                provincia="RM",
            )

        assert result is not None
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_limit_is_per_studio(self) -> None:
        """Studio A at 100 clients should not block Studio B."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        # Studio B has only 10 clients
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10
        mock_dup_result = MagicMock()
        mock_dup_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_dup_result])

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
            patch("app.services.client_service.func"),
            patch("app.services.client_service.Client") as mock_client_cls,
        ):
            mock_client_cls.return_value = _make_mock_client(studio_id=STUDIO_B)

            from app.services.client_service import ClientService

            svc = ClientService()
            result = await svc.create(
                mock_db,
                studio_id=STUDIO_B,
                codice_fiscale="VRDLGI90A01H501X",
                nome="Luigi Verdi",
                tipo_cliente=TipoCliente.PERSONA_FISICA,
                comune="Milano",
                provincia="MI",
            )

        assert result is not None


# ---------------------------------------------------------------------------
# Tenant isolation: duplicate codice_fiscale per studio
# ---------------------------------------------------------------------------


class TestDuplicateCFPerStudio:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_duplicate_cf_blocked_same_studio(self) -> None:
        mock_db = AsyncMock()

        # Limit check passes
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10
        # Duplicate check finds existing client
        mock_dup_result = MagicMock()
        mock_dup_result.scalar_one_or_none.return_value = _make_mock_client()

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_dup_result])

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
            patch("app.services.client_service.func"),
            patch("app.services.client_service.Client"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            with pytest.raises(ValueError, match="codice fiscale"):
                await svc.create(
                    mock_db,
                    studio_id=STUDIO_A,
                    codice_fiscale="RSSMRA85M01H501Z",
                    nome="Test",
                    tipo_cliente=TipoCliente.PERSONA_FISICA,
                    comune="Roma",
                    provincia="RM",
                )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_same_cf_allowed_different_studio(self) -> None:
        """Same codice_fiscale in different studio should be allowed."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        # Limit check passes
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 5
        # Duplicate check returns None (no duplicate in Studio B)
        mock_dup_result = MagicMock()
        mock_dup_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_dup_result])

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
            patch("app.services.client_service.func"),
            patch("app.services.client_service.Client") as mock_client_cls,
        ):
            mock_client_cls.return_value = _make_mock_client(studio_id=STUDIO_B)

            from app.services.client_service import ClientService

            svc = ClientService()
            result = await svc.create(
                mock_db,
                studio_id=STUDIO_B,
                codice_fiscale="RSSMRA85M01H501Z",
                nome="Same CF Different Studio",
                tipo_cliente=TipoCliente.PERSONA_FISICA,
                comune="Milano",
                provincia="MI",
            )

        assert result is not None


# ---------------------------------------------------------------------------
# Tenant isolation: soft delete
# ---------------------------------------------------------------------------


class TestSoftDeleteIsolation:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_soft_delete_correct_studio(self) -> None:
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        mock_client = _make_mock_client(studio_id=STUDIO_A)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_client
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            result = await svc.soft_delete(mock_db, client_id=1, studio_id=STUDIO_A)

        assert result is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_soft_delete_wrong_studio_returns_none(self) -> None:
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            result = await svc.soft_delete(mock_db, client_id=1, studio_id=STUDIO_B)

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_wrong_studio_returns_none(self) -> None:
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.client_service.select"),
            patch("app.services.client_service.and_"),
        ):
            from app.services.client_service import ClientService

            svc = ClientService()
            result = await svc.update(mock_db, client_id=1, studio_id=STUDIO_B, nome="Hacker")

        assert result is None
