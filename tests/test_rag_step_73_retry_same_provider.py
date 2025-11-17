"""
Tests for RAG STEP 73 — Retry same provider (RAG.providers.retry.same.provider)

This process step retries the LLM call using the same provider (or failover provider if set).
It increments the attempt counter and loops back to the LLM call step.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep73RetrySameProvider:
    """Test suite for RAG STEP 73 - Retry same provider."""

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_73_retry_with_same_provider(self, mock_rag_log):
        """Test Step 73: Retry with same provider."""
        from app.orchestrators.providers import step_73__retry_same

        # Mock current provider
        mock_provider = MagicMock()
        mock_provider.provider_type.value = "openai"
        mock_provider.model = "gpt-4"

        ctx = {
            "provider": mock_provider,
            "attempt_number": 1,
            "max_retries": 3,
            "messages": [{"role": "user", "content": "test"}],
            "error": "Rate limit exceeded",
            "request_id": "test-73-retry",
        }

        result = await step_73__retry_same(messages=[], ctx=ctx)

        # Verify retry setup
        assert isinstance(result, dict)
        assert result["retry_initiated"] is True
        assert result["attempt_number"] == 2  # Incremented from 1 to 2
        assert result["provider"] == mock_provider  # Same provider
        assert result["next_step"] == "llm_call"  # Routes back to LLM call
        assert result["provider_type"] == "openai"
        assert result["model"] == "gpt-4"

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 73
        assert completed_log["node_label"] == "RetrySame"
        assert completed_log["retry_initiated"] is True
        assert completed_log["attempt_number"] == 2

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_73_retry_with_failover_provider(self, mock_rag_log):
        """Test Step 73: Retry with failover provider (from Step 72)."""
        from app.orchestrators.providers import step_73__retry_same

        # Mock failover provider
        mock_failover = MagicMock()
        mock_failover.provider_type.value = "anthropic"
        mock_failover.model = "claude-3-sonnet-20241022"

        ctx = {
            "provider": mock_failover,
            "attempt_number": 2,
            "max_retries": 3,
            "messages": [{"role": "user", "content": "test"}],
            "is_failover": True,
            "request_id": "test-73-failover",
        }

        result = await step_73__retry_same(messages=[], ctx=ctx)

        # Should retry with failover provider
        assert result["retry_initiated"] is True
        assert result["attempt_number"] == 3  # Incremented from 2 to 3
        assert result["provider"] == mock_failover
        assert result["is_failover"] is True
        assert result["provider_type"] == "anthropic"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_73_increments_attempt_number(self, mock_rag_log):
        """Test Step 73: Correctly increments attempt number."""
        from app.orchestrators.providers import step_73__retry_same

        mock_provider = MagicMock()

        test_cases = [
            (0, 1),  # 0 → 1
            (1, 2),  # 1 → 2
            (2, 3),  # 2 → 3
            (3, 4),  # 3 → 4
        ]

        for current_attempt, expected_attempt in test_cases:
            mock_rag_log.reset_mock()

            ctx = {
                "provider": mock_provider,
                "attempt_number": current_attempt,
                "max_retries": 5,
                "request_id": f"test-73-attempt-{current_attempt}",
            }

            result = await step_73__retry_same(messages=[], ctx=ctx)

            assert result["retry_initiated"] is True
            assert (
                result["attempt_number"] == expected_attempt
            ), f"Failed for current={current_attempt}, expected={expected_attempt}"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_73_preserves_context(self, mock_rag_log):
        """Test Step 73: Preserves all necessary context for retry."""
        from app.orchestrators.providers import step_73__retry_same

        mock_provider = MagicMock()
        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Second message"},
        ]
        previous_errors = ["Attempt 1: Rate limit"]

        ctx = {
            "provider": mock_provider,
            "attempt_number": 1,
            "max_retries": 3,
            "messages": messages,
            "previous_errors": previous_errors,
            "error": "Attempt 1: Rate limit",
            "request_id": "test-73-context",
        }

        result = await step_73__retry_same(messages=[], ctx=ctx)

        # Verify context preservation
        assert result["retry_initiated"] is True
        assert result["messages"] == messages
        assert result["previous_errors"] == previous_errors
        assert result["max_retries"] == 3
        assert result["request_id"] == "test-73-context"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_73_routes_to_llm_call(self, mock_rag_log):
        """Test Step 73: Always routes to LLM call step."""
        from app.orchestrators.providers import step_73__retry_same

        mock_provider = MagicMock()

        ctx = {"provider": mock_provider, "attempt_number": 1, "max_retries": 3, "request_id": "test-73-route"}

        result = await step_73__retry_same(messages=[], ctx=ctx)

        # Should always route to llm_call
        assert result["next_step"] == "llm_call"
        assert result["retry_initiated"] is True


class TestRAGStep73Parity:
    """Parity tests proving Step 73 preserves existing retry logic."""

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_73_parity_continue_loop(self, mock_rag_log):
        """Test Step 73: Parity with existing continue loop logic."""
        from app.orchestrators.providers import step_73__retry_same

        # Original logic from graph.py:799
        # continue  (continues the for loop to retry)
        mock_provider = MagicMock()

        ctx = {"provider": mock_provider, "attempt_number": 1, "max_retries": 3, "request_id": "test-parity-continue"}

        result = await step_73__retry_same(messages=[], ctx=ctx)

        # Original: continue loop to next iteration
        # Our: increment attempt and route back to llm_call
        assert result["retry_initiated"] is True
        assert result["attempt_number"] == 2  # Next iteration
        assert result["next_step"] == "llm_call"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_73_parity_attempt_increment(self, mock_rag_log):
        """Test Step 73: Parity for attempt counter increment."""
        from app.orchestrators.providers import step_73__retry_same

        # Original: for attempt in range(max_retries) → next iteration
        # Our: increment attempt_number
        mock_provider = MagicMock()

        for original_attempt in range(3):
            mock_rag_log.reset_mock()

            # Our 1-based indexing
            our_attempt = original_attempt + 1

            ctx = {
                "provider": mock_provider,
                "attempt_number": our_attempt,
                "max_retries": 3,
                "request_id": f"test-parity-{our_attempt}",
            }

            result = await step_73__retry_same(messages=[], ctx=ctx)

            # Next iteration in original loop
            original_attempt + 1
            next_ours = our_attempt + 1

            assert result["attempt_number"] == next_ours
            assert result["retry_initiated"] is True


class TestRAGStep73Integration:
    """Integration tests for Step 70/72 → Step 73 → LLM call flow."""

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_70_to_73_integration(self, mock_rag_log):
        """Test Step 70 (retry same) → Step 73 (retry) integration."""
        from app.core.config import Environment
        from app.orchestrators.platform import step_70__prod_check
        from app.orchestrators.providers import step_73__retry_same

        # Step 70: NOT production or NOT last retry
        step_70_ctx = {
            "environment": Environment.DEVELOPMENT,
            "attempt_number": 1,
            "max_retries": 3,
            "is_last_retry": False,
            "request_id": "test-integration-70-73",
        }

        step_70_result = await step_70__prod_check(messages=[], ctx=step_70_ctx)

        # Should route to retry_same_provider
        assert step_70_result["use_failover"] is False
        assert step_70_result["next_step"] == "retry_same_provider"

        # Step 73: Retry same provider
        mock_provider = MagicMock()
        mock_provider.provider_type.value = "openai"
        mock_provider.model = "gpt-4"

        step_73_ctx = {
            "provider": mock_provider,
            "attempt_number": step_70_result["attempt_number"],
            "max_retries": step_70_result["max_retries"],
            "messages": [{"role": "user", "content": "test"}],
            "request_id": step_70_result["request_id"],
        }

        step_73_result = await step_73__retry_same(messages=[], ctx=step_73_ctx)

        # Should increment and retry
        assert step_73_result["retry_initiated"] is True
        assert step_73_result["attempt_number"] == 2  # Incremented
        assert step_73_result["next_step"] == "llm_call"

    @pytest.mark.asyncio
    @patch("app.core.llm.factory.get_llm_provider")
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_72_to_73_failover_integration(self, mock_rag_log, mock_get_provider):
        """Test Step 72 (failover) → Step 73 (retry with failover) integration."""
        from app.orchestrators.providers import step_72__get_failover_provider, step_73__retry_same

        # Step 72: Get failover provider
        mock_failover = MagicMock()
        mock_failover.provider_type.value = "anthropic"
        mock_failover.model = "claude-3-sonnet-20241022"
        mock_get_provider.return_value = mock_failover

        step_72_ctx = {
            "messages": [{"role": "user", "content": "test"}],
            "max_cost_eur": 0.10,
            "attempt_number": 2,
            "max_retries": 3,
            "request_id": "test-integration-72-73",
        }

        step_72_result = await step_72__get_failover_provider(messages=[], ctx=step_72_ctx)

        # Should get failover provider
        assert step_72_result["provider_obtained"] is True
        assert step_72_result["is_failover"] is True

        # Step 73: Retry with failover provider
        step_73_ctx = {
            "provider": step_72_result["provider"],
            "attempt_number": step_72_result["attempt_number"],
            "max_retries": step_72_result["max_retries"],
            "messages": step_72_ctx["messages"],
            "is_failover": step_72_result["is_failover"],
            "request_id": step_72_result["request_id"],
        }

        step_73_result = await step_73__retry_same(messages=[], ctx=step_73_ctx)

        # Should retry with failover provider
        assert step_73_result["retry_initiated"] is True
        assert step_73_result["attempt_number"] == 3
        assert step_73_result["provider"] == mock_failover
        assert step_73_result["is_failover"] is True
        assert step_73_result["next_step"] == "llm_call"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_73_full_retry_cycle(self, mock_rag_log):
        """Test Step 73: Full retry cycle simulation."""
        from app.orchestrators.providers import step_73__retry_same

        mock_provider = MagicMock()
        max_retries = 3

        # Simulate multiple retry attempts
        for attempt in range(1, max_retries):
            mock_rag_log.reset_mock()

            ctx = {
                "provider": mock_provider,
                "attempt_number": attempt,
                "max_retries": max_retries,
                "messages": [{"role": "user", "content": "test"}],
                "error": f"Attempt {attempt} failed",
                "request_id": f"test-cycle-{attempt}",
            }

            result = await step_73__retry_same(messages=[], ctx=ctx)

            # Each retry should increment and route back
            assert result["retry_initiated"] is True
            assert result["attempt_number"] == attempt + 1
            assert result["next_step"] == "llm_call"
