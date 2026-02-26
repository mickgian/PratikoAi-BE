"""DEV-389: Tests for Hallucination Guard soft/strict mode and timeout integration.

Tests cover:
- Soft mode: log and continue
- Strict mode: flag regeneration
- Timeout guard with ThreadPoolExecutor
- Error handling (graceful degradation)
- Empty/missing input handling
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_response.citation_validator import (
    _run_with_timeout,
    validate_citations_in_response,
)


def _make_validation_result(
    *,
    has_hallucinations: bool = False,
    hallucinated_citations: list | None = None,
    valid_citations: list | None = None,
    extracted_citations: list | None = None,
    hallucination_rate: float = 0.0,
) -> MagicMock:
    """Create a mock CitationValidationResult with controlled attributes."""
    result = MagicMock()
    result.has_hallucinations = has_hallucinations
    result.hallucinated_citations = hallucinated_citations or []
    result.valid_citations = valid_citations or []
    result.extracted_citations = extracted_citations or []
    result.hallucination_rate = hallucination_rate
    return result


# ------------------------------------------------------------------ #
# Soft mode
# ------------------------------------------------------------------ #
class TestHallucinationGuardSoftMode:
    """Soft mode: log warning, continue with flagged response."""

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_MODE", "soft")
    @patch("app.services.llm_response.citation_validator._get_hallucination_guard")
    def test_soft_mode_with_hallucinations(self, mock_get_guard) -> None:
        """Hallucinated citations logged but no regeneration flag."""
        mock_guard = MagicMock()
        mock_guard.validate_citations.return_value = _make_validation_result(
            has_hallucinations=True,
            hallucinated_citations=["Legge 197/2022"],
            hallucination_rate=1.0,
        )
        mock_get_guard.return_value = mock_guard

        state: dict = {"request_id": "soft-1", "session_id": "s-1"}
        result = validate_citations_in_response(
            "La Legge n. 197/2022 disciplina X.",
            "Contesto KB senza tale legge.",
            state,
        )

        assert result is not None
        assert result.has_hallucinations is True
        assert "hallucination_requires_regeneration" not in state

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_MODE", "soft")
    @patch("app.services.llm_response.citation_validator._get_hallucination_guard")
    def test_soft_mode_no_hallucinations(self, mock_get_guard) -> None:
        """Valid citations pass cleanly in soft mode."""
        mock_guard = MagicMock()
        mock_guard.validate_citations.return_value = _make_validation_result(
            has_hallucinations=False,
            extracted_citations=["Legge 199/2025"],
            valid_citations=["Legge 199/2025"],
        )
        mock_get_guard.return_value = mock_guard

        state: dict = {"request_id": "soft-2"}
        result = validate_citations_in_response(
            "La Legge n. 199/2025 disciplina la definizione.",
            "La Legge 30 dicembre 2025 n. 199 disciplina la definizione agevolata.",
            state,
        )

        assert result is not None
        assert result.has_hallucinations is False
        assert "hallucination_requires_regeneration" not in state


# ------------------------------------------------------------------ #
# Strict mode
# ------------------------------------------------------------------ #
class TestHallucinationGuardStrictMode:
    """Strict mode: flag for regeneration when hallucinations found."""

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_MODE", "strict")
    @patch("app.services.llm_response.citation_validator._get_hallucination_guard")
    def test_strict_mode_flags_regeneration(self, mock_get_guard) -> None:
        mock_guard = MagicMock()
        mock_guard.validate_citations.return_value = _make_validation_result(
            has_hallucinations=True,
            hallucinated_citations=["Legge 197/2022"],
            hallucination_rate=1.0,
        )
        mock_get_guard.return_value = mock_guard

        state: dict = {"request_id": "strict-1"}
        result = validate_citations_in_response(
            "La Legge n. 197/2022.",
            "Contesto KB diverso.",
            state,
        )

        assert result is not None
        assert result.has_hallucinations is True
        assert state["hallucination_requires_regeneration"] is True
        assert len(state["hallucinated_citations"]) > 0

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_MODE", "strict")
    @patch("app.services.llm_response.citation_validator._get_hallucination_guard")
    def test_strict_mode_no_flag_when_valid(self, mock_get_guard) -> None:
        mock_guard = MagicMock()
        mock_guard.validate_citations.return_value = _make_validation_result(
            has_hallucinations=False,
            extracted_citations=["Legge 199/2025"],
            valid_citations=["Legge 199/2025"],
        )
        mock_get_guard.return_value = mock_guard

        state: dict = {"request_id": "strict-2"}
        result = validate_citations_in_response(
            "La Legge n. 199/2025.",
            "La Legge 30 dicembre 2025 n. 199.",
            state,
        )

        assert result is not None
        assert "hallucination_requires_regeneration" not in state


# ------------------------------------------------------------------ #
# Timeout
# ------------------------------------------------------------------ #
class TestHallucinationGuardTimeout:
    """Timeout: fallback to unvalidated on slow validation."""

    def test_timeout_returns_none(self) -> None:
        def slow_fn(*args):
            time.sleep(5)
            return "unreachable"

        result = _run_with_timeout(slow_fn, "a", "b", timeout_s=0.1)
        assert result is None

    def test_fast_fn_within_timeout(self) -> None:
        def fast_fn(a, b):
            return a + b

        result = _run_with_timeout(fast_fn, "hello", " world", timeout_s=2.0)
        assert result == "hello world"

    @patch("app.services.llm_response.citation_validator.HALLUCINATION_GUARD_TIMEOUT_S", 0.001)
    @patch("app.services.llm_response.citation_validator._get_hallucination_guard")
    def test_timeout_in_pipeline_returns_none(self, mock_get_guard) -> None:
        mock_guard = MagicMock()

        def slow_validate(*args):
            time.sleep(1)
            return MagicMock()

        mock_guard.validate_citations.side_effect = slow_validate
        mock_get_guard.return_value = mock_guard

        state: dict = {"request_id": "timeout-1"}
        result = validate_citations_in_response("Legge 199/2025", "Legge 199/2025", state)

        assert result is None

    def test_timeout_uses_default_when_none(self) -> None:
        """When timeout_s is None, falls back to module default."""

        def instant_fn():
            return 42

        result = _run_with_timeout(instant_fn, timeout_s=None)
        assert result == 42


# ------------------------------------------------------------------ #
# Empty / missing inputs
# ------------------------------------------------------------------ #
class TestHallucinationGuardInputValidation:
    """Test empty/missing input handling."""

    def test_empty_response_skips(self) -> None:
        state: dict = {"request_id": "empty-1"}
        result = validate_citations_in_response("", "Some context", state)
        assert result is None

    def test_empty_context_skips(self) -> None:
        state: dict = {"request_id": "empty-2"}
        result = validate_citations_in_response("Some response", "", state)
        assert result is None

    def test_both_empty_skips(self) -> None:
        state: dict = {"request_id": "empty-3"}
        result = validate_citations_in_response("", "", state)
        assert result is None


# ------------------------------------------------------------------ #
# No citations in response
# ------------------------------------------------------------------ #
class TestHallucinationGuardNoCitations:
    """Test response with no legal citations."""

    @patch("app.services.llm_response.citation_validator._get_hallucination_guard")
    def test_no_citations_returns_clean_result(self, mock_get_guard) -> None:
        mock_guard = MagicMock()
        mock_guard.validate_citations.return_value = _make_validation_result(
            has_hallucinations=False,
            extracted_citations=[],
        )
        mock_get_guard.return_value = mock_guard

        state: dict = {"request_id": "no-cit"}
        result = validate_citations_in_response(
            "Buongiorno, come posso aiutarti?",
            "Contesto KB con leggi varie.",
            state,
        )

        assert result is not None
        assert not result.has_hallucinations


# ------------------------------------------------------------------ #
# Error handling
# ------------------------------------------------------------------ #
class TestHallucinationGuardErrorHandling:
    """Test graceful degradation on errors."""

    @patch("app.services.llm_response.citation_validator._get_hallucination_guard")
    def test_guard_exception_returns_none(self, mock_get_guard) -> None:
        """Exception in guard does not break the pipeline."""
        mock_guard = MagicMock()
        mock_guard.validate_citations.side_effect = RuntimeError("Unexpected error")
        mock_get_guard.return_value = mock_guard

        state: dict = {"request_id": "error-1"}
        result = validate_citations_in_response(
            "La Legge 199/2025 disciplina X.",
            "Contesto KB.",
            state,
        )

        assert result is None

    @patch("app.services.llm_response.citation_validator._get_hallucination_guard")
    def test_guard_import_error_returns_none(self, mock_get_guard) -> None:
        """Import error in lazy loading is caught."""
        mock_get_guard.side_effect = ImportError("Module not found")

        state: dict = {"request_id": "error-2"}
        result = validate_citations_in_response(
            "La Legge 199/2025.",
            "Contesto.",
            state,
        )

        assert result is None
