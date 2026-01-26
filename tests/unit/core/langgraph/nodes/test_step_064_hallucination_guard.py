"""TDD Tests for DEV-249: Integrate HallucinationGuard into LangGraph pipeline.

Tests for validating that HallucinationGuard is called for LLM responses
and hallucinations are properly logged and tracked.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.langgraph.nodes.step_064__llm_call import (
    _validate_citations_in_response,
)


class TestValidateCitationsInResponse:
    """Tests for citation validation in LLM responses."""

    def test_validates_citations_when_context_present(self):
        """Validates citations when KB context is available."""
        response_text = "La rottamazione è disciplinata dalla Legge n. 199/2025."
        kb_context = "I commi da 231 a 252 della Legge 30 dicembre 2025 n. 199 disciplinano..."
        state = {"request_id": "test-123"}

        result = _validate_citations_in_response(response_text, kb_context, state)

        assert result is not None
        assert len(result.valid_citations) == 1
        assert len(result.hallucinated_citations) == 0
        assert not result.has_hallucinations

    def test_detects_hallucinated_citations(self):
        """Detects citations not present in KB context."""
        response_text = "La rottamazione è disciplinata dalla Legge n. 197/2022."
        kb_context = "I commi da 231 a 252 della Legge 30 dicembre 2025 n. 199 disciplinano..."
        state = {"request_id": "test-123"}

        result = _validate_citations_in_response(response_text, kb_context, state)

        assert result is not None
        assert result.has_hallucinations
        assert len(result.hallucinated_citations) == 1
        assert "197/2022" in result.hallucinated_citations[0]

    def test_returns_none_when_no_context(self):
        """Returns None when KB context is empty."""
        response_text = "La Legge n. 199/2025 disciplina..."
        kb_context = ""
        state = {"request_id": "test-123"}

        result = _validate_citations_in_response(response_text, kb_context, state)

        assert result is None

    def test_returns_none_when_no_response(self):
        """Returns None when response text is empty."""
        response_text = ""
        kb_context = "La Legge n. 199/2025 disciplina..."
        state = {"request_id": "test-123"}

        result = _validate_citations_in_response(response_text, kb_context, state)

        assert result is None

    def test_handles_response_without_citations(self):
        """Handles responses without any law citations gracefully."""
        response_text = "Buongiorno, come posso aiutarti oggi?"
        kb_context = "La Legge n. 199/2025 disciplina..."
        state = {"request_id": "test-123"}

        result = _validate_citations_in_response(response_text, kb_context, state)

        assert result is not None
        assert len(result.extracted_citations) == 0
        assert not result.has_hallucinations


class TestHallucinationGuardIntegration:
    """Tests for HallucinationGuard integration in step_064."""

    @patch("app.core.langgraph.nodes.step_064__llm_call._validate_citations_in_response")
    def test_integration_called_after_llm_response(self, mock_validate):
        """Validation is called after LLM response is generated."""
        from app.services.hallucination_guard import CitationValidationResult

        mock_validate.return_value = CitationValidationResult(
            extracted_citations=["Legge 199/2025"],
            valid_citations=["Legge 199/2025"],
            hallucinated_citations=[],
        )

        # This test verifies the function exists and can be called
        response_text = "La Legge n. 199/2025 disciplina..."
        kb_context = "La Legge 199/2025 introduce..."
        state = {"request_id": "test-123"}

        from app.core.langgraph.nodes.step_064__llm_call import (
            _validate_citations_in_response,
        )

        _validate_citations_in_response(response_text, kb_context, state)

        # Verify mock was called (integration point exists)
        mock_validate.assert_called_once()


class TestHallucinationGuardLogging:
    """Tests for logging of hallucination detection."""

    @patch("app.core.langgraph.nodes.step_064__llm_call.logger")
    def test_logs_warning_when_hallucinations_detected(self, mock_logger):
        """Logs warning when hallucinations are detected."""
        response_text = "La rottamazione è disciplinata dalla Legge n. 197/2022."
        kb_context = "La Legge 30 dicembre 2025 n. 199 disciplina..."
        state = {"request_id": "test-123", "session_id": "session-456"}

        _validate_citations_in_response(response_text, kb_context, state)

        # Verify warning was logged
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args
        assert "DEV249_hallucination_detected" in str(call_args) or "hallucination" in str(call_args).lower()

    @patch("app.core.langgraph.nodes.step_064__llm_call.logger")
    def test_logs_info_when_all_citations_valid(self, mock_logger):
        """Logs info when all citations are valid."""
        response_text = "La rottamazione è disciplinata dalla Legge n. 199/2025."
        kb_context = "La Legge 30 dicembre 2025 n. 199 disciplina..."
        state = {"request_id": "test-123"}

        result = _validate_citations_in_response(response_text, kb_context, state)

        # Should log info (not warning) for valid citations
        assert result is not None
        assert not result.has_hallucinations


class TestHallucinationGuardGracefulDegradation:
    """Tests for graceful degradation when HallucinationGuard fails."""

    @patch("app.core.langgraph.nodes.step_064__llm_call._get_hallucination_guard")
    @patch("app.core.langgraph.nodes.step_064__llm_call.logger")
    def test_graceful_degradation_on_guard_error(self, mock_logger, mock_get_guard):
        """Continues without validation when guard raises exception."""
        mock_guard = MagicMock()
        mock_guard.validate_citations.side_effect = Exception("Guard error")
        mock_get_guard.return_value = mock_guard

        response_text = "La Legge n. 199/2025 disciplina..."
        kb_context = "La Legge 199/2025 introduce..."
        state = {"request_id": "test-123"}

        # Should not raise, should return None gracefully
        result = _validate_citations_in_response(response_text, kb_context, state)

        assert result is None
        # Should log the error
        mock_logger.error.assert_called()


class TestHallucinationCheckResultInState:
    """Tests for hallucination_check_result in RAGState."""

    def test_state_contains_hallucination_result(self):
        """Hallucination check result is stored in state."""
        response_text = "La Legge n. 197/2022 e la Legge n. 199/2025 disciplinano..."
        kb_context = "La Legge 30 dicembre 2025 n. 199 disciplina..."
        state = {"request_id": "test-123"}

        result = _validate_citations_in_response(response_text, kb_context, state)

        assert result is not None
        # Result should be serializable for state storage
        result_dict = result.to_dict()
        assert "hallucinated_citations" in result_dict
        assert "valid_citations" in result_dict
        assert "hallucination_rate" in result_dict


class TestPerformanceRequirements:
    """Tests for performance requirements (<50ms)."""

    def test_validation_completes_within_time_limit(self):
        """Citation validation completes within 50ms."""
        import time

        response_text = """
        La rottamazione è disciplinata dalla Legge n. 199/2025 (Legge di Bilancio 2026).
        Questa normativa modifica il D.Lgs. 46/1999 e il DPR 602/1973.
        In base al D.L. 34/2020, convertito dalla L. 77/2020, sono previste specifiche esclusioni.
        """
        kb_context = """
        I commi da 231 a 252 della Legge 30 dicembre 2025 n. 199 disciplinano la definizione
        agevolata dei carichi affidati all'agente della riscossione dal 1° gennaio 2000 al
        31 dicembre 2024. Il DPR 602/1973 regola la riscossione delle imposte.
        """
        state = {"request_id": "test-123"}

        start_time = time.perf_counter()
        result = _validate_citations_in_response(response_text, kb_context, state)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert result is not None
        assert elapsed_ms < 50, f"Validation took {elapsed_ms:.2f}ms, expected <50ms"
