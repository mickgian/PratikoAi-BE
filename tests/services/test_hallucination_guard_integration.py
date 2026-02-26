"""DEV-389: Tests for Hallucination Guard soft/strict mode and timeout integration."""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_response.citation_validator import (
    _run_with_timeout,
    validate_citations_in_response,
)


class TestHallucinationGuardSoftMode:
    """Soft mode: log warning, continue with flagged response."""

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_MODE", "soft")
    def test_soft_mode_returns_result_with_hallucinations(self) -> None:
        """In soft mode, hallucinated citations are returned but no regeneration flag."""
        response = "La rottamazione è disciplinata dalla Legge n. 197/2022."
        context = "La Legge 30 dicembre 2025 n. 199 disciplina la definizione agevolata."
        state: dict = {"request_id": "soft-1"}

        result = validate_citations_in_response(response, context, state)

        assert result is not None
        assert result.has_hallucinations
        assert "hallucination_requires_regeneration" not in state

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_MODE", "soft")
    def test_soft_mode_no_hallucinations(self) -> None:
        """In soft mode, valid citations pass without flag."""
        response = "La Legge n. 199/2025 disciplina la definizione agevolata."
        context = "La Legge 30 dicembre 2025 n. 199 disciplina la definizione agevolata."
        state: dict = {"request_id": "soft-2"}

        result = validate_citations_in_response(response, context, state)

        assert result is not None
        assert not result.has_hallucinations
        assert "hallucination_requires_regeneration" not in state


class TestHallucinationGuardStrictMode:
    """Strict mode: flag for regeneration when hallucinations found."""

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_MODE", "strict")
    def test_strict_mode_flags_regeneration(self) -> None:
        """In strict mode, hallucinations flag state for regeneration."""
        response = "La rottamazione è disciplinata dalla Legge n. 197/2022."
        context = "La Legge 30 dicembre 2025 n. 199 disciplina la definizione agevolata."
        state: dict = {"request_id": "strict-1"}

        result = validate_citations_in_response(response, context, state)

        assert result is not None
        assert result.has_hallucinations
        assert state.get("hallucination_requires_regeneration") is True
        assert len(state.get("hallucinated_citations", [])) > 0

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_MODE", "strict")
    def test_strict_mode_no_flag_when_valid(self) -> None:
        """In strict mode, valid citations do not flag regeneration."""
        response = "La Legge n. 199/2025 disciplina la definizione agevolata."
        context = "La Legge 30 dicembre 2025 n. 199 disciplina la definizione agevolata."
        state: dict = {"request_id": "strict-2"}

        result = validate_citations_in_response(response, context, state)

        assert result is not None
        assert not result.has_hallucinations
        assert "hallucination_requires_regeneration" not in state


class TestHallucinationGuardTimeout:
    """Timeout: fallback to unvalidated on slow validation."""

    def test_timeout_returns_none(self) -> None:
        """When validation exceeds timeout, None is returned."""

        def slow_fn(*args):
            time.sleep(5)
            return "should not reach"

        result = _run_with_timeout(slow_fn, "a", "b", timeout_s=0.1)
        assert result is None

    def test_fast_validation_within_timeout(self) -> None:
        """Fast validation completes within timeout."""

        def fast_fn(a, b):
            return a + b

        result = _run_with_timeout(fast_fn, "hello", " world", timeout_s=2.0)
        assert result == "hello world"

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_TIMEOUT_S", 0.001)
    @patch("app.services.llm_response.citation_validator._get_hallucination_guard")
    def test_timeout_in_pipeline_returns_none(self, mock_get_guard) -> None:
        """Pipeline returns None when guard times out."""
        mock_guard = MagicMock()

        def slow_validate(*args):
            time.sleep(1)
            return MagicMock()

        mock_guard.validate_citations.side_effect = slow_validate
        mock_get_guard.return_value = mock_guard

        state: dict = {"request_id": "timeout-1"}
        result = validate_citations_in_response("Legge 199/2025", "Legge 199/2025", state)

        assert result is None


class TestHallucinationGuardNoCitations:
    """Skip validation when no legal citations present."""

    def test_no_citations_skip_validation(self) -> None:
        """Response without citations skips validation gracefully."""
        response = "Buongiorno, come posso aiutarti oggi?"
        context = "La Legge 199/2025 disciplina la definizione agevolata."
        state: dict = {"request_id": "no-cit"}

        result = validate_citations_in_response(response, context, state)

        assert result is not None
        assert len(result.extracted_citations) == 0
        assert not result.has_hallucinations
