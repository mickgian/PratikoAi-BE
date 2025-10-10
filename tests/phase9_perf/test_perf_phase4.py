"""
Performance tests for Phase 4: Cache, LLM, and Tools wrappers.

Tests that wrapper overhead meets P95 budget requirements.
Uses time.perf_counter() for precise timing.
"""

import pytest
import time
from unittest.mock import patch

from tests.common.fixtures_state import make_state, state_needs_llm, state_with_tools
from tests.common.fakes import (
    fake_cache_check_orch,
    fake_llm_call_orch,
    fake_tool_execution_orch,
)
from tests.common.budgets import (
    should_skip_perf_tests,
    get_cache_budget,
    get_llm_budget,
    get_tools_budget,
    calculate_p95,
    assert_within_budget,
)
from app.core.langgraph.nodes.step_059__check_cache import node_step_59
from app.core.langgraph.nodes.step_064__llm_call import node_step_64
from app.core.langgraph.nodes.step_080__kb_tool import node_step_80


@pytest.mark.perf
@pytest.mark.phase4
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase4CachePerformance:
    """Test cache wrapper performance."""

    async def test_cache_check_wrapper_performance(self):
        """Verify cache check wrapper meets P95 budget."""
        state = make_state()
        fake_orch = fake_cache_check_orch(hit=True)

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_59(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        # Calculate P95
        p95_ms = calculate_p95(durations)
        budget_ms = get_cache_budget()

        # Assert within budget
        assert_within_budget(p95_ms, budget_ms, "cache_check_wrapper")

    async def test_cache_miss_wrapper_performance(self):
        """Verify cache miss path meets P95 budget."""
        state = make_state()
        fake_orch = fake_cache_check_orch(hit=False)

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_59(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_cache_budget()

        assert_within_budget(p95_ms, budget_ms, "cache_miss_wrapper")


@pytest.mark.perf
@pytest.mark.phase4
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase4LLMPerformance:
    """Test LLM wrapper performance."""

    async def test_llm_call_wrapper_performance(self):
        """Verify LLM call wrapper meets P95 budget."""
        state = state_needs_llm()
        fake_orch = fake_llm_call_orch(success=True, has_tools=False)

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_64(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_llm_budget()

        assert_within_budget(p95_ms, budget_ms, "llm_call_wrapper")

    async def test_llm_with_tools_wrapper_performance(self):
        """Verify LLM with tools wrapper meets P95 budget."""
        state = state_needs_llm()
        fake_orch = fake_llm_call_orch(success=True, has_tools=True)

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_64(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_llm_budget()

        assert_within_budget(p95_ms, budget_ms, "llm_with_tools_wrapper")

    async def test_llm_failure_wrapper_performance(self):
        """Verify LLM failure path wrapper meets P95 budget."""
        state = state_needs_llm()
        fake_orch = fake_llm_call_orch(success=False)

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_64(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_llm_budget()

        assert_within_budget(p95_ms, budget_ms, "llm_failure_wrapper")


@pytest.mark.perf
@pytest.mark.phase4
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase4ToolsPerformance:
    """Test tool execution wrapper performance."""

    async def test_kb_tool_wrapper_performance(self):
        """Verify KB tool wrapper meets P95 budget."""
        state = state_with_tools()
        fake_orch = fake_tool_execution_orch(tool_type="kb")

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_080__kb_tool.step_80__kb_tool", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_80(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_tools_budget()

        assert_within_budget(p95_ms, budget_ms, "kb_tool_wrapper")

    async def test_ccnl_tool_wrapper_performance(self):
        """Verify CCNL tool wrapper meets P95 budget."""
        state = state_with_tools()
        fake_orch = fake_tool_execution_orch(tool_type="ccnl")

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_081__ccnl_tool.step_81__ccnl_tool", fake_orch):
            from app.core.langgraph.nodes.step_081__ccnl_tool import node_step_81

            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_81(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_tools_budget()

        assert_within_budget(p95_ms, budget_ms, "ccnl_tool_wrapper")

    async def test_doc_ingest_tool_wrapper_performance(self):
        """Verify document ingest tool wrapper meets P95 budget."""
        state = state_with_tools()
        fake_orch = fake_tool_execution_orch(tool_type="doc")

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_082__doc_ingest_tool.step_82__doc_ingest_tool", fake_orch):
            from app.core.langgraph.nodes.step_082__doc_ingest_tool import node_step_82

            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_82(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_tools_budget()

        assert_within_budget(p95_ms, budget_ms, "doc_ingest_tool_wrapper")

    async def test_faq_tool_wrapper_performance(self):
        """Verify FAQ tool wrapper meets P95 budget."""
        state = state_with_tools()
        fake_orch = fake_tool_execution_orch(tool_type="faq")

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_083__faq_tool.step_83__faq_tool", fake_orch):
            from app.core.langgraph.nodes.step_083__faq_tool import node_step_83

            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_83(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_tools_budget()

        assert_within_budget(p95_ms, budget_ms, "faq_tool_wrapper")


@pytest.mark.perf
@pytest.mark.phase4
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase4StateManipulation:
    """Test state manipulation performance."""

    async def test_state_copy_performance(self):
        """Verify state copy operation is fast."""
        state = make_state(
            messages=[{"role": "user", "content": "test"}] * 10,
            privacy={"enabled": True, "pii_detected": False},
            llm={"success": True, "response": {"content": "test"}},
        )

        iterations = 100
        durations = []

        for _ in range(iterations):
            start_ns = time.perf_counter_ns()
            _ = state.copy()
            end_ns = time.perf_counter_ns()

            duration_ms = (end_ns - start_ns) / 1_000_000
            durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        # State copy should be very fast (<1ms)
        assert_within_budget(p95_ms, 1.0, "state_copy")

    async def test_state_update_performance(self):
        """Verify state update operation is fast."""
        state = make_state()

        iterations = 100
        durations = []

        for i in range(iterations):
            start_ns = time.perf_counter_ns()
            state["test_field"] = f"value_{i}"
            state["nested"] = {"key": i, "data": "test"}
            end_ns = time.perf_counter_ns()

            duration_ms = (end_ns - start_ns) / 1_000_000
            durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        # State update should be very fast (<0.5ms)
        assert_within_budget(p95_ms, 0.5, "state_update")
