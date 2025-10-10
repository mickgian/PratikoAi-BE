"""
Parity tests for Phase 8: Golden KB Fast-Path Lane.

Verifies that golden lookup nodes correctly delegate to orchestrators
and handle both high-confidence and fallback paths.
"""

import pytest
from unittest.mock import patch

from tests.common.fixtures_state import make_state, state_golden_eligible
from tests.common.fakes import (
    fake_golden_lookup_orch,
    FakeOrchestrator,
)
from app.core.langgraph.nodes.step_020__golden_fast_gate import node_step_20
from app.core.langgraph.nodes.step_024__golden_lookup import node_step_24
from app.core.langgraph.nodes.step_028__serve_golden import node_step_28


@pytest.mark.parity
@pytest.mark.phase8
class TestPhase8GoldenGateParity:
    """Test golden fast-path gate node wrapper parity."""

    async def test_golden_gate_eligible_delegates(self):
        """Verify golden gate with eligible query delegates correctly."""
        state = state_golden_eligible()
        fake_orch = FakeOrchestrator({
            "golden_eligible": True,
            "should_check_golden": True
        })

        with patch("app.core.langgraph.nodes.step_020__golden_fast_gate.step_20__golden_fast_gate", fake_orch):
            result = await node_step_20(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify eligibility
        assert result.get("golden_eligible") is True
        assert result.get("should_check_golden") is True

    async def test_golden_gate_not_eligible_delegates(self):
        """Verify golden gate with ineligible query delegates correctly."""
        state = make_state(
            messages=[{"role": "user", "content": "Complex query that needs LLM"}]
        )
        fake_orch = FakeOrchestrator({
            "golden_eligible": False,
            "should_check_golden": False
        })

        with patch("app.core.langgraph.nodes.step_020__golden_fast_gate.step_20__golden_fast_gate", fake_orch):
            result = await node_step_20(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify not eligible
        assert result.get("golden_eligible") is False


@pytest.mark.parity
@pytest.mark.phase8
class TestPhase8GoldenLookupParity:
    """Test golden lookup node wrapper parity."""

    async def test_golden_lookup_high_confidence_delegates(self):
        """Verify golden lookup with high confidence match delegates correctly."""
        state = state_golden_eligible()
        fake_orch = fake_golden_lookup_orch(match_found=True, high_confidence=True)

        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_orch):
            result = await node_step_24(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify high confidence match
        assert result.get("match_found") is True
        assert result.get("high_confidence_match") is True
        assert result.get("similarity_score", 0) >= 0.95

    async def test_golden_lookup_low_confidence_delegates(self):
        """Verify golden lookup with low confidence match delegates correctly."""
        state = state_golden_eligible()
        fake_orch = fake_golden_lookup_orch(match_found=True, high_confidence=False)

        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_orch):
            result = await node_step_24(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify low confidence match
        assert result.get("match_found") is True
        assert result.get("high_confidence_match") is False
        assert result.get("similarity_score", 0) < 0.95

    async def test_golden_lookup_no_match_delegates(self):
        """Verify golden lookup with no match delegates correctly."""
        state = state_golden_eligible()
        fake_orch = fake_golden_lookup_orch(match_found=False, high_confidence=False)

        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_orch):
            result = await node_step_24(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify no match
        assert result.get("match_found") is False


@pytest.mark.parity
@pytest.mark.phase8
class TestPhase8ServeGoldenParity:
    """Test serve golden answer node wrapper parity."""

    async def test_serve_golden_delegates_correctly(self):
        """Verify serving golden answer delegates correctly."""
        state = state_golden_eligible()
        state["golden_answer"] = {
            "faq_id": "faq-123",
            "answer": "Golden answer text",
            "confidence": 0.98
        }

        fake_orch = FakeOrchestrator({
            "golden_served": True,
            "response": {
                "content": "Golden answer text",
                "source": "golden_kb",
                "faq_id": "faq-123"
            },
            "complete": True
        })

        with patch("app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden", fake_orch):
            result = await node_step_28(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify golden served
        assert result.get("golden_served") is True
        assert result.get("complete") is True

    async def test_serve_golden_preserves_match_metadata(self):
        """Verify serving golden preserves match metadata."""
        state = state_golden_eligible()
        state["golden_answer"] = {
            "faq_id": "faq-456",
            "answer": "Answer text",
            "confidence": 0.96,
            "category": "policy"
        }

        fake_orch = FakeOrchestrator({
            "golden_served": True,
            "response": {"content": "Answer text"},
            "complete": True
        })

        with patch("app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden", fake_orch):
            result = await node_step_28(state)

        # Golden answer metadata preserved
        assert result.get("golden_answer", {}).get("faq_id") == "faq-456"
        assert result.get("golden_answer", {}).get("category") == "policy"

    async def test_kb_context_check_delegates(self):
        """Verify KB context check delegates correctly for low confidence."""
        state = state_golden_eligible()
        state["match_found"] = True
        state["high_confidence_match"] = False
        state["similarity_score"] = 0.75

        fake_orch = FakeOrchestrator({
            "kb_context_needed": True,
            "should_query_kb": True
        })

        with patch("app.core.langgraph.nodes.step_026__kb_context_check.step_26__kb_context_check", fake_orch):
            from app.core.langgraph.nodes.step_026__kb_context_check import node_step_26
            result = await node_step_26(state)

        # Verify orchestrator was called
        assert fake_orch.call_count == 1

        # Verify KB context needed
        assert result.get("kb_context_needed") is True
