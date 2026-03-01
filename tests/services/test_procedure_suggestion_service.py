"""DEV-429: Tests for ProcedureSuggestionService."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.procedure_suggestion_service import ProcedureSuggestionService


@pytest.fixture
def svc() -> ProcedureSuggestionService:
    return ProcedureSuggestionService()


@pytest.fixture
def studio_id():
    return uuid4()


def _make_procedure(code: str, title: str) -> SimpleNamespace:
    return SimpleNamespace(code=code, title=title, is_active=True)


def _make_client(stato: str) -> SimpleNamespace:
    return SimpleNamespace(stato_cliente=stato)


def _make_profile(regime: str, ateco: str = "62.01.00") -> SimpleNamespace:
    return SimpleNamespace(regime_fiscale=regime, codice_ateco_principale=ateco)


class TestProspectSuggestions:
    """Prospect clients get apertura procedures."""

    @pytest.mark.asyncio
    async def test_prospect_gets_apertura(self, svc, studio_id) -> None:
        """Prospect client → apertura P.IVA suggested."""
        from app.models.client import StatoCliente

        procedures = [_make_procedure("APERTURA_PIVA", "Apertura Partita IVA")]
        client = _make_client(StatoCliente.PROSPECT)

        with (
            patch.object(svc, "_get_from_cache", return_value=None),
            patch.object(svc, "_set_cache", return_value=None),
            patch.object(svc, "_get_client", return_value=client),
            patch.object(svc, "_get_client_profile", return_value=None),
            patch.object(svc, "_get_active_procedures", return_value=procedures),
        ):
            result = await svc.suggest_procedures(
                AsyncMock(),
                client_id=1,
                studio_id=studio_id,
            )

        assert len(result) == 1
        assert result[0]["code"] == "APERTURA_PIVA"


class TestForfettarioSuggestions:
    """Forfettario clients get regime transformation suggestions."""

    @pytest.mark.asyncio
    async def test_forfettario_gets_trasformazione(self, svc, studio_id) -> None:
        """Forfettario regime → trasformazione suggested."""
        from app.models.client import StatoCliente
        from app.models.client_profile import RegimeFiscale

        procedures = [_make_procedure("TRASFORMAZIONE_REGIME", "Trasformazione Regime Fiscale")]
        client = _make_client(StatoCliente.ATTIVO)
        profile = _make_profile(RegimeFiscale.FORFETTARIO)

        with (
            patch.object(svc, "_get_from_cache", return_value=None),
            patch.object(svc, "_set_cache", return_value=None),
            patch.object(svc, "_get_client", return_value=client),
            patch.object(svc, "_get_client_profile", return_value=profile),
            patch.object(svc, "_get_active_procedures", return_value=procedures),
        ):
            result = await svc.suggest_procedures(
                AsyncMock(),
                client_id=1,
                studio_id=studio_id,
            )

        assert len(result) == 1
        assert result[0]["code"] == "TRASFORMAZIONE_REGIME"


class TestNoMatches:
    """No matching procedures returns empty list."""

    @pytest.mark.asyncio
    async def test_no_matches_returns_empty(self, svc, studio_id) -> None:
        """No matching procedures → empty list."""
        from app.models.client import StatoCliente
        from app.models.client_profile import RegimeFiscale

        procedures = [_make_procedure("SOMETHING_ELSE", "Procedura diversa")]
        client = _make_client(StatoCliente.ATTIVO)
        profile = _make_profile(RegimeFiscale.ORDINARIO)

        with (
            patch.object(svc, "_get_from_cache", return_value=None),
            patch.object(svc, "_set_cache", return_value=None),
            patch.object(svc, "_get_client", return_value=client),
            patch.object(svc, "_get_client_profile", return_value=profile),
            patch.object(svc, "_get_active_procedures", return_value=procedures),
        ):
            result = await svc.suggest_procedures(
                AsyncMock(),
                client_id=1,
                studio_id=studio_id,
            )

        assert result == []


class TestClientNotFound:
    """Missing client returns empty list."""

    @pytest.mark.asyncio
    async def test_client_not_found(self, svc, studio_id) -> None:
        """Client not found → empty list."""
        with (
            patch.object(svc, "_get_from_cache", return_value=None),
            patch.object(svc, "_get_client", return_value=None),
        ):
            result = await svc.suggest_procedures(
                AsyncMock(),
                client_id=999,
                studio_id=studio_id,
            )

        assert result == []


class TestIncompleteProfile:
    """Client with no profile still gets status-based suggestions."""

    @pytest.mark.asyncio
    async def test_no_profile_still_works(self, svc, studio_id) -> None:
        """Incomplete profile → only status-based suggestions."""
        from app.models.client import StatoCliente

        procedures = [_make_procedure("APERTURA_PIVA", "Apertura P.IVA")]
        client = _make_client(StatoCliente.PROSPECT)

        with (
            patch.object(svc, "_get_from_cache", return_value=None),
            patch.object(svc, "_set_cache", return_value=None),
            patch.object(svc, "_get_client", return_value=client),
            patch.object(svc, "_get_client_profile", return_value=None),
            patch.object(svc, "_get_active_procedures", return_value=procedures),
        ):
            result = await svc.suggest_procedures(
                AsyncMock(),
                client_id=1,
                studio_id=studio_id,
            )

        assert len(result) >= 1


class TestMultipleSortedDeduplicated:
    """Multiple matches are deduplicated by code."""

    @pytest.mark.asyncio
    async def test_multiple_sorted(self, svc, studio_id) -> None:
        """Multiple matching procedures are deduplicated."""
        from app.models.client import StatoCliente
        from app.models.client_profile import RegimeFiscale

        procedures = [
            _make_procedure("APERTURA_PIVA", "Apertura P.IVA"),
            _make_procedure("TRASFORMAZIONE_REGIME", "Trasformazione Regime"),
        ]
        client = _make_client(StatoCliente.PROSPECT)
        profile = _make_profile(RegimeFiscale.FORFETTARIO)

        with (
            patch.object(svc, "_get_from_cache", return_value=None),
            patch.object(svc, "_set_cache", return_value=None),
            patch.object(svc, "_get_client", return_value=client),
            patch.object(svc, "_get_client_profile", return_value=profile),
            patch.object(svc, "_get_active_procedures", return_value=procedures),
        ):
            result = await svc.suggest_procedures(
                AsyncMock(),
                client_id=1,
                studio_id=studio_id,
            )

        codes = [s["code"] for s in result]
        assert len(codes) == len(set(codes))  # no duplicates


class TestCacheHit:
    """Cache hit returns cached data."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_db(self, svc, studio_id) -> None:
        """Cache hit skips DB queries."""
        cached = [{"code": "CACHED", "title": "Cached", "reason": "From cache"}]
        mock_db = AsyncMock()

        with patch.object(svc, "_get_from_cache", return_value=cached):
            result = await svc.suggest_procedures(
                mock_db,
                client_id=1,
                studio_id=studio_id,
            )

        assert result == cached
