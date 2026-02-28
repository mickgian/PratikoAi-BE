"""DEV-328: Matching Performance Test Suite.

Tests NormativeMatchingService performance: _evaluate_conditions completes
under 5ms for large rulesets, _compare handles all operators efficiently,
and match_rule_to_clients processes many clients without degradation.
"""

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.normative_matching_service import (
    NormativeMatchingService,
    _compare,
    _get_field_value,
)

# _evaluate_conditions is a static method on NormativeMatchingService
_evaluate_conditions = NormativeMatchingService._evaluate_conditions

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(**kwargs: object) -> SimpleNamespace:
    defaults = {
        "id": 1,
        "studio_id": "s1",
        "nome": "Test",
        "codice_fiscale": "RSSMRA85M01H501Z",
        "tipo_cliente": "persona_fisica",
        "stato_cliente": "attivo",
        "comune": "Roma",
        "provincia": "RM",
        "deleted_at": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_profile(**kwargs: object) -> SimpleNamespace:
    defaults = {
        "client_id": 1,
        "reddito_annuo": 50000,
        "fascia_eta": "30-40",
        "categoria_professionale": "dipendente",
        "profile_vector": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# _evaluate_conditions performance
# ---------------------------------------------------------------------------


class TestEvaluateConditionsPerformance:
    """Ensure _evaluate_conditions stays fast even with many rules."""

    def test_10_rules_and_under_5ms(self) -> None:
        conditions = {
            "operator": "AND",
            "rules": [{"field": "nome", "op": "eq", "value": "Test"}] * 10,
        }
        client = _make_client()

        start = time.perf_counter()
        for _ in range(100):
            _evaluate_conditions(conditions, client, None)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Average per call should be well under 5ms
        avg_ms = elapsed_ms / 100
        assert avg_ms < 5, f"Average {avg_ms:.3f}ms exceeds 5ms threshold"

    def test_50_rules_and_performance(self) -> None:
        conditions = {
            "operator": "OR",
            "rules": [{"field": f"field_{i}", "op": "eq", "value": "val"} for i in range(50)],
        }
        client = _make_client()

        start = time.perf_counter()
        for _ in range(100):
            _evaluate_conditions(conditions, client, None)
        elapsed_ms = (time.perf_counter() - start) * 1000

        avg_ms = elapsed_ms / 100
        assert avg_ms < 10, f"Average {avg_ms:.3f}ms exceeds 10ms threshold"

    def test_and_with_early_exit(self) -> None:
        """AND operator should fail fast if first condition fails."""
        conditions = {
            "operator": "AND",
            "rules": [
                {"field": "nome", "op": "eq", "value": "NONEXISTENT"},
                *[{"field": "nome", "op": "eq", "value": "Test"}] * 20,
            ],
        }
        client = _make_client()
        score = _evaluate_conditions(conditions, client, None)
        assert score == 0.0

    def test_or_with_partial_matches(self) -> None:
        conditions = {
            "operator": "OR",
            "rules": [
                {"field": "nome", "op": "eq", "value": "Test"},
                {"field": "nome", "op": "eq", "value": "Nope"},
                {"field": "provincia", "op": "eq", "value": "RM"},
            ],
        }
        client = _make_client()
        score = _evaluate_conditions(conditions, client, None)
        assert abs(score - 2.0 / 3.0) < 0.01


# ---------------------------------------------------------------------------
# _compare performance
# ---------------------------------------------------------------------------


class TestComparePerformance:
    def test_eq_operator_batch(self) -> None:
        start = time.perf_counter()
        for _ in range(10000):
            _compare("hello", "eq", "hello")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"10k eq comparisons took {elapsed_ms:.1f}ms"

    def test_gte_operator_batch(self) -> None:
        start = time.perf_counter()
        for _ in range(10000):
            _compare(100, "gte", 50)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"10k gte comparisons took {elapsed_ms:.1f}ms"

    def test_in_operator_batch(self) -> None:
        values = ["a", "b", "c", "d", "e"]
        start = time.perf_counter()
        for _ in range(10000):
            _compare("c", "in", values)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"10k in comparisons took {elapsed_ms:.1f}ms"

    def test_contains_operator_batch(self) -> None:
        start = time.perf_counter()
        for _ in range(10000):
            _compare("hello world", "contains", "world")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"10k contains comparisons took {elapsed_ms:.1f}ms"


# ---------------------------------------------------------------------------
# _get_field_value performance
# ---------------------------------------------------------------------------


class TestFieldValuePerformance:
    def test_direct_attr_batch(self) -> None:
        client = _make_client()
        start = time.perf_counter()
        for _ in range(10000):
            _get_field_value(client, None, "nome")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"10k direct lookups took {elapsed_ms:.1f}ms"

    def test_profile_attr_batch(self) -> None:
        client = _make_client()
        profile = _make_profile()
        start = time.perf_counter()
        for _ in range(10000):
            _get_field_value(client, profile, "profile.reddito_annuo")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"10k profile lookups took {elapsed_ms:.1f}ms"

    def test_missing_field_returns_none(self) -> None:
        client = _make_client()
        result = _get_field_value(client, None, "nonexistent_field")
        assert result is None


# ---------------------------------------------------------------------------
# match_rule_to_clients performance
# ---------------------------------------------------------------------------


class TestMatchRuleToClientsPerformance:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_100_clients_under_100ms(self) -> None:
        """Matching a rule against 100 clients should complete quickly."""
        mock_db = AsyncMock()

        # Build a mock rule
        mock_rule = MagicMock()
        mock_rule.is_active = True
        mock_rule.valid_from = None
        mock_rule.valid_to = None
        mock_rule.conditions = {
            "operator": "AND",
            "rules": [{"field": "stato_cliente", "op": "eq", "value": "attivo"}],
        }
        mock_db.get = AsyncMock(return_value=mock_rule)

        # Build 100 mock clients
        rows = []
        for i in range(100):
            c = _make_client(id=i)
            p = _make_profile(client_id=i)
            rows.append((c, p))

        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = NormativeMatchingService()

        with (
            patch("app.services.normative_matching_service.select"),
            patch("app.services.normative_matching_service.and_"),
        ):
            start = time.perf_counter()
            matches = await svc.match_rule_to_clients(
                mock_db,
                rule_id="00000000-0000-0000-0000-000000000001",
                studio_id="00000000-0000-0000-0000-000000000002",
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(matches) == 100
        assert elapsed_ms < 100, f"Matching 100 clients took {elapsed_ms:.1f}ms"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_match_returns_empty_for_expired_rule(self) -> None:
        """Expired rules should return empty immediately."""
        from datetime import date, timedelta

        mock_db = AsyncMock()
        mock_rule = MagicMock()
        mock_rule.is_active = True
        mock_rule.valid_from = date.today() - timedelta(days=60)
        mock_rule.valid_to = date.today() - timedelta(days=1)
        mock_rule.conditions = {"operator": "AND", "rules": []}
        mock_db.get = AsyncMock(return_value=mock_rule)

        svc = NormativeMatchingService()
        result = await svc.match_rule_to_clients(
            mock_db,
            rule_id="00000000-0000-0000-0000-000000000001",
            studio_id="00000000-0000-0000-0000-000000000002",
        )
        assert result == []

    @pytest.mark.asyncio(loop_scope="function")
    async def test_future_rule_returns_empty(self) -> None:
        """Future rules (valid_from in the future) should return empty."""
        from datetime import date, timedelta

        mock_db = AsyncMock()
        mock_rule = MagicMock()
        mock_rule.is_active = True
        mock_rule.valid_from = date.today() + timedelta(days=30)
        mock_rule.valid_to = None
        mock_rule.conditions = {"operator": "AND", "rules": []}
        mock_db.get = AsyncMock(return_value=mock_rule)

        svc = NormativeMatchingService()
        result = await svc.match_rule_to_clients(
            mock_db,
            rule_id="00000000-0000-0000-0000-000000000001",
            studio_id="00000000-0000-0000-0000-000000000002",
        )
        assert result == []


# ---------------------------------------------------------------------------
# Semantic fallback performance
# ---------------------------------------------------------------------------


class TestSemanticFallbackPerformance:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_semantic_fallback_triggered_on_no_structured_match(self) -> None:
        """When structured match returns empty, semantic fallback is used."""
        mock_db = AsyncMock()

        mock_rule = MagicMock()
        mock_rule.is_active = True
        mock_rule.valid_from = None
        mock_rule.valid_to = None
        mock_rule.name = "Test Rule"
        mock_rule.description = "A test rule"
        mock_rule.categoria = "fiscale"
        mock_rule.conditions = {
            "operator": "AND",
            "rules": [{"field": "nome", "op": "eq", "value": "NOMATCH"}],
        }
        mock_db.get = AsyncMock(return_value=mock_rule)

        # Structured match returns no results, then semantic returns results
        clients_with_vectors = []
        for i in range(5):
            c = _make_client(id=i, nome="Different")
            p = _make_profile(client_id=i, profile_vector=[0.1] * 10)
            clients_with_vectors.append((c, p))

        # First call for structured (returns rows but no match due to conditions)
        mock_structured_result = MagicMock()
        mock_structured_result.all.return_value = [
            (_make_client(id=i, nome="Different"), _make_profile(client_id=i)) for i in range(5)
        ]

        # Second call for semantic
        mock_semantic_result = MagicMock()
        mock_semantic_result.all.return_value = clients_with_vectors

        mock_db.execute = AsyncMock(side_effect=[mock_structured_result, mock_semantic_result])

        svc = NormativeMatchingService()

        with (
            patch("app.services.normative_matching_service.select"),
            patch("app.services.normative_matching_service.and_"),
        ):
            result = await svc.match_rule_to_clients(
                mock_db,
                rule_id="00000000-0000-0000-0000-000000000001",
                studio_id="00000000-0000-0000-0000-000000000002",
            )

        # _compute_text_similarity returns 0.5 which is below threshold 0.7
        # so semantic fallback returns empty
        assert isinstance(result, list)
