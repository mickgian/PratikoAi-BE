"""
Failure injection tests for Phase 4: Cache, LLM, and Tools failures.

Tests error handling for cache downtime, LLM API errors, and tool timeouts.
"""

from unittest.mock import patch

import pytest

from app.core.langgraph.nodes.step_059__check_cache import node_step_59
from app.core.langgraph.nodes.step_064__llm_call import node_step_64
from app.core.langgraph.nodes.step_080__kb_tool import node_step_80
from tests.common.fakes import FakeOrchestrator
from tests.common.fixtures_state import make_state, state_needs_llm, state_with_tools


@pytest.mark.failure
@pytest.mark.phase4
class TestPhase4CacheFailures:
    """Test cache service failure handling."""

    async def test_cache_service_down_handles_gracefully(self):
        """Verify cache service down is handled gracefully (treat as miss)."""
        state = make_state()

        # Cache check raises exception
        fake_orch = FakeOrchestrator(
            {
                "cache_error": True,
                "cache_available": False,
                "cache_hit": False,  # Treat as miss when cache is down
            }
        )
        with patch("app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_orch):
            state = await node_step_59(state)

        # Should handle gracefully and continue
        assert state.get("cache_error") is True
        assert state["cache"]["hit"] is False  # Treated as miss

    async def test_cache_timeout_treats_as_miss(self):
        """Verify cache timeout is treated as cache miss."""
        state = make_state()

        fake_orch = FakeOrchestrator({"cache_timeout": True, "cache_hit": False, "timeout_ms": 5000})
        with patch("app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_orch):
            state = await node_step_59(state)

        # Timeout treated as miss
        assert state.get("cache_timeout") is True
        assert state["cache"]["hit"] is False

    async def test_cache_corrupted_data_treats_as_miss(self):
        """Verify corrupted cache data is treated as miss."""
        state = make_state()

        fake_orch = FakeOrchestrator({"cache_hit": False, "cache_error": True, "error_type": "corrupted_data"})
        with patch("app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_orch):
            state = await node_step_59(state)

        # Corrupted data treated as miss
        assert state["cache"]["hit"] is False


@pytest.mark.failure
@pytest.mark.phase4
class TestPhase4LLMFailures:
    """Test LLM API failure handling."""

    async def test_llm_500_error_sets_failure_state(self):
        """Verify LLM 500 error sets appropriate failure state."""
        state = state_needs_llm()

        # LLM returns 500 error
        fake_orch = FakeOrchestrator(
            {"llm_success": False, "error": "Internal Server Error", "status_code": 500, "retryable": True}
        )
        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            state = await node_step_64(state)

        # Failure state set
        assert state["llm"]["success"] is False
        assert state.get("status_code") == 500
        assert state.get("retryable") is True

    async def test_llm_rate_limit_error_indicates_retry(self):
        """Verify rate limit error indicates retry is possible."""
        state = state_needs_llm()

        fake_orch = FakeOrchestrator(
            {
                "llm_success": False,
                "error": "Rate limit exceeded",
                "status_code": 429,
                "retryable": True,
                "retry_after_ms": 1000,
            }
        )
        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            state = await node_step_64(state)

        # Rate limit should be retryable
        assert state["llm"]["success"] is False
        assert state.get("status_code") == 429
        assert state.get("retryable") is True

    async def test_llm_auth_error_not_retryable(self):
        """Verify authentication error is not retryable."""
        state = state_needs_llm()

        fake_orch = FakeOrchestrator(
            {"llm_success": False, "error": "Invalid API key", "status_code": 401, "retryable": False}
        )
        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            state = await node_step_64(state)

        # Auth error should not be retryable
        assert state["llm"]["success"] is False
        assert state.get("status_code") == 401
        assert state.get("retryable") is False

    async def test_llm_timeout_error_retryable(self):
        """Verify LLM timeout is retryable."""
        state = state_needs_llm()

        fake_orch = FakeOrchestrator(
            {"llm_success": False, "error": "Request timeout", "timeout": True, "retryable": True}
        )
        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            state = await node_step_64(state)

        # Timeout should be retryable
        assert state["llm"]["success"] is False
        assert state.get("timeout") is True
        assert state.get("retryable") is True


@pytest.mark.failure
@pytest.mark.phase4
class TestPhase4ToolFailures:
    """Test tool execution failure handling."""

    async def test_tool_timeout_handles_gracefully(self):
        """Verify tool timeout is handled gracefully."""
        state = state_with_tools()

        # Tool execution times out
        fake_orch = FakeOrchestrator(
            {"tool_success": False, "error": "Tool execution timeout", "timeout": True, "timeout_ms": 30000}
        )
        with patch("app.core.langgraph.nodes.step_080__kb_tool.step_80__kb_tool", fake_orch):
            state = await node_step_80(state)

        # Timeout handled
        assert state.get("tool_success") is False
        assert state.get("timeout") is True

    async def test_tool_kb_unavailable_returns_error(self):
        """Verify KB unavailable error is handled."""
        state = state_with_tools()

        fake_orch = FakeOrchestrator(
            {"tool_success": False, "error": "Knowledge base unavailable", "kb_available": False}
        )
        with patch("app.core.langgraph.nodes.step_080__kb_tool.step_80__kb_tool", fake_orch):
            state = await node_step_80(state)

        # KB unavailable handled
        assert state.get("tool_success") is False
        assert state.get("kb_available") is False

    async def test_tool_empty_results_not_failure(self):
        """Verify empty tool results is not treated as failure."""
        state = state_with_tools()

        # Tool succeeds but returns empty results
        fake_orch = FakeOrchestrator({"tool_success": True, "results": {"documents": []}, "results_count": 0})
        with patch("app.core.langgraph.nodes.step_080__kb_tool.step_80__kb_tool", fake_orch):
            state = await node_step_80(state)

        # Success despite empty results
        assert state.get("tool_success") is True
        assert state.get("results_count") == 0

    async def test_tool_partial_failure_returns_available_results(self):
        """Verify partial tool failure returns available results."""
        state = state_with_tools()

        # Some documents retrieved, some failed
        fake_orch = FakeOrchestrator(
            {
                "tool_success": True,
                "partial_failure": True,
                "results": {"documents": [{"title": "Doc 1"}]},
                "results_count": 1,
                "failed_sources": ["source_2"],
            }
        )
        with patch("app.core.langgraph.nodes.step_080__kb_tool.step_80__kb_tool", fake_orch):
            state = await node_step_80(state)

        # Partial results returned
        assert state.get("tool_success") is True
        assert state.get("partial_failure") is True
        assert state.get("results_count") == 1


@pytest.mark.failure
@pytest.mark.phase4
class TestPhase4RetryLogic:
    """Test retry logic after failures."""

    async def test_retry_after_llm_failure(self):
        """Verify retry is attempted after retryable LLM failure."""
        state = state_needs_llm()
        state["retry_count"] = 0

        # First attempt: failure (500)
        fake_fail = FakeOrchestrator(
            {"llm_success": False, "error": "Server error", "status_code": 500, "retryable": True}
        )
        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_fail):
            state = await node_step_64(state)

        assert state["llm"]["success"] is False
        assert state.get("retryable") is True

        # Step 69: Retry check (should retry)
        fake_retry_check = FakeOrchestrator({"should_retry": True, "retry_count": 1, "max_retries": 3})
        with patch("app.core.langgraph.nodes.step_069__retry_check.step_69__retry_check", fake_retry_check):
            from app.core.langgraph.nodes.step_069__retry_check import node_step_69

            state = await node_step_69(state)

        # Retry should be indicated
        assert state.get("should_retry") is True

    async def test_no_retry_after_non_retryable_failure(self):
        """Verify no retry after non-retryable failure."""
        state = state_needs_llm()

        # Non-retryable failure (401)
        fake_fail = FakeOrchestrator(
            {"llm_success": False, "error": "Auth error", "status_code": 401, "retryable": False}
        )
        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_fail):
            state = await node_step_64(state)

        # Step 69: Retry check (should NOT retry)
        fake_retry_check = FakeOrchestrator({"should_retry": False, "retry_allowed": False})
        with patch("app.core.langgraph.nodes.step_069__retry_check.step_69__retry_check", fake_retry_check):
            from app.core.langgraph.nodes.step_069__retry_check import node_step_69

            state = await node_step_69(state)

        # No retry
        assert state.get("should_retry") is False
