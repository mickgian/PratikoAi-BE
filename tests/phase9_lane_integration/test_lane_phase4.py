"""
Lane integration tests for Phase 4: Cache, LLM, and Tools lane.

Tests end-to-end flow through cache check → LLM call → tool execution paths.
"""

from unittest.mock import patch

import pytest

from app.core.langgraph.nodes.step_059__check_cache import node_step_59
from app.core.langgraph.nodes.step_064__llm_call import node_step_64
from app.core.langgraph.nodes.step_080__kb_tool import node_step_80
from app.core.langgraph.nodes.step_099__tool_results import node_step_99
from tests.common.fakes import (
    fake_cache_check_orch,
    fake_llm_call_orch,
    fake_tool_execution_orch,
)
from tests.common.fixtures_state import make_state


@pytest.mark.lane
@pytest.mark.phase4
class TestPhase4CacheHitPath:
    """Test cache hit path (bypass LLM)."""

    async def test_cache_hit_returns_cached_response(self):
        """Verify cache hit path returns cached response and skips LLM."""
        state = make_state()

        # Step 59: Check cache (HIT)
        with patch(
            "app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_cache_check_orch(hit=True)
        ):
            state = await node_step_59(state)

        # Verify cache hit detected
        assert state["cache"]["hit"] is True
        assert state.get("cached_response") is not None

        # In real flow, we'd skip to step_62 (cache_hit routing)
        # and then step_66 (return_cached)
        # Verify state has what's needed
        assert state.get("cached_response", {}).get("content") == "Cached answer"


@pytest.mark.lane
@pytest.mark.phase4
class TestPhase4CacheMissLLMPath:
    """Test cache miss → LLM call path."""

    async def test_cache_miss_flows_to_llm_call(self):
        """Verify cache miss flows to LLM call."""
        state = make_state(provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"})

        # Step 59: Check cache (MISS)
        with patch(
            "app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_cache_check_orch(hit=False)
        ):
            state = await node_step_59(state)

        # Verify cache miss
        assert state["cache"]["hit"] is False

        # Step 64: LLM call (SUCCESS without tools)
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            fake_llm_call_orch(success=True, has_tools=False),
        ):
            state = await node_step_64(state)

        # Verify LLM success
        assert state["llm"]["success"] is True
        assert state["llm"]["response"]["content"] == "LLM response"

    async def test_cache_miss_llm_success_has_response(self):
        """Verify cache miss + LLM success produces complete response."""
        state = make_state(provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"})

        # Cache miss
        with patch(
            "app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_cache_check_orch(hit=False)
        ):
            state = await node_step_59(state)

        # LLM success
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            fake_llm_call_orch(success=True, has_tools=False),
        ):
            state = await node_step_64(state)

        # Should have complete LLM response
        assert state["llm"]["success"] is True
        assert state["llm"]["response"]["content"]
        assert state["llm"]["response"]["usage"]["input_tokens"] == 100


@pytest.mark.lane
@pytest.mark.phase4
class TestPhase4ToolExecutionPath:
    """Test LLM with tools → tool execution path."""

    async def test_llm_with_tools_flows_to_tool_execution(self):
        """Verify LLM with tool calls flows to tool execution."""
        state = make_state(provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"})

        # Cache miss
        with patch(
            "app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_cache_check_orch(hit=False)
        ):
            state = await node_step_59(state)

        # LLM with tools
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            fake_llm_call_orch(success=True, has_tools=True),
        ):
            state = await node_step_64(state)

        # Verify tool calls present
        assert state["llm"]["success"] is True
        assert state.get("llm_response", {}).get("tool_calls") is not None

        # Step 80: KB tool execution
        with patch(
            "app.core.langgraph.nodes.step_080__kb_tool.step_80__kb_tool", fake_tool_execution_orch(tool_type="kb")
        ):
            state = await node_step_80(state)

        # Verify tool execution
        assert state.get("tool_success") is True
        assert state.get("results") is not None

    async def test_tool_results_merged_correctly(self):
        """Verify tool results are merged into state correctly."""
        state = make_state(provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"})

        # Cache miss → LLM with tools
        with patch(
            "app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_cache_check_orch(hit=False)
        ):
            state = await node_step_59(state)

        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            fake_llm_call_orch(success=True, has_tools=True),
        ):
            state = await node_step_64(state)

        # KB tool execution
        with patch(
            "app.core.langgraph.nodes.step_080__kb_tool.step_80__kb_tool", fake_tool_execution_orch(tool_type="kb")
        ):
            state = await node_step_80(state)

        # Step 99: Merge tool results
        from tests.common.fakes import FakeOrchestrator

        fake_merge = FakeOrchestrator({"tools_merged": True, "tool_results_count": 1})
        with patch("app.core.langgraph.nodes.step_099__tool_results.step_99__tool_results", fake_merge):
            state = await node_step_99(state)

        # Verify merge
        assert state.get("tools_merged") is True


@pytest.mark.lane
@pytest.mark.phase4
class TestPhase4RetryPath:
    """Test LLM failure → retry path."""

    async def test_llm_failure_can_retry(self):
        """Verify LLM failure sets up retry state."""
        state = make_state(provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"})

        # Cache miss
        with patch(
            "app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_cache_check_orch(hit=False)
        ):
            state = await node_step_59(state)

        # LLM failure
        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_llm_call_orch(success=False)):
            state = await node_step_64(state)

        # Verify failure detected
        assert state["llm"]["success"] is False
        assert state.get("error") is not None

        # In real flow, step_69 (retry_check) would determine retry logic
        # Verify we have error state for retry decision
        assert state.get("status_code") == 500
