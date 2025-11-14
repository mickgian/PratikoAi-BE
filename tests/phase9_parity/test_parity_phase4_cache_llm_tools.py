"""
Parity tests for Phase 4: Cache, LLM, and Tools lane.

Verifies that node wrappers correctly delegate to orchestrators
and maintain consistent state behavior.
"""

import pytest
from unittest.mock import patch, AsyncMock

from tests.common.fixtures_state import make_state, state_needs_llm, state_with_tools
from tests.common.fakes import (
    fake_cache_check_orch,
    fake_llm_call_orch,
    fake_tool_execution_orch,
)
from app.core.langgraph.nodes.step_059__check_cache import node_step_59
from app.core.langgraph.nodes.step_064__llm_call import node_step_64
from app.core.langgraph.nodes.step_080__kb_tool import node_step_80


@pytest.mark.parity
@pytest.mark.phase4
class TestPhase4CacheParity:
    """Test cache node wrapper parity with orchestrator."""

    async def test_cache_hit_delegates_to_orchestrator(self):
        """Verify cache hit path delegates correctly."""
        state = make_state()
        fake_orch = fake_cache_check_orch(hit=True)

        with patch("app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_orch):
            result = await node_step_59(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify state reflects cache hit
        assert "cache" in result
        assert result["cache"]["hit"] is True
        assert result.get("cached_response") is not None

    async def test_cache_miss_delegates_to_orchestrator(self):
        """Verify cache miss path delegates correctly."""
        state = make_state()
        fake_orch = fake_cache_check_orch(hit=False)

        with patch("app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_orch):
            result = await node_step_59(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify state reflects cache miss
        assert "cache" in result
        assert result["cache"]["hit"] is False

    async def test_cache_wrapper_preserves_state(self):
        """Verify cache wrapper doesn't lose state fields."""
        state = make_state(
            messages=[{"role": "user", "content": "test"}],
            privacy={"enabled": True}
        )
        fake_orch = fake_cache_check_orch(hit=False)

        with patch("app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_orch):
            result = await node_step_59(state)

        # Original state preserved
        assert result["messages"] == state["messages"]
        assert result["privacy"] == state["privacy"]


@pytest.mark.parity
@pytest.mark.phase4
class TestPhase4LLMParity:
    """Test LLM node wrapper parity with orchestrator."""

    async def test_llm_success_delegates_to_orchestrator(self):
        """Verify successful LLM call delegates correctly."""
        state = state_needs_llm()
        fake_orch = fake_llm_call_orch(success=True, has_tools=False)

        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            result = await node_step_64(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify state reflects LLM success
        assert "llm" in result
        assert result["llm"]["success"] is True
        assert result["llm"]["response"] is not None

    async def test_llm_with_tools_delegates_correctly(self):
        """Verify LLM call with tool requests delegates correctly."""
        state = state_needs_llm()
        fake_orch = fake_llm_call_orch(success=True, has_tools=True)

        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            result = await node_step_64(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify state reflects tool calls
        assert result["llm"]["success"] is True
        assert result.get("llm_response", {}).get("tool_calls") is not None

    async def test_llm_failure_delegates_correctly(self):
        """Verify LLM failure path delegates correctly."""
        state = state_needs_llm()
        fake_orch = fake_llm_call_orch(success=False)

        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            result = await node_step_64(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify state reflects failure
        assert result["llm"]["success"] is False


@pytest.mark.parity
@pytest.mark.phase4
class TestPhase4ToolsParity:
    """Test tool execution node wrapper parity with orchestrator."""

    async def test_kb_tool_delegates_to_orchestrator(self):
        """Verify KB tool execution delegates correctly."""
        state = state_with_tools()
        fake_orch = fake_tool_execution_orch(tool_type="kb")

        with patch("app.core.langgraph.nodes.step_080__kb_tool.step_80__kb_tool", fake_orch):
            result = await node_step_80(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify state updated with tool results
        assert result.get("tool_success") is True
        assert result.get("tool_type") == "kb"

    async def test_tool_wrapper_preserves_llm_state(self):
        """Verify tool wrapper doesn't lose LLM state."""
        state = state_with_tools()
        original_llm = state.get("llm")
        fake_orch = fake_tool_execution_orch(tool_type="kb")

        with patch("app.core.langgraph.nodes.step_080__kb_tool.step_80__kb_tool", fake_orch):
            result = await node_step_80(state)

        # LLM state preserved
        assert result.get("llm") == original_llm
