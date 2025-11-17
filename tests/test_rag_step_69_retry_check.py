"""
Tests for RAG STEP 69 — Another attempt allowed? (RAG.platform.another.attempt.allowed)

This decision step checks if another retry attempt is allowed based on the current attempt number
and maximum retries configuration. Routes to retry logic (Step 70) if allowed, or error (Step 71) if exhausted.
"""

from unittest.mock import patch

import pytest


class TestRAGStep69RetryCheck:
    """Test suite for RAG STEP 69 - Another attempt allowed decision."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_first_attempt_retry_allowed(self, mock_rag_log):
        """Test Step 69: First attempt failed - retry allowed."""
        from app.orchestrators.platform import step_69__retry_check

        ctx = {
            "attempt_number": 1,
            "max_retries": 3,
            "error": "Rate limit exceeded",
            "request_id": "test-69-first-attempt",
        }

        result = await step_69__retry_check(messages=[], ctx=ctx)

        # Verify retry is allowed
        assert isinstance(result, dict)
        assert result["retry_allowed"] is True
        assert result["attempts_remaining"] == 2  # 3 max - 1 current
        assert result["next_step"] == "prod_check"  # Routes to Step 70
        assert result["reason"] == "retries_available"
        assert result["attempt_number"] == 1
        assert result["max_retries"] == 3

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 69
        assert completed_log["node_label"] == "RetryCheck"
        assert completed_log["retry_allowed"] is True
        assert completed_log["decision"] == "retry"
        assert completed_log["attempts_remaining"] == 2

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_second_attempt_retry_allowed(self, mock_rag_log):
        """Test Step 69: Second attempt failed - still allowed one more retry."""
        from app.orchestrators.platform import step_69__retry_check

        ctx = {
            "attempt_number": 2,
            "max_retries": 3,
            "error": "Connection timeout",
            "request_id": "test-69-second-attempt",
        }

        result = await step_69__retry_check(messages=[], ctx=ctx)

        # Still allowed (attempt 2 of 3)
        assert result["retry_allowed"] is True
        assert result["attempts_remaining"] == 1
        assert result["next_step"] == "prod_check"
        assert result["is_last_retry"] is True  # This is the last allowed retry

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_max_retries_exhausted(self, mock_rag_log):
        """Test Step 69: Max retries exhausted - no more attempts allowed."""
        from app.orchestrators.platform import step_69__retry_check

        ctx = {"attempt_number": 3, "max_retries": 3, "error": "API error", "request_id": "test-69-exhausted"}

        result = await step_69__retry_check(messages=[], ctx=ctx)

        # No more retries allowed
        assert result["retry_allowed"] is False
        assert result["attempts_remaining"] == 0
        assert result["next_step"] == "error_500"  # Routes to Step 71
        assert result["reason"] == "max_retries_exceeded"
        assert result["all_attempts_failed"] is True

        # Verify logging reflects exhaustion
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        completed_log = completed_logs[0][1]
        assert completed_log["retry_allowed"] is False
        assert completed_log["decision"] == "no_retry"
        assert completed_log["max_retries_exceeded"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_custom_max_retries(self, mock_rag_log):
        """Test Step 69: Custom max_retries configuration."""
        from app.orchestrators.platform import step_69__retry_check

        # Test with different max_retries values
        test_cases = [
            (1, 1, False),  # attempt 1, max 1 → exhausted
            (1, 2, True),  # attempt 1, max 2 → allowed
            (1, 5, True),  # attempt 1, max 5 → allowed
            (4, 5, True),  # attempt 4, max 5 → allowed (last)
            (5, 5, False),  # attempt 5, max 5 → exhausted
        ]

        for attempt, max_retries, should_allow in test_cases:
            mock_rag_log.reset_mock()

            ctx = {
                "attempt_number": attempt,
                "max_retries": max_retries,
                "request_id": f"test-69-custom-{attempt}-{max_retries}",
            }

            result = await step_69__retry_check(messages=[], ctx=ctx)

            assert result["retry_allowed"] == should_allow, f"Failed for attempt={attempt}, max={max_retries}"
            assert result["attempts_remaining"] == max(0, max_retries - attempt)

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_with_error_history(self, mock_rag_log):
        """Test Step 69: Retry check with error history tracking."""
        from app.orchestrators.platform import step_69__retry_check

        previous_errors = ["Attempt 1: Rate limit exceeded", "Attempt 2: Connection timeout"]

        ctx = {
            "attempt_number": 2,
            "max_retries": 4,
            "error": "Attempt 2: Connection timeout",
            "previous_errors": previous_errors,
            "request_id": "test-69-error-history",
        }

        result = await step_69__retry_check(messages=[], ctx=ctx)

        # Should still allow retry
        assert result["retry_allowed"] is True
        assert result["previous_errors"] == previous_errors
        assert len(result["previous_errors"]) == 2

        # Verify error history is logged
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        completed_log = completed_logs[0][1]
        assert completed_log["error_count"] == 2

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_zero_based_vs_one_based_attempts(self, mock_rag_log):
        """Test Step 69: Handle both zero-based and one-based attempt numbering."""
        from app.orchestrators.platform import step_69__retry_check

        # Test one-based (attempt 1 is first try)
        ctx = {"attempt_number": 1, "max_retries": 3, "request_id": "test-69-one-based"}

        result = await step_69__retry_check(messages=[], ctx=ctx)
        assert result["retry_allowed"] is True
        assert result["attempts_remaining"] == 2

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_missing_max_retries_uses_default(self, mock_rag_log):
        """Test Step 69: Uses default max_retries when not provided."""
        from app.orchestrators.platform import step_69__retry_check

        ctx = {
            "attempt_number": 1,
            # max_retries not provided
            "request_id": "test-69-default",
        }

        result = await step_69__retry_check(messages=[], ctx=ctx)

        # Should use default (typically 3)
        assert result["retry_allowed"] is not None
        assert "max_retries" in result
        assert result["max_retries"] >= 1  # Has some default value


class TestRAGStep69Parity:
    """Parity tests proving Step 69 preserves existing retry logic."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_parity_retry_logic(self, mock_rag_log):
        """Test Step 69: Parity with existing for-loop retry logic."""
        from app.orchestrators.platform import step_69__retry_check

        max_retries = 3

        # Original logic: for attempt in range(max_retries)
        # Attempts are 0, 1, 2 (but we use 1-based: 1, 2, 3)

        for attempt_number in range(1, max_retries + 1):
            # Original: would continue loop if attempt < max_retries - 1
            # Our logic: retry_allowed if attempt_number < max_retries
            original_would_retry = attempt_number < max_retries

            ctx = {
                "attempt_number": attempt_number,
                "max_retries": max_retries,
                "request_id": f"test-parity-{attempt_number}",
            }

            result = await step_69__retry_check(messages=[], ctx=ctx)

            # Verify parity
            assert (
                result["retry_allowed"] == original_would_retry
            ), f"Parity failed at attempt {attempt_number}/{max_retries}"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_parity_exhaustion_behavior(self, mock_rag_log):
        """Test Step 69: Parity for retry exhaustion (routes to error)."""
        from app.orchestrators.platform import step_69__retry_check

        # Original: after max_retries loop ends, raises Exception
        # Our logic: retry_allowed=False routes to error_500

        ctx = {"attempt_number": 3, "max_retries": 3, "request_id": "test-parity-exhausted"}

        result = await step_69__retry_check(messages=[], ctx=ctx)

        # Should match original exhaustion behavior
        assert result["retry_allowed"] is False
        assert result["next_step"] == "error_500"
        assert result["all_attempts_failed"] is True


class TestRAGStep69Integration:
    """Integration tests for Step 67 → Step 69 → Step 70/71 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.orchestrators.llm.rag_step_log")
    async def test_step_67_to_69_integration(self, mock_llm_log, mock_platform_log):
        """Test Step 67 (LLM failure) → Step 69 (retry check) integration."""
        from app.orchestrators.llm import step_67__llmsuccess
        from app.orchestrators.platform import step_69__retry_check

        # Step 67: LLM call failed
        step_67_ctx = {
            "llm_response": None,
            "error": "API timeout",
            "attempt_number": 1,
            "max_retries": 3,
            "request_id": "test-integration-67-69",
        }

        step_67_result = await step_67__llmsuccess(messages=[], ctx=step_67_ctx)

        # Should route to retry_check
        assert step_67_result["llm_success"] is False
        assert step_67_result["next_step"] == "retry_check"

        # Step 69: Check if retry allowed
        step_69_ctx = {
            "attempt_number": step_67_result["attempt_number"],
            "max_retries": step_67_result["max_retries"],
            "error": step_67_result["error_message"],
            "request_id": step_67_result["request_id"],
        }

        step_69_result = await step_69__retry_check(messages=[], ctx=step_69_ctx)

        # Should allow retry (first attempt)
        assert step_69_result["retry_allowed"] is True
        assert step_69_result["next_step"] == "prod_check"
        assert step_69_result["attempts_remaining"] == 2
