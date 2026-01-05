"""TDD Tests for DEV-238: Detailed Logging for Reasoning Traces.

Tests for structured logging of reasoning traces with mandatory context fields.

Coverage Target: 90%+ for new code.
"""

from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Sample State Data for Testing
# =============================================================================

SAMPLE_STATE = {
    "user_id": "user_123",
    "session_id": "session_456",
    "request_id": "req_789",
    "reasoning_type": "cot",
    "reasoning_trace": {"step1": "Analysis", "step2": "Conclusion"},
    "model_used": "claude-3-sonnet",
    "query_complexity": "complex",
}

SAMPLE_TOT_STATE = {
    "user_id": "user_123",
    "session_id": "session_456",
    "request_id": "req_789",
    "reasoning_type": "tot",
    "reasoning_trace": {
        "hypotheses": [
            {"id": "h1", "confidence": 0.85},
            {"id": "h2", "confidence": 0.72},
        ],
        "selected": "h1",
    },
    "model_used": "claude-3-opus",
    "query_complexity": "multi_domain",
}


# =============================================================================
# Log Reasoning Trace Recorded Tests
# =============================================================================


class TestLogReasoningTraceRecorded:
    """Tests for reasoning_trace_recorded log event."""

    def test_log_reasoning_trace_includes_mandatory_fields(self):
        """Log should include all mandatory context fields."""
        from app.services.reasoning_trace_logger import log_reasoning_trace_recorded

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_reasoning_trace_recorded(SAMPLE_STATE, elapsed_ms=150.5)

            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args[1]

            # Mandatory fields from Logging Standards
            assert call_kwargs["user_id"] == "user_123"
            assert call_kwargs["session_id"] == "session_456"
            assert call_kwargs["operation"] == "reasoning_trace"
            assert call_kwargs["resource_id"] == "req_789"

    def test_log_reasoning_trace_includes_reasoning_fields(self):
        """Log should include reasoning-specific fields."""
        from app.services.reasoning_trace_logger import log_reasoning_trace_recorded

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_reasoning_trace_recorded(SAMPLE_STATE, elapsed_ms=150.5)

            call_kwargs = mock_logger.info.call_args[1]

            assert call_kwargs["reasoning_type"] == "cot"
            assert call_kwargs["model_used"] == "claude-3-sonnet"
            assert call_kwargs["query_complexity"] == "complex"
            assert call_kwargs["latency_ms"] == 150.5

    def test_log_reasoning_trace_truncates_long_traces(self):
        """Reasoning trace should be truncated for logging."""
        from app.services.reasoning_trace_logger import log_reasoning_trace_recorded

        long_state = SAMPLE_STATE.copy()
        long_state["reasoning_trace"] = {"data": "A" * 2000}

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_reasoning_trace_recorded(long_state, elapsed_ms=100.0)

            call_kwargs = mock_logger.info.call_args[1]

            # Trace should be truncated
            assert len(call_kwargs["reasoning_trace"]) <= 1100  # 1000 + "[truncated]"
            assert "[truncated]" in call_kwargs["reasoning_trace"]

    def test_log_reasoning_trace_handles_none_trace(self):
        """Should handle None reasoning trace gracefully."""
        from app.services.reasoning_trace_logger import log_reasoning_trace_recorded

        state_no_trace = SAMPLE_STATE.copy()
        state_no_trace["reasoning_trace"] = None

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_reasoning_trace_recorded(state_no_trace, elapsed_ms=100.0)

            call_kwargs = mock_logger.info.call_args[1]
            assert call_kwargs["reasoning_trace"] == ""

    def test_log_reasoning_trace_handles_missing_optional_fields(self):
        """Should handle missing optional fields with defaults."""
        from app.services.reasoning_trace_logger import log_reasoning_trace_recorded

        minimal_state = {
            "request_id": "req_123",
        }

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_reasoning_trace_recorded(minimal_state, elapsed_ms=50.0)

            call_kwargs = mock_logger.info.call_args[1]

            # Should use None for missing fields
            assert call_kwargs["user_id"] is None
            assert call_kwargs["session_id"] is None
            assert call_kwargs["reasoning_type"] is None


# =============================================================================
# Log Reasoning Trace Failed Tests
# =============================================================================


class TestLogReasoningTraceFailed:
    """Tests for reasoning_trace_failed log event."""

    def test_log_reasoning_trace_failed_includes_error_info(self):
        """Log should include error details."""
        from app.services.reasoning_trace_logger import log_reasoning_trace_failed

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_reasoning_trace_failed(
                state=SAMPLE_STATE,
                error_type="JSONDecodeError",
                error_message="Expecting value: line 1",
                content_sample="Invalid JSON content here...",
            )

            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args[1]

            assert call_kwargs["error_type"] == "JSONDecodeError"
            assert call_kwargs["error_message"] == "Expecting value: line 1"
            assert "Invalid JSON" in call_kwargs["content_sample"]

    def test_log_reasoning_trace_failed_includes_mandatory_fields(self):
        """Failed log should include mandatory context fields."""
        from app.services.reasoning_trace_logger import log_reasoning_trace_failed

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_reasoning_trace_failed(
                state=SAMPLE_STATE,
                error_type="ParseError",
                error_message="Failed to parse",
                content_sample="sample",
            )

            call_kwargs = mock_logger.warning.call_args[1]

            # Mandatory fields
            assert call_kwargs["user_id"] == "user_123"
            assert call_kwargs["session_id"] == "session_456"
            assert call_kwargs["operation"] == "reasoning_trace_parse"
            assert call_kwargs["resource_id"] == "req_789"

    def test_log_reasoning_trace_failed_truncates_content_sample(self):
        """Content sample should be truncated."""
        from app.services.reasoning_trace_logger import log_reasoning_trace_failed

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_reasoning_trace_failed(
                state=SAMPLE_STATE,
                error_type="JSONDecodeError",
                error_message="Error",
                content_sample="X" * 500,
            )

            call_kwargs = mock_logger.warning.call_args[1]

            # Content sample should be truncated to ~200 chars
            assert len(call_kwargs["content_sample"]) <= 220


# =============================================================================
# Log Dual Reasoning Generated Tests
# =============================================================================


class TestLogDualReasoningGenerated:
    """Tests for dual_reasoning_generated log event."""

    def test_log_dual_reasoning_includes_both_traces(self):
        """Log should include both internal and public reasoning."""
        from app.services.reasoning_trace_logger import log_dual_reasoning_generated

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_dual_reasoning_generated(
                state=SAMPLE_STATE,
                internal_trace="Detailed analysis with technical terms...",
                public_reasoning="User-friendly summary of findings.",
                elapsed_ms=200.0,
            )

            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args[1]

            assert "Detailed analysis" in call_kwargs["internal_trace"]
            assert "User-friendly" in call_kwargs["public_reasoning"]

    def test_log_dual_reasoning_includes_mandatory_fields(self):
        """Dual reasoning log should include mandatory context fields."""
        from app.services.reasoning_trace_logger import log_dual_reasoning_generated

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_dual_reasoning_generated(
                state=SAMPLE_STATE,
                internal_trace="internal",
                public_reasoning="public",
                elapsed_ms=100.0,
            )

            call_kwargs = mock_logger.info.call_args[1]

            assert call_kwargs["user_id"] == "user_123"
            assert call_kwargs["session_id"] == "session_456"
            assert call_kwargs["operation"] == "dual_reasoning"
            assert call_kwargs["latency_ms"] == 100.0


# =============================================================================
# Log ToT Hypothesis Evaluated Tests
# =============================================================================


class TestLogToTHypothesisEvaluated:
    """Tests for tot_hypothesis_evaluated log event."""

    def test_log_tot_hypothesis_includes_hypothesis_details(self):
        """Log should include hypothesis evaluation details."""
        from app.services.reasoning_trace_logger import log_tot_hypothesis_evaluated

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_tot_hypothesis_evaluated(
                state=SAMPLE_TOT_STATE,
                hypothesis_id="h1",
                probability=0.85,
                source_weight_score=0.92,
                selected=True,
            )

            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args[1]

            assert call_kwargs["hypothesis_id"] == "h1"
            assert call_kwargs["probability"] == 0.85
            assert call_kwargs["source_weight_score"] == 0.92
            assert call_kwargs["selected"] is True

    def test_log_tot_hypothesis_includes_mandatory_fields(self):
        """ToT hypothesis log should include mandatory context fields."""
        from app.services.reasoning_trace_logger import log_tot_hypothesis_evaluated

        with patch("app.services.reasoning_trace_logger.logger") as mock_logger:
            log_tot_hypothesis_evaluated(
                state=SAMPLE_TOT_STATE,
                hypothesis_id="h2",
                probability=0.72,
                source_weight_score=0.65,
                selected=False,
            )

            call_kwargs = mock_logger.info.call_args[1]

            assert call_kwargs["user_id"] == "user_123"
            assert call_kwargs["session_id"] == "session_456"
            assert call_kwargs["operation"] == "tot_hypothesis_evaluation"
            assert call_kwargs["resource_id"] == "req_789"


# =============================================================================
# Truncation Helper Tests
# =============================================================================


class TestTruncateForLog:
    """Tests for the truncation helper function."""

    def test_truncate_short_text_unchanged(self):
        """Short text should not be truncated."""
        from app.services.reasoning_trace_logger import truncate_for_log

        short_text = "Short text"
        result = truncate_for_log(short_text, max_length=100)

        assert result == short_text

    def test_truncate_long_text_adds_marker(self):
        """Long text should be truncated with marker."""
        from app.services.reasoning_trace_logger import truncate_for_log

        long_text = "A" * 200
        result = truncate_for_log(long_text, max_length=100)

        assert len(result) <= 115  # 100 + "...[truncated]"
        assert "[truncated]" in result

    def test_truncate_none_returns_empty(self):
        """None input should return empty string."""
        from app.services.reasoning_trace_logger import truncate_for_log

        result = truncate_for_log(None, max_length=100)

        assert result == ""

    def test_truncate_dict_converts_to_string(self):
        """Dict input should be converted to string first."""
        from app.services.reasoning_trace_logger import truncate_for_log

        dict_input = {"key": "value"}
        result = truncate_for_log(dict_input, max_length=100)

        assert "key" in result
        assert "value" in result


# =============================================================================
# Integration Tests
# =============================================================================


class TestReasoningLoggerIntegration:
    """Integration tests for reasoning trace logger."""

    def test_logger_uses_structlog(self):
        """Logger should be a structlog logger."""
        from app.services.reasoning_trace_logger import logger

        # Logger should have structlog characteristics
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_all_log_functions_exist(self):
        """All required log functions should be importable."""
        from app.services.reasoning_trace_logger import (
            log_dual_reasoning_generated,
            log_reasoning_trace_failed,
            log_reasoning_trace_recorded,
            log_tot_hypothesis_evaluated,
        )

        assert callable(log_reasoning_trace_recorded)
        assert callable(log_reasoning_trace_failed)
        assert callable(log_dual_reasoning_generated)
        assert callable(log_tot_hypothesis_evaluated)
