"""DEV-329: Unit Tests for NormativeMatchingService and ProfileEmbeddingService.

Tests structured rule evaluation, field comparison, hybrid matching
(structured + semantic fallback), and profile embedding text generation.
"""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.normative_matching_service import (
    NormativeMatchingService,
    _compare,
    _get_field_value,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service() -> NormativeMatchingService:
    return NormativeMatchingService()


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def mock_client():
    """Client-like object using SimpleNamespace to avoid MagicMock auto-attrs."""
    return SimpleNamespace(
        id=1,
        studio_id=uuid4(),
        tipo_cliente="persona_fisica",
        provincia="RM",
        deleted_at=None,
    )


@pytest.fixture
def mock_profile():
    """ClientProfile-like object."""
    return SimpleNamespace(
        client_id=1,
        codice_ateco_principale="10.11.00",
        regime_fiscale="ordinario",
        n_dipendenti=5,
        profile_vector=[0.1] * 1536,
    )


# ---------------------------------------------------------------------------
# _get_field_value tests
# ---------------------------------------------------------------------------


class TestGetFieldValue:
    """Tests for the _get_field_value helper function."""

    def test_client_field(self, mock_client: SimpleNamespace) -> None:
        result = _get_field_value(mock_client, None, "tipo_cliente")
        assert result == "persona_fisica"

    def test_client_provincia(self, mock_client: SimpleNamespace) -> None:
        result = _get_field_value(mock_client, None, "provincia")
        assert result == "RM"

    def test_profile_field_with_profile(self, mock_client: SimpleNamespace, mock_profile: SimpleNamespace) -> None:
        result = _get_field_value(mock_client, mock_profile, "profile.regime_fiscale")
        assert result == "ordinario"

    def test_profile_field_no_profile(self, mock_client: SimpleNamespace) -> None:
        """When profile is None and field starts with profile., fallback to client getattr."""
        result = _get_field_value(mock_client, None, "profile.regime_fiscale")
        # SimpleNamespace doesn't have 'profile.regime_fiscale', returns None
        assert result is None

    def test_nonexistent_field(self, mock_client: SimpleNamespace) -> None:
        """Non-existent field on SimpleNamespace returns None via getattr default."""
        result = _get_field_value(mock_client, None, "nonexistent_field")
        assert result is None

    def test_profile_ateco(self, mock_client: SimpleNamespace, mock_profile: SimpleNamespace) -> None:
        result = _get_field_value(mock_client, mock_profile, "profile.codice_ateco_principale")
        assert result == "10.11.00"


# ---------------------------------------------------------------------------
# _compare tests
# ---------------------------------------------------------------------------


class TestCompare:
    """Tests for the _compare helper function."""

    def test_eq_match(self) -> None:
        assert _compare("ordinario", "eq", "ordinario") is True

    def test_eq_no_match(self) -> None:
        assert _compare("forfettario", "eq", "ordinario") is False

    def test_neq_match(self) -> None:
        assert _compare("forfettario", "neq", "ordinario") is True

    def test_neq_no_match(self) -> None:
        assert _compare("ordinario", "neq", "ordinario") is False

    def test_in_list_match(self) -> None:
        assert _compare("RM", "in", ["RM", "MI", "TO"]) is True

    def test_in_list_no_match(self) -> None:
        assert _compare("NA", "in", ["RM", "MI", "TO"]) is False

    def test_in_not_list(self) -> None:
        assert _compare("RM", "in", "RM") is False

    def test_contains_string(self) -> None:
        assert _compare("codice_10.11.00", "contains", "10.11") is True

    def test_contains_list(self) -> None:
        assert _compare(["A", "B", "C"], "contains", "B") is True

    def test_contains_list_no_match(self) -> None:
        assert _compare(["A", "B", "C"], "contains", "D") is False

    def test_gte_match(self) -> None:
        assert _compare(10, "gte", 5) is True

    def test_gte_equal(self) -> None:
        assert _compare(5, "gte", 5) is True

    def test_gte_no_match(self) -> None:
        assert _compare(3, "gte", 5) is False

    def test_lte_match(self) -> None:
        assert _compare(3, "lte", 5) is True

    def test_lte_no_match(self) -> None:
        assert _compare(10, "lte", 5) is False

    def test_none_value_always_false(self) -> None:
        assert _compare(None, "eq", "anything") is False

    def test_unknown_operator(self) -> None:
        assert _compare("a", "unknown_op", "b") is False

    def test_gte_non_numeric(self) -> None:
        assert _compare("abc", "gte", 5) is False


# ---------------------------------------------------------------------------
# _evaluate_conditions tests
# ---------------------------------------------------------------------------


class TestEvaluateConditions:
    """Tests for NormativeMatchingService._evaluate_conditions."""

    def test_empty_conditions(self, mock_client: SimpleNamespace) -> None:
        result = NormativeMatchingService._evaluate_conditions({}, mock_client, None)
        assert result == 0.0

    def test_no_rules(self, mock_client: SimpleNamespace) -> None:
        conditions = {"operator": "AND", "rules": []}
        result = NormativeMatchingService._evaluate_conditions(conditions, mock_client, None)
        assert result == 0.0

    def test_and_all_match(self, mock_client: SimpleNamespace) -> None:
        conditions = {
            "operator": "AND",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                {"field": "provincia", "op": "eq", "value": "RM"},
            ],
        }
        result = NormativeMatchingService._evaluate_conditions(conditions, mock_client, None)
        assert result == 1.0

    def test_and_partial_match(self, mock_client: SimpleNamespace) -> None:
        conditions = {
            "operator": "AND",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                {"field": "provincia", "op": "eq", "value": "MI"},
            ],
        }
        result = NormativeMatchingService._evaluate_conditions(conditions, mock_client, None)
        assert result == 0.0

    def test_or_partial_match(self, mock_client: SimpleNamespace) -> None:
        conditions = {
            "operator": "OR",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                {"field": "provincia", "op": "eq", "value": "MI"},
            ],
        }
        result = NormativeMatchingService._evaluate_conditions(conditions, mock_client, None)
        assert result == 0.5

    def test_or_all_match(self, mock_client: SimpleNamespace) -> None:
        conditions = {
            "operator": "OR",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                {"field": "provincia", "op": "eq", "value": "RM"},
            ],
        }
        result = NormativeMatchingService._evaluate_conditions(conditions, mock_client, None)
        assert result == 1.0

    def test_with_profile_fields(self, mock_client: SimpleNamespace, mock_profile: SimpleNamespace) -> None:
        conditions = {
            "operator": "AND",
            "rules": [
                {"field": "profile.regime_fiscale", "op": "eq", "value": "ordinario"},
                {"field": "profile.n_dipendenti", "op": "gte", "value": 3},
            ],
        }
        result = NormativeMatchingService._evaluate_conditions(conditions, mock_client, mock_profile)
        assert result == 1.0


# ---------------------------------------------------------------------------
# match_rule_to_clients tests
# ---------------------------------------------------------------------------


class TestMatchRuleToClients:
    """Tests for NormativeMatchingService.match_rule_to_clients."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_rule_not_found(self, service: NormativeMatchingService, mock_db: AsyncMock, studio_id) -> None:
        mock_db.get = AsyncMock(return_value=None)
        rule_id = uuid4()

        with pytest.raises(ValueError, match="non trovata"):
            await service.match_rule_to_clients(mock_db, rule_id=rule_id, studio_id=studio_id)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_rule_inactive(self, service: NormativeMatchingService, mock_db: AsyncMock, studio_id) -> None:
        rule = MagicMock()
        rule.is_active = False
        mock_db.get = AsyncMock(return_value=rule)

        with pytest.raises(ValueError, match="non è attiva"):
            await service.match_rule_to_clients(mock_db, rule_id=uuid4(), studio_id=studio_id)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_rule_future_valid_from(
        self, service: NormativeMatchingService, mock_db: AsyncMock, studio_id
    ) -> None:
        rule = MagicMock()
        rule.is_active = True
        rule.valid_from = date.today() + timedelta(days=30)
        rule.valid_to = None
        mock_db.get = AsyncMock(return_value=rule)

        result = await service.match_rule_to_clients(mock_db, rule_id=uuid4(), studio_id=studio_id)
        assert result == []

    @pytest.mark.asyncio(loop_scope="function")
    async def test_rule_expired(self, service: NormativeMatchingService, mock_db: AsyncMock, studio_id) -> None:
        rule = MagicMock()
        rule.is_active = True
        rule.valid_from = date.today() - timedelta(days=60)
        rule.valid_to = date.today() - timedelta(days=1)
        mock_db.get = AsyncMock(return_value=rule)

        result = await service.match_rule_to_clients(mock_db, rule_id=uuid4(), studio_id=studio_id)
        assert result == []

    @pytest.mark.asyncio(loop_scope="function")
    async def test_structured_match_returns_results(
        self, service: NormativeMatchingService, mock_db: AsyncMock, studio_id
    ) -> None:
        rule = MagicMock()
        rule.is_active = True
        rule.valid_from = date.today() - timedelta(days=10)
        rule.valid_to = None
        mock_db.get = AsyncMock(return_value=rule)

        expected_matches = [{"client_id": 1, "score": 1.0, "method": "structured"}]
        with patch.object(service, "_structured_match", AsyncMock(return_value=expected_matches)):
            result = await service.match_rule_to_clients(mock_db, rule_id=uuid4(), studio_id=studio_id)
        assert result == expected_matches

    @pytest.mark.asyncio(loop_scope="function")
    async def test_semantic_fallback(self, service: NormativeMatchingService, mock_db: AsyncMock, studio_id) -> None:
        rule = MagicMock()
        rule.is_active = True
        rule.valid_from = date.today() - timedelta(days=10)
        rule.valid_to = None
        mock_db.get = AsyncMock(return_value=rule)

        semantic_matches = [{"client_id": 2, "score": 0.8, "method": "semantic"}]
        with (
            patch.object(service, "_structured_match", AsyncMock(return_value=[])),
            patch.object(service, "_semantic_match", AsyncMock(return_value=semantic_matches)),
        ):
            result = await service.match_rule_to_clients(mock_db, rule_id=uuid4(), studio_id=studio_id)
        assert result == semantic_matches


# ---------------------------------------------------------------------------
# ProfileEmbeddingService tests
# ---------------------------------------------------------------------------


class TestProfileEmbeddingService:
    """Tests for ProfileEmbeddingService."""

    def test_build_profile_text_full(self) -> None:
        from app.services.profile_embedding_service import ProfileEmbeddingService

        svc = ProfileEmbeddingService()
        profile = SimpleNamespace(
            codice_ateco_principale="10.11.00",
            codici_ateco_secondari=["10.12.00"],
            regime_fiscale="ordinario",
            ccnl_applicato="commercio",
            n_dipendenti=5,
            data_inizio_attivita=date(2020, 1, 1),
            immobili=["casa"],
        )
        text = svc.build_profile_text(profile)
        assert "10.11.00" in text
        assert "ordinario" in text

    def test_build_profile_text_minimal(self) -> None:
        from app.services.profile_embedding_service import ProfileEmbeddingService

        svc = ProfileEmbeddingService()
        profile = SimpleNamespace(
            codice_ateco_principale="62.01",
            codici_ateco_secondari=[],
            regime_fiscale="forfettario",
            ccnl_applicato=None,
            n_dipendenti=0,
            data_inizio_attivita=None,
            immobili=[],
        )
        text = svc.build_profile_text(profile)
        assert "62.01" in text
        assert "forfettario" in text
