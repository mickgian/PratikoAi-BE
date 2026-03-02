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


class TestCessatoSuggestions:
    """Cessato clients get chiusura procedures."""

    @pytest.mark.asyncio
    async def test_cessato_gets_chiusura(self, svc, studio_id) -> None:
        """Cessato client → chiusura procedure suggested."""
        from app.models.client import StatoCliente

        procedures = [_make_procedure("CHIUSURA_PIVA", "Cessazione Partita IVA")]
        client = _make_client(StatoCliente.CESSATO)

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
        assert result[0]["code"] == "CHIUSURA_PIVA"
        assert "cessato" in result[0]["reason"].lower()


class TestSemplificatoSuggestions:
    """Semplificato clients get passaggio ordinario suggestions."""

    @pytest.mark.asyncio
    async def test_semplificato_gets_passaggio(self, svc, studio_id) -> None:
        """Semplificato regime → passaggio a ordinario suggested."""
        from app.models.client import StatoCliente
        from app.models.client_profile import RegimeFiscale

        procedures = [_make_procedure("PASSAGGIO_ORDINARIO", "Passaggio a Regime Ordinario")]
        client = _make_client(StatoCliente.ATTIVO)
        profile = _make_profile(RegimeFiscale.SEMPLIFICATO)

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
        assert result[0]["code"] == "PASSAGGIO_ORDINARIO"
        assert "semplificato" in result[0]["reason"].lower()


class TestAtecoConstructionSuggestions:
    """Construction sector clients get sicurezza procedures."""

    @pytest.mark.asyncio
    async def test_construction_ateco_gets_sicurezza(self, svc, studio_id) -> None:
        """Construction ATECO code (41.x) → sicurezza procedure suggested."""
        from app.models.client import StatoCliente
        from app.models.client_profile import RegimeFiscale

        procedures = [_make_procedure("CANTIERE_SIC", "Sicurezza Cantiere")]
        client = _make_client(StatoCliente.ATTIVO)
        profile = _make_profile(RegimeFiscale.ORDINARIO, ateco="41.20.00")

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
        assert result[0]["code"] == "CANTIERE_SIC"
        assert "edile" in result[0]["reason"].lower()

    @pytest.mark.asyncio
    async def test_no_ateco_skips_ateco_matching(self, svc) -> None:
        """Profile without ATECO code skips ATECO matching."""
        from app.models.client_profile import RegimeFiscale

        procedures = [_make_procedure("CANTIERE_SIC", "Sicurezza Cantiere")]
        profile = _make_profile(RegimeFiscale.ORDINARIO, ateco="")

        result = svc._match_by_ateco(profile, procedures)
        assert result == []


class TestCacheHelpers:
    """Tests for cache get/set methods."""

    @pytest.mark.asyncio
    async def test_get_from_cache_returns_none_on_error(self, svc) -> None:
        """Cache get failure returns None."""
        with patch("app.services.cache.cache_service") as mock_cache:
            mock_cache._get_redis = AsyncMock(side_effect=Exception("Redis down"))
            result = await svc._get_from_cache("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_from_cache_returns_none_when_no_redis(self, svc) -> None:
        """Cache get returns None when Redis not available."""
        with patch("app.services.cache.cache_service") as mock_cache:
            mock_cache._get_redis = AsyncMock(return_value=None)
            result = await svc._get_from_cache("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_cache_swallows_errors(self, svc) -> None:
        """Cache set failure is silently swallowed."""
        with patch("app.services.cache.cache_service") as mock_cache:
            mock_cache._get_redis = AsyncMock(side_effect=Exception("Redis down"))
            await svc._set_cache("test_key", [{"code": "X"}])

    @pytest.mark.asyncio
    async def test_set_cache_noop_when_no_redis(self, svc) -> None:
        """Cache set is noop when Redis not available."""
        with patch("app.services.cache.cache_service") as mock_cache:
            mock_cache._get_redis = AsyncMock(return_value=None)
            await svc._set_cache("test_key", [{"code": "X"}])
