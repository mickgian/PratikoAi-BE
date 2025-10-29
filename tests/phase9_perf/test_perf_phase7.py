"""
Performance tests for Phase 7: Streaming wrappers.

Tests that streaming wrapper overhead meets P95 budget requirements.
"""

import pytest
import time
from unittest.mock import patch

from tests.common.fixtures_state import make_state, state_streaming_enabled
from tests.common.fakes import (
    fake_stream_setup_orch,
    FakeOrchestrator,
)
from tests.common.budgets import (
    should_skip_perf_tests,
    get_stream_budget,
    calculate_p95,
    assert_within_budget,
)
from app.core.langgraph.nodes.step_104__stream_check import node_step_104
from app.core.langgraph.nodes.step_105__stream_setup import node_step_105
from app.core.langgraph.nodes.step_108__write_sse import node_step_108
from app.core.langgraph.nodes.step_107__single_pass import node_step_107


@pytest.mark.perf
@pytest.mark.phase7
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase7StreamCheckPerformance:
    """Test stream check wrapper performance."""

    async def test_stream_check_enabled_performance(self):
        """Verify stream check (enabled) wrapper meets P95 budget."""
        state = make_state(streaming={"requested": True, "enabled": False})
        fake_orch = FakeOrchestrator({
            "streaming_enabled": True,
            "stream_requested": True
        })

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_104__stream_check.step_104__stream_check", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_104(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "stream_check_enabled")

    async def test_stream_check_disabled_performance(self):
        """Verify stream check (disabled) wrapper meets P95 budget."""
        state = make_state(streaming={"requested": False, "enabled": False})
        fake_orch = FakeOrchestrator({
            "streaming_enabled": False,
            "stream_requested": False
        })

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_104__stream_check.step_104__stream_check", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_104(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "stream_check_disabled")


@pytest.mark.perf
@pytest.mark.phase7
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase7StreamSetupPerformance:
    """Test stream setup wrapper performance."""

    async def test_stream_setup_wrapper_performance(self):
        """Verify stream setup wrapper meets P95 budget."""
        state = state_streaming_enabled()
        fake_orch = fake_stream_setup_orch()

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_105__stream_setup.step_105__stream_setup", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_105(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "stream_setup_wrapper")


@pytest.mark.perf
@pytest.mark.phase7
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase7SSEWritePerformance:
    """Test SSE write wrapper performance."""

    async def test_sse_write_small_response_performance(self):
        """Verify SSE write wrapper with small response meets P95 budget."""
        state = state_streaming_enabled()
        state["response"] = {"content": "Small response text", "complete": True}

        fake_orch = FakeOrchestrator({
            "chunks_written": 1,
            "write_success": True
        })

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_108(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "sse_write_small")

    async def test_sse_write_large_response_performance(self):
        """Verify SSE write wrapper with large response meets P95 budget."""
        state = state_streaming_enabled()
        # Simulate large response (multiple chunks)
        state["response"] = {
            "content": " ".join([f"chunk{i}" for i in range(100)]),
            "complete": True
        }

        fake_orch = FakeOrchestrator({
            "chunks_written": 100,
            "write_success": True
        })

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_108__write_sse.step_108__write_sse", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_108(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "sse_write_large")


@pytest.mark.perf
@pytest.mark.phase7
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase7SinglePassPerformance:
    """Test non-streaming single-pass wrapper performance."""

    async def test_single_pass_wrapper_performance(self):
        """Verify single-pass (non-streaming) wrapper meets P95 budget."""
        state = make_state(
            streaming={"enabled": False},
            response={"content": "Complete response text", "complete": True}
        )

        fake_orch = FakeOrchestrator({
            "response_complete": True,
            "response_sent": True
        })

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_107__single_pass.step_107__single_pass", fake_orch):
            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_107(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "single_pass_wrapper")


@pytest.mark.perf
@pytest.mark.phase7
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase7StreamingGenerator:
    """Test async generator wrapper performance."""

    async def test_async_generator_wrapper_performance(self):
        """Verify async generator wrapper meets P95 budget."""
        state = state_streaming_enabled()
        state["response"] = {"content": "word1 word2 word3 word4 word5", "complete": False}

        fake_orch = FakeOrchestrator({
            "generator_ready": True,
            "chunk_count": 5
        })

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_106__async_gen.step_106__async_gen", fake_orch):
            from app.core.langgraph.nodes.step_106__async_gen import node_step_106

            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_106(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "async_generator_wrapper")


@pytest.mark.perf
@pytest.mark.phase7
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase7StreamingCompletion:
    """Test streaming completion wrapper performance."""

    async def test_send_done_wrapper_performance(self):
        """Verify send done signal wrapper meets P95 budget."""
        state = state_streaming_enabled()
        state["response"] = {"complete": True}

        fake_orch = FakeOrchestrator({
            "done_sent": True,
            "stream_complete": True
        })

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_110__send_done.step_110__send_done", fake_orch):
            from app.core.langgraph.nodes.step_110__send_done import node_step_110

            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_110(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "send_done_wrapper")

    async def test_stream_response_wrapper_performance(self):
        """Verify stream response wrapper meets P95 budget."""
        state = state_streaming_enabled()

        fake_orch = FakeOrchestrator({
            "streaming_in_progress": True,
            "chunks_sent": 10
        })

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_109__stream_response.step_109__stream_response", fake_orch):
            from app.core.langgraph.nodes.step_109__stream_response import node_step_109

            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_109(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "stream_response_wrapper")


@pytest.mark.perf
@pytest.mark.phase7
@pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled (RAG_SKIP_PERF=1)")
class TestPhase7MetricsCollection:
    """Test metrics collection wrapper performance."""

    async def test_collect_metrics_wrapper_performance(self):
        """Verify collect metrics wrapper meets P95 budget."""
        state = state_streaming_enabled()
        state["metrics"] = {
            "total_duration_ms": 523,
            "llm_calls": 1,
            "cache_hits": 0,
            "tool_calls": 0
        }

        fake_orch = FakeOrchestrator({
            "metrics_collected": True,
            "metric_count": 10
        })

        iterations = 10
        durations = []

        with patch("app.core.langgraph.nodes.step_111__collect_metrics.step_111__collect_metrics", fake_orch):
            from app.core.langgraph.nodes.step_111__collect_metrics import node_step_111

            for _ in range(iterations):
                start_ns = time.perf_counter_ns()
                await node_step_111(state.copy())
                end_ns = time.perf_counter_ns()

                duration_ms = (end_ns - start_ns) / 1_000_000
                durations.append(duration_ms)

        p95_ms = calculate_p95(durations)
        budget_ms = get_stream_budget()

        assert_within_budget(p95_ms, budget_ms, "collect_metrics_wrapper")
