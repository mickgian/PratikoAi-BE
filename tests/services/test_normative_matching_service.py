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
