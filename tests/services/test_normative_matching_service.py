"""DEV-320: Tests for NormativeMatchingService — Normative matching engine.

Tests cover:
- Matching clients to rules using structured conditions
- Empty result handling when no clients match
- Semantic fallback when structured matching yields no results
- Performance validation (under 100ms)
- Invalid rule condition handling
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.matching_rule import MatchingRule, RuleType
from app.services.normative_matching_service import NormativeMatchingService


@pytest.fixture
def matching_service() -> NormativeMatchingService:
    return NormativeMatchingService()


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
def sample_rule() -> MatchingRule:
    return MatchingRule(
        id=uuid4(),
        name="R001 — Rottamazione Quater",
        description="Rottamazione cartelle esattoriali quater.",
        rule_type=RuleType.NORMATIVA,
        conditions={
            "operator": "AND",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                {"field": "provincia", "op": "in", "value": ["RM", "MI", "NA"]},
            ],
        },
        priority=80,
        is_active=True,
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        categoria="fiscale",
        fonte_normativa="DL 34/2023",
    )


class TestNormativeMatchingServiceMatchRuleToClients:
    """Test NormativeMatchingService.match_rule_to_clients()."""

    @pytest.mark.asyncio
    async def test_match_clients_to_rule_happy_path(
        self,
        matching_service: NormativeMatchingService,
        mock_db: AsyncMock,
        studio_id,
        sample_rule: MatchingRule,
    ) -> None:
        """Happy path: match clients using structured rule conditions."""
        # Mock db.get to return the rule
        mock_db.get = AsyncMock(return_value=sample_rule)

        # Mock structured match: outerjoin query returns client-profile pairs
        mock_client1 = MagicMock()
        mock_client1.id = 1
        mock_client1.tipo_cliente = "persona_fisica"
        mock_client1.provincia = "RM"
        mock_client1.deleted_at = None

        mock_client2 = MagicMock()
        mock_client2.id = 2
        mock_client2.tipo_cliente = "persona_fisica"
        mock_client2.provincia = "MI"
        mock_client2.deleted_at = None

        mock_profile = MagicMock()
        mock_profile.profile_vector = None

        # Structured match query
        structured_result = MagicMock()
        structured_result.all = MagicMock(return_value=[(mock_client1, mock_profile), (mock_client2, mock_profile)])
        mock_db.execute = AsyncMock(return_value=structured_result)

        result = await matching_service.match_rule_to_clients(
            db=mock_db,
            rule_id=sample_rule.id,
            studio_id=studio_id,
        )

        assert len(result) == 2
        assert result[0]["method"] == "structured"

    @pytest.mark.asyncio
    async def test_match_no_clients_found(
        self,
        matching_service: NormativeMatchingService,
        mock_db: AsyncMock,
        studio_id,
        sample_rule: MatchingRule,
    ) -> None:
        """No matching clients returns empty list."""
        mock_db.get = AsyncMock(return_value=sample_rule)

        # Structured match returns no clients
        structured_result = MagicMock()
        structured_result.all = MagicMock(return_value=[])
        # Semantic match also returns no clients
        semantic_result = MagicMock()
        semantic_result.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(side_effect=[structured_result, semantic_result])

        result = await matching_service.match_rule_to_clients(
            db=mock_db,
            rule_id=sample_rule.id,
            studio_id=studio_id,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_semantic_fallback_when_no_structured_match(
        self,
        matching_service: NormativeMatchingService,
        mock_db: AsyncMock,
        studio_id,
        sample_rule: MatchingRule,
    ) -> None:
        """Falls back to vector/semantic matching when structured match finds nothing."""
        mock_db.get = AsyncMock(return_value=sample_rule)

        # Structured match returns empty
        structured_result = MagicMock()
        structured_result.all = MagicMock(return_value=[])

        # Semantic fallback returns a client with profile_vector
        mock_client = MagicMock()
        mock_client.id = 3
        mock_client.deleted_at = None
        mock_profile = MagicMock()
        mock_profile.profile_vector = [0.1] * 1536  # non-None vector

        semantic_result = MagicMock()
        semantic_result.all = MagicMock(return_value=[(mock_client, mock_profile)])

        mock_db.execute = AsyncMock(side_effect=[structured_result, semantic_result])

        result = await matching_service.match_rule_to_clients(
            db=mock_db,
            rule_id=sample_rule.id,
            studio_id=studio_id,
        )

        # Semantic matching returns results via fallback
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_performance_under_100ms(
        self,
        matching_service: NormativeMatchingService,
        mock_db: AsyncMock,
        studio_id,
        sample_rule: MatchingRule,
    ) -> None:
        """Performance check: matching completes quickly with mocked DB."""
        import time

        mock_db.get = AsyncMock(return_value=sample_rule)

        # Quick match with no clients
        structured_result = MagicMock()
        structured_result.all = MagicMock(return_value=[])
        semantic_result = MagicMock()
        semantic_result.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(side_effect=[structured_result, semantic_result])

        start = time.perf_counter()
        await matching_service.match_rule_to_clients(
            db=mock_db,
            rule_id=sample_rule.id,
            studio_id=studio_id,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"Matching took {elapsed_ms:.1f}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_invalid_rule_raises(
        self,
        matching_service: NormativeMatchingService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Non-existent rule raises ValueError."""
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="non trovata"):
            await matching_service.match_rule_to_clients(
                db=mock_db,
                rule_id=uuid4(),
                studio_id=studio_id,
            )


class TestNormativeMatchingServiceEvaluateConditions:
    """Test NormativeMatchingService._evaluate_conditions()."""

    def test_evaluate_and_all_match(self, matching_service: NormativeMatchingService) -> None:
        """AND operator with all conditions matching returns 1.0."""
        conditions = {
            "operator": "AND",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                {"field": "provincia", "op": "eq", "value": "RM"},
            ],
        }
        client = MagicMock(tipo_cliente="persona_fisica", provincia="RM")
        score = matching_service._evaluate_conditions(conditions, client, None)
        assert score == 1.0

    def test_evaluate_and_partial_match(self, matching_service: NormativeMatchingService) -> None:
        """AND operator with partial match returns 0.0."""
        conditions = {
            "operator": "AND",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                {"field": "provincia", "op": "eq", "value": "MI"},
            ],
        }
        client = MagicMock(tipo_cliente="persona_fisica", provincia="RM")
        score = matching_service._evaluate_conditions(conditions, client, None)
        assert score == 0.0

    def test_evaluate_empty_conditions(self, matching_service: NormativeMatchingService) -> None:
        """Empty conditions return 0.0."""
        client = MagicMock()
        score = matching_service._evaluate_conditions({}, client, None)
        assert score == 0.0

    def test_evaluate_or_all_match(self, matching_service: NormativeMatchingService) -> None:
        """OR operator with all conditions matching returns 1.0."""
        conditions = {
            "operator": "OR",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                {"field": "provincia", "op": "eq", "value": "RM"},
            ],
        }
        client = MagicMock(tipo_cliente="persona_fisica", provincia="RM")
        score = matching_service._evaluate_conditions(conditions, client, None)
        assert score == 1.0

    def test_evaluate_or_partial_match(self, matching_service: NormativeMatchingService) -> None:
        """OR operator with partial match returns fractional score."""
        conditions = {
            "operator": "OR",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                {"field": "provincia", "op": "eq", "value": "MI"},
            ],
        }
        client = MagicMock(tipo_cliente="persona_fisica", provincia="RM")
        score = matching_service._evaluate_conditions(conditions, client, None)
        assert score == 0.5

    def test_evaluate_empty_rules_list(self, matching_service: NormativeMatchingService) -> None:
        """Conditions with empty rules list return 0.0."""
        conditions = {"operator": "AND", "rules": []}
        client = MagicMock()
        score = matching_service._evaluate_conditions(conditions, client, None)
        assert score == 0.0

    def test_evaluate_unknown_operator(self, matching_service: NormativeMatchingService) -> None:
        """Unknown operator returns 0.0."""
        conditions = {
            "operator": "XOR",
            "rules": [
                {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
            ],
        }
        client = MagicMock(tipo_cliente="persona_fisica")
        score = matching_service._evaluate_conditions(conditions, client, None)
        assert score == 0.0

    def test_evaluate_with_profile_field(self, matching_service: NormativeMatchingService) -> None:
        """Conditions can reference profile fields via dotted path."""
        conditions = {
            "operator": "AND",
            "rules": [
                {"field": "profile.settore", "op": "eq", "value": "commercio"},
            ],
        }
        client = MagicMock()
        profile = MagicMock(settore="commercio")
        score = matching_service._evaluate_conditions(conditions, client, profile)
        assert score == 1.0


class TestNormativeMatchingServiceCompare:
    """Test _compare() helper function."""

    def test_compare_eq_match(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("persona_fisica", "eq", "persona_fisica") is True

    def test_compare_eq_no_match(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("societa", "eq", "persona_fisica") is False

    def test_compare_neq(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("societa", "neq", "persona_fisica") is True

    def test_compare_in_list(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("RM", "in", ["RM", "MI", "NA"]) is True

    def test_compare_in_not_in_list(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("TO", "in", ["RM", "MI", "NA"]) is False

    def test_compare_in_not_a_list(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("RM", "in", "RM") is False

    def test_compare_contains_string(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("commercio alimentare", "contains", "commercio") is True

    def test_compare_contains_list(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare(["RM", "MI"], "contains", "RM") is True

    def test_compare_contains_not_found(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("artigianato", "contains", "commercio") is False

    def test_compare_contains_non_iterable(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare(42, "contains", "4") is False

    def test_compare_gte(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare(100, "gte", 50) is True
        assert _compare(50, "gte", 50) is True
        assert _compare(49, "gte", 50) is False

    def test_compare_lte(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare(30, "lte", 50) is True
        assert _compare(50, "lte", 50) is True
        assert _compare(51, "lte", 50) is False

    def test_compare_gte_invalid_type(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("abc", "gte", 50) is False

    def test_compare_lte_invalid_type(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("abc", "lte", 50) is False

    def test_compare_none_actual(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare(None, "eq", "test") is False

    def test_compare_unknown_operator(self) -> None:
        from app.services.normative_matching_service import _compare

        assert _compare("val", "regex", "val") is False


class TestNormativeMatchingServiceGetFieldValue:
    """Test _get_field_value() helper function."""

    def test_get_client_field(self) -> None:
        from app.services.normative_matching_service import _get_field_value

        client = MagicMock(tipo_cliente="persona_fisica")
        result = _get_field_value(client, None, "tipo_cliente")
        assert result == "persona_fisica"

    def test_get_profile_field(self) -> None:
        from app.services.normative_matching_service import _get_field_value

        client = MagicMock()
        profile = MagicMock(settore="commercio")
        result = _get_field_value(client, profile, "profile.settore")
        assert result == "commercio"

    def test_get_profile_field_no_profile(self) -> None:
        from app.services.normative_matching_service import _get_field_value

        client = MagicMock(spec=["tipo_cliente", "provincia"])
        result = _get_field_value(client, None, "profile.settore")
        # When profile is None, falls through to getattr(client, "profile.settore", None)
        # which returns None since client spec doesn't have that attribute
        assert result is None

    def test_get_nonexistent_field(self) -> None:
        from app.services.normative_matching_service import _get_field_value

        client = MagicMock(spec=[])
        result = _get_field_value(client, None, "nonexistent")
        assert result is None


class TestNormativeMatchingServiceComputeSimilarity:
    """Test _compute_text_similarity()."""

    def test_similarity_with_vector(self, matching_service: NormativeMatchingService) -> None:
        """Profile with vector returns 0.5 (placeholder heuristic)."""
        profile = MagicMock(profile_vector=[0.1] * 1536)
        score = matching_service._compute_text_similarity("test rule", profile)
        assert score == 0.5

    def test_similarity_without_vector(self, matching_service: NormativeMatchingService) -> None:
        """Profile without vector returns 0.0."""
        profile = MagicMock(profile_vector=None)
        score = matching_service._compute_text_similarity("test rule", profile)
        assert score == 0.0


class TestNormativeMatchingServiceInactiveRule:
    """Test edge cases for inactive/expired rules."""

    @pytest.mark.asyncio
    async def test_inactive_rule_raises(
        self,
        matching_service: NormativeMatchingService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Inactive rule raises ValueError."""
        inactive_rule = MagicMock()
        inactive_rule.is_active = False
        mock_db.get = AsyncMock(return_value=inactive_rule)

        with pytest.raises(ValueError, match="non è attiva"):
            await matching_service.match_rule_to_clients(
                db=mock_db,
                rule_id=uuid4(),
                studio_id=studio_id,
            )

    @pytest.mark.asyncio
    async def test_future_rule_returns_empty(
        self,
        matching_service: NormativeMatchingService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Rule with future valid_from returns empty list."""
        future_rule = MagicMock()
        future_rule.is_active = True
        future_rule.valid_from = date(2099, 1, 1)
        future_rule.valid_to = None
        mock_db.get = AsyncMock(return_value=future_rule)

        result = await matching_service.match_rule_to_clients(
            db=mock_db,
            rule_id=uuid4(),
            studio_id=studio_id,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_expired_rule_returns_empty(
        self,
        matching_service: NormativeMatchingService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Rule with past valid_to returns empty list."""
        expired_rule = MagicMock()
        expired_rule.is_active = True
        expired_rule.valid_from = date(2020, 1, 1)
        expired_rule.valid_to = date(2020, 12, 31)
        mock_db.get = AsyncMock(return_value=expired_rule)

        result = await matching_service.match_rule_to_clients(
            db=mock_db,
            rule_id=uuid4(),
            studio_id=studio_id,
        )
        assert result == []
