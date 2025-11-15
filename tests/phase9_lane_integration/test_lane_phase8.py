"""
Lane integration tests for Phase 8: Golden KB Fast-Path Lane.

Tests end-to-end flow through golden lookup → serve or fallback paths.
"""

from unittest.mock import patch

import pytest

from app.core.langgraph.nodes.step_020__golden_fast_gate import node_step_20
from app.core.langgraph.nodes.step_024__golden_lookup import node_step_24
from app.core.langgraph.nodes.step_025__golden_hit import node_step_25
from app.core.langgraph.nodes.step_026__kb_context_check import node_step_26
from app.core.langgraph.nodes.step_028__serve_golden import node_step_28
from tests.common.fakes import (
    FakeOrchestrator,
    fake_golden_lookup_orch,
)
from tests.common.fixtures_state import make_state, state_golden_eligible


@pytest.mark.lane
@pytest.mark.phase8
class TestPhase8GoldenFastPath:
    """Test golden fast-path (high confidence match → serve)."""

    async def test_golden_eligible_high_confidence_serves_immediately(self):
        """Verify high confidence golden match serves immediately."""
        state = state_golden_eligible()

        # Step 20: Golden gate (ELIGIBLE)
        fake_gate = FakeOrchestrator({"golden_eligible": True, "should_check_golden": True})
        with patch("app.core.langgraph.nodes.step_020__golden_fast_gate.step_20__golden_fast_gate", fake_gate):
            state = await node_step_20(state)

        assert state.get("golden_eligible") is True

        # Step 24: Golden lookup (HIGH CONFIDENCE)
        with patch(
            "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
            fake_golden_lookup_orch(match_found=True, high_confidence=True),
        ):
            state = await node_step_24(state)

        # High confidence match
        assert state.get("match_found") is True
        assert state.get("high_confidence_match") is True
        assert state.get("similarity_score", 0) >= 0.95

        # Step 25: Golden hit check (routing)
        fake_hit = FakeOrchestrator({"golden_hit": True, "serve_golden": True})
        with patch("app.core.langgraph.nodes.step_025__golden_hit.step_25__golden_hit", fake_hit):
            state = await node_step_25(state)

        assert state.get("golden_hit") is True

        # Step 28: Serve golden
        fake_serve = FakeOrchestrator(
            {
                "golden_served": True,
                "response": {"content": state.get("answer"), "source": "golden_kb"},
                "complete": True,
            }
        )
        with patch("app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden", fake_serve):
            state = await node_step_28(state)

        # Golden served, request complete
        assert state.get("golden_served") is True
        assert state.get("complete") is True

    async def test_golden_fast_path_skips_llm(self):
        """Verify golden fast-path skips expensive LLM calls."""
        state = state_golden_eligible()

        # Go through golden path
        fake_gate = FakeOrchestrator({"golden_eligible": True})
        with patch("app.core.langgraph.nodes.step_020__golden_fast_gate.step_20__golden_fast_gate", fake_gate):
            state = await node_step_20(state)

        with patch(
            "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
            fake_golden_lookup_orch(match_found=True, high_confidence=True),
        ):
            state = await node_step_24(state)

        # LLM should not have been called
        assert "llm" not in state or not state.get("llm", {}).get("success")


@pytest.mark.lane
@pytest.mark.phase8
class TestPhase8GoldenLowConfidencePath:
    """Test golden low confidence → KB context → serve path."""

    async def test_low_confidence_checks_kb_context(self):
        """Verify low confidence match checks KB for additional context."""
        state = state_golden_eligible()

        # Golden gate eligible
        fake_gate = FakeOrchestrator({"golden_eligible": True})
        with patch("app.core.langgraph.nodes.step_020__golden_fast_gate.step_20__golden_fast_gate", fake_gate):
            state = await node_step_20(state)

        # Lookup finds LOW confidence match
        with patch(
            "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
            fake_golden_lookup_orch(match_found=True, high_confidence=False),
        ):
            state = await node_step_24(state)

        assert state.get("match_found") is True
        assert state.get("high_confidence_match") is False

        # Step 26: KB context check
        fake_kb_check = FakeOrchestrator({"kb_context_needed": True, "should_query_kb": True})
        with patch("app.core.langgraph.nodes.step_026__kb_context_check.step_26__kb_context_check", fake_kb_check):
            state = await node_step_26(state)

        # KB context needed
        assert state.get("kb_context_needed") is True

    async def test_low_confidence_with_kb_delta_serves(self):
        """Verify low confidence + KB delta still serves golden."""
        state = state_golden_eligible()

        # Low confidence lookup
        with patch(
            "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
            fake_golden_lookup_orch(match_found=True, high_confidence=False),
        ):
            state = await node_step_24(state)

        # Step 27: KB delta (get additional context)
        fake_delta = FakeOrchestrator(
            {"kb_docs": [{"title": "Supporting doc", "content": "Additional context"}], "kb_context_added": True}
        )
        with patch("app.core.langgraph.nodes.step_027__kb_delta.step_27__kb_delta", fake_delta):
            from app.core.langgraph.nodes.step_027__kb_delta import node_step_27

            state = await node_step_27(state)

        # KB context added
        assert state.get("kb_context_added") is True
        assert len(state.get("kb_docs", [])) > 0

        # Still serve golden (with KB context)
        fake_serve = FakeOrchestrator(
            {"golden_served": True, "response": {"content": "Golden answer with context"}, "complete": True}
        )
        with patch("app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden", fake_serve):
            state = await node_step_28(state)

        assert state.get("golden_served") is True


@pytest.mark.lane
@pytest.mark.phase8
class TestPhase8GoldenMissPath:
    """Test golden miss → fallback to normal LLM path."""

    async def test_golden_no_match_falls_back_to_llm(self):
        """Verify no golden match falls back to normal LLM path."""
        state = state_golden_eligible()

        # Golden gate eligible
        fake_gate = FakeOrchestrator({"golden_eligible": True})
        with patch("app.core.langgraph.nodes.step_020__golden_fast_gate.step_20__golden_fast_gate", fake_gate):
            state = await node_step_20(state)

        # Lookup finds NO match
        with patch(
            "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
            fake_golden_lookup_orch(match_found=False, high_confidence=False),
        ):
            state = await node_step_24(state)

        # No match found
        assert state.get("match_found") is False

        # Step 25: Golden hit check (routing decision)
        fake_hit = FakeOrchestrator({"golden_hit": False, "fallback_to_llm": True})
        with patch("app.core.langgraph.nodes.step_025__golden_hit.step_25__golden_hit", fake_hit):
            state = await node_step_25(state)

        # Should fallback
        assert state.get("golden_hit") is False
        assert state.get("fallback_to_llm") is True

    async def test_golden_not_eligible_skips_lookup(self):
        """Verify non-eligible queries skip golden lookup entirely."""
        state = make_state(messages=[{"role": "user", "content": "Complex query requiring LLM reasoning"}])

        # Golden gate NOT eligible
        fake_gate = FakeOrchestrator({"golden_eligible": False, "should_check_golden": False})
        with patch("app.core.langgraph.nodes.step_020__golden_fast_gate.step_20__golden_fast_gate", fake_gate):
            state = await node_step_20(state)

        # Not eligible - would route directly to LLM path
        assert state.get("golden_eligible") is False
        # Golden lookup should be skipped in routing


@pytest.mark.lane
@pytest.mark.phase8
class TestPhase8GoldenMetrics:
    """Test golden KB metrics and tracking."""

    async def test_golden_hit_tracks_faq_id(self):
        """Verify golden hit tracks FAQ ID for metrics."""
        state = state_golden_eligible()

        # High confidence match
        with patch(
            "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
            fake_golden_lookup_orch(match_found=True, high_confidence=True),
        ):
            state = await node_step_24(state)

        # FAQ ID tracked
        assert state.get("faq_id") == "faq-123"

        # Serve golden
        fake_serve = FakeOrchestrator(
            {"golden_served": True, "response": {"content": "Answer", "faq_id": "faq-123"}, "complete": True}
        )
        with patch("app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden", fake_serve):
            state = await node_step_28(state)

        # Metrics should include FAQ ID
        assert state.get("response", {}).get("faq_id") == "faq-123"

    async def test_golden_preserves_similarity_score(self):
        """Verify similarity score is preserved for analytics."""
        state = state_golden_eligible()

        with patch(
            "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
            fake_golden_lookup_orch(match_found=True, high_confidence=True),
        ):
            state = await node_step_24(state)

        # Similarity score preserved
        assert state.get("similarity_score") == 0.95
