"""
Tests for RAG STEP 70 — Prod environment and last retry? (RAG.platform.prod.environment.and.last.retry)

This decision step checks if we're in production environment AND on the last retry attempt.
If both conditions are true, routes to failover provider (Step 72), otherwise retry same provider (Step 73).
"""

from unittest.mock import patch

import pytest

from app.core.config import Environment


class TestRAGStep70ProdCheck:
    """Test suite for RAG STEP 70 - Prod environment and last retry decision."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_production_and_last_retry(self, mock_rag_log):
        """Test Step 70: Production environment AND last retry - routes to failover."""
        from app.orchestrators.platform import step_70__prod_check

        ctx = {
            "environment": Environment.PRODUCTION,
            "attempt_number": 2,
            "max_retries": 3,
            "is_last_retry": True,
            "request_id": "test-70-prod-last",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        # Should route to failover (Step 72)
        assert isinstance(result, dict)
        assert result["is_production"] is True
        assert result["is_last_retry"] is True
        assert result["use_failover"] is True
        assert result["next_step"] == "get_failover_provider"  # Routes to Step 72
        assert result["reason"] == "production_last_retry"

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 70
        assert completed_log["node_label"] == "ProdCheck"
        assert completed_log["use_failover"] is True
        assert completed_log["decision"] == "failover"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_production_not_last_retry(self, mock_rag_log):
        """Test Step 70: Production but NOT last retry - retry same provider."""
        from app.orchestrators.platform import step_70__prod_check

        ctx = {
            "environment": Environment.PRODUCTION,
            "attempt_number": 1,
            "max_retries": 3,
            "is_last_retry": False,
            "request_id": "test-70-prod-not-last",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        # Should retry same provider (Step 73)
        assert result["is_production"] is True
        assert result["is_last_retry"] is False
        assert result["use_failover"] is False
        assert result["next_step"] == "retry_same_provider"  # Routes to Step 73
        assert result["reason"] == "production_not_last_retry"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_non_production_last_retry(self, mock_rag_log):
        """Test Step 70: Non-production environment but last retry - retry same."""
        from app.orchestrators.platform import step_70__prod_check

        ctx = {
            "environment": Environment.DEVELOPMENT,
            "attempt_number": 2,
            "max_retries": 3,
            "is_last_retry": True,
            "request_id": "test-70-dev-last",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        # Should retry same provider (Step 73)
        assert result["is_production"] is False
        assert result["is_last_retry"] is True
        assert result["use_failover"] is False
        assert result["next_step"] == "retry_same_provider"  # Routes to Step 73
        assert result["reason"] == "non_production"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_non_production_not_last_retry(self, mock_rag_log):
        """Test Step 70: Non-production and not last retry - retry same."""
        from app.orchestrators.platform import step_70__prod_check

        ctx = {
            "environment": Environment.DEVELOPMENT,
            "attempt_number": 1,
            "max_retries": 3,
            "is_last_retry": False,
            "request_id": "test-70-dev-not-last",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        assert result["is_production"] is False
        assert result["is_last_retry"] is False
        assert result["use_failover"] is False
        assert result["next_step"] == "retry_same_provider"
        assert result["reason"] == "non_production"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_staging_environment(self, mock_rag_log):
        """Test Step 70: Staging environment behavior."""
        from app.orchestrators.platform import step_70__prod_check

        ctx = {
            "environment": Environment.STAGING,
            "attempt_number": 2,
            "max_retries": 3,
            "is_last_retry": True,
            "request_id": "test-70-staging",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        # Staging is not production, so retry same provider
        assert result["is_production"] is False
        assert result["use_failover"] is False
        assert result["next_step"] == "retry_same_provider"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_calculates_is_last_retry(self, mock_rag_log):
        """Test Step 70: Correctly calculates is_last_retry from attempt/max_retries."""
        from app.orchestrators.platform import step_70__prod_check

        # Test auto-calculation when is_last_retry not provided
        ctx = {
            "environment": Environment.PRODUCTION,
            "attempt_number": 2,
            "max_retries": 3,
            # is_last_retry not provided
            "request_id": "test-70-auto-calc",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        # Should calculate: attempt 2 of max 3 = last retry (2 == 3 - 1)
        assert result["is_last_retry"] is True
        assert result["use_failover"] is True
        assert result["next_step"] == "get_failover_provider"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_missing_environment_defaults_to_config(self, mock_rag_log):
        """Test Step 70: Uses settings.ENVIRONMENT when not in context."""
        from app.orchestrators.platform import step_70__prod_check

        ctx = {
            # environment not provided
            "attempt_number": 2,
            "max_retries": 3,
            "is_last_retry": True,
            "request_id": "test-70-default-env",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        # Should use settings.ENVIRONMENT (from config)
        assert "is_production" in result
        assert result["is_production"] is not None

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_various_attempt_patterns(self, mock_rag_log):
        """Test Step 70: Various attempt number patterns."""
        from app.orchestrators.platform import step_70__prod_check

        test_cases = [
            # (attempt, max_retries, expected_is_last_retry)
            (0, 3, False),  # First attempt (0-based)
            (1, 3, False),  # First attempt (1-based)
            (2, 3, True),  # Last retry (1-based: 2 of 3)
            (1, 2, True),  # Last retry (1-based: 1 of 2)
            (4, 5, True),  # Last retry (4 of 5)
        ]

        for attempt, max_retries, expected_last in test_cases:
            mock_rag_log.reset_mock()

            ctx = {
                "environment": Environment.PRODUCTION,
                "attempt_number": attempt,
                "max_retries": max_retries,
                "request_id": f"test-70-pattern-{attempt}-{max_retries}",
            }

            result = await step_70__prod_check(messages=[], ctx=ctx)

            # Logic: is_last_retry when attempt_number == max_retries - 1
            # OR when attempts_remaining == 1
            assert result["is_last_retry"] == expected_last, f"Failed for attempt={attempt}, max={max_retries}"

            if expected_last:
                assert result["use_failover"] is True
                assert result["next_step"] == "get_failover_provider"
            else:
                assert result["use_failover"] is False
                assert result["next_step"] == "retry_same_provider"


class TestRAGStep70Parity:
    """Parity tests proving Step 70 preserves existing logic."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_parity_failover_condition(self, mock_rag_log):
        """Test Step 70: Parity with existing failover condition."""
        from app.orchestrators.platform import step_70__prod_check

        # Original logic from graph.py:779
        # if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
        # Note: In 0-based indexing, max_retries=3 means attempts 0,1,2
        # attempt == max_retries - 2 means attempt 1 (second attempt)
        # In 1-based indexing, this is attempt 2 of 3 (last retry)

        max_retries = 3

        # Original 0-based: attempt 1 of range(3) = [0, 1, 2]
        # Our 1-based: attempt 2 of 3
        original_attempt_0based = 1
        our_attempt_1based = 2

        ctx = {
            "environment": Environment.PRODUCTION,
            "attempt_number": our_attempt_1based,
            "max_retries": max_retries,
            "request_id": "test-parity-failover",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        # Original condition: PRODUCTION and attempt == max_retries - 2
        # Our condition: PRODUCTION and is_last_retry
        original_would_failover = (
            ctx["environment"] == Environment.PRODUCTION and original_attempt_0based == max_retries - 2
        )

        assert result["use_failover"] == original_would_failover
        assert result["use_failover"] is True  # Both should be True

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_parity_retry_same_condition(self, mock_rag_log):
        """Test Step 70: Parity for retry same provider condition."""
        from app.orchestrators.platform import step_70__prod_check

        # Original: any case where NOT (PRODUCTION and last retry)
        test_cases = [
            (Environment.DEVELOPMENT, 1, 3, False),  # Dev, not last
            (Environment.DEVELOPMENT, 2, 3, False),  # Dev, last
            (Environment.PRODUCTION, 1, 3, False),  # Prod, not last
            (Environment.STAGING, 2, 3, False),  # Staging, last
        ]

        for env, attempt, max_retries, expected_failover in test_cases:
            mock_rag_log.reset_mock()

            ctx = {
                "environment": env,
                "attempt_number": attempt,
                "max_retries": max_retries,
                "request_id": f"test-parity-{env.value}-{attempt}",
            }

            result = await step_70__prod_check(messages=[], ctx=ctx)

            # All these cases should NOT use failover
            assert result["use_failover"] == expected_failover
            assert result["next_step"] == "retry_same_provider"


class TestRAGStep70Integration:
    """Integration tests for Step 69 → Step 70 → Step 72/73 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_69_to_70_integration(self, mock_rag_log):
        """Test Step 69 (retry allowed) → Step 70 (prod check) integration."""
        from app.orchestrators.platform import step_69__retry_check, step_70__prod_check

        # Step 69: Check if retry allowed
        step_69_ctx = {
            "attempt_number": 2,
            "max_retries": 3,
            "error": "API timeout",
            "request_id": "test-integration-69-70",
        }

        step_69_result = await step_69__retry_check(messages=[], ctx=step_69_ctx)

        # Should allow retry and route to prod_check
        assert step_69_result["retry_allowed"] is True
        assert step_69_result["next_step"] == "prod_check"
        assert step_69_result["is_last_retry"] is True  # attempt 2 of 3

        # Step 70: Check if production and last retry
        step_70_ctx = {
            "environment": Environment.PRODUCTION,
            "attempt_number": step_69_result["attempt_number"],
            "max_retries": step_69_result["max_retries"],
            "is_last_retry": step_69_result["is_last_retry"],
            "request_id": step_69_result["request_id"],
        }

        step_70_result = await step_70__prod_check(messages=[], ctx=step_70_ctx)

        # Production + last retry = use failover
        assert step_70_result["use_failover"] is True
        assert step_70_result["next_step"] == "get_failover_provider"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_to_72_failover_flow(self, mock_rag_log):
        """Test Step 70 → Step 72 (failover) flow."""
        from app.orchestrators.platform import step_70__prod_check

        # Production + last retry
        ctx = {
            "environment": Environment.PRODUCTION,
            "attempt_number": 2,
            "max_retries": 3,
            "is_last_retry": True,
            "request_id": "test-70-to-72",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        # Should route to Step 72 (get_failover_provider)
        assert result["use_failover"] is True
        assert result["next_step"] == "get_failover_provider"

        # Context should be ready for Step 72
        assert result["environment"] == Environment.PRODUCTION
        assert result["attempt_number"] == 2
        assert result["max_retries"] == 3

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    async def test_step_70_to_73_retry_same_flow(self, mock_rag_log):
        """Test Step 70 → Step 73 (retry same) flow."""
        from app.orchestrators.platform import step_70__prod_check

        # Production but NOT last retry
        ctx = {
            "environment": Environment.PRODUCTION,
            "attempt_number": 1,
            "max_retries": 3,
            "is_last_retry": False,
            "request_id": "test-70-to-73",
        }

        result = await step_70__prod_check(messages=[], ctx=ctx)

        # Should route to Step 73 (retry_same_provider)
        assert result["use_failover"] is False
        assert result["next_step"] == "retry_same_provider"

        # Context preserved for Step 73
        assert result["environment"] == Environment.PRODUCTION
        assert result["attempt_number"] == 1
