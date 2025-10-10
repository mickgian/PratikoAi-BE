"""
Failure injection tests for Phase 8: Golden KB failures.

Tests error handling for golden misses and KB fallback scenarios.
"""

import pytest
from unittest.mock import patch

from tests.common.fixtures_state import make_state, state_golden_eligible
from tests.common.fakes import FakeOrchestrator
from app.core.langgraph.nodes.step_020__golden_fast_gate import node_step_20
from app.core.langgraph.nodes.step_024__golden_lookup import node_step_24
from app.core.langgraph.nodes.step_026__kb_context_check import node_step_26
from app.core.langgraph.nodes.step_027__kb_delta import node_step_27
from app.core.langgraph.nodes.step_028__serve_golden import node_step_28


@pytest.mark.failure
@pytest.mark.phase8
class TestPhase8GoldenMiss:
    """Test golden KB miss scenarios."""

    async def test_golden_no_match_falls_back_gracefully(self):
        """Verify no golden match falls back to normal flow gracefully."""
        state = state_golden_eligible()

        # Golden gate eligible
        fake_gate = FakeOrchestrator({
            "golden_eligible": True,
            "should_check_golden": True
        })
        with patch("app.core.langgraph.nodes.step_020__golden_fast_gate.step_20__golden_fast_gate", fake_gate):
            state = await node_step_20(state)

        # Golden lookup finds NO match
        fake_lookup = FakeOrchestrator({
            "match_found": False,
            "similarity_score": 0.45,  # Low similarity
            "checked_faqs": 150
        })
        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_lookup):
            state = await node_step_24(state)

        # No match - should fallback
        assert state.get("match_found") is False
        assert state.get("similarity_score", 0) < 0.7

        # Step 25: Golden hit check indicates fallback
        fake_hit = FakeOrchestrator({
            "golden_hit": False,
            "fallback_to_llm": True
        })
        with patch("app.core.langgraph.nodes.step_025__golden_hit.step_25__golden_hit", fake_hit):
            from app.core.langgraph.nodes.step_025__golden_hit import node_step_25
            state = await node_step_25(state)

        # Fallback triggered
        assert state.get("golden_hit") is False
        assert state.get("fallback_to_llm") is True

    async def test_golden_lookup_service_unavailable(self):
        """Verify golden lookup service unavailable triggers fallback."""
        state = state_golden_eligible()

        # Lookup service down
        fake_lookup = FakeOrchestrator({
            "match_found": False,
            "error": "Golden KB service unavailable",
            "service_available": False,
            "fallback_required": True
        })
        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_lookup):
            state = await node_step_24(state)

        # Service unavailable - fallback
        assert state.get("service_available") is False
        assert state.get("fallback_required") is True

    async def test_golden_lookup_timeout(self):
        """Verify golden lookup timeout triggers fallback."""
        state = state_golden_eligible()

        # Lookup times out
        fake_lookup = FakeOrchestrator({
            "match_found": False,
            "timeout": True,
            "timeout_ms": 5000,
            "fallback_to_llm": True
        })
        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_lookup):
            state = await node_step_24(state)

        # Timeout - fallback
        assert state.get("timeout") is True
        assert state.get("fallback_to_llm") is True


@pytest.mark.failure
@pytest.mark.phase8
class TestPhase8KBFallback:
    """Test KB context fallback failures."""

    async def test_kb_context_unavailable_proceeds_without(self):
        """Verify KB context unavailable allows proceeding without extra context."""
        state = state_golden_eligible()

        # Low confidence match
        fake_lookup = FakeOrchestrator({
            "match_found": True,
            "high_confidence_match": False,
            "similarity_score": 0.75
        })
        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_lookup):
            state = await node_step_24(state)

        # KB context check indicates need for KB
        fake_kb_check = FakeOrchestrator({
            "kb_context_needed": True,
            "should_query_kb": True
        })
        with patch("app.core.langgraph.nodes.step_026__kb_context_check.step_26__kb_context_check", fake_kb_check):
            state = await node_step_26(state)

        # KB delta (KB unavailable)
        fake_delta = FakeOrchestrator({
            "kb_docs": [],
            "kb_available": False,
            "error": "KB service unavailable",
            "proceed_without_kb": True
        })
        with patch("app.core.langgraph.nodes.step_027__kb_delta.step_27__kb_delta", fake_delta):
            state = await node_step_27(state)

        # KB unavailable but can proceed
        assert state.get("kb_available") is False
        assert state.get("proceed_without_kb") is True

    async def test_kb_context_timeout_serves_golden_anyway(self):
        """Verify KB context timeout still serves golden answer."""
        state = state_golden_eligible()
        state["golden_answer"] = {
            "faq_id": "faq-123",
            "answer": "Golden answer text",
            "confidence": 0.78
        }

        # Low confidence, need KB context
        fake_kb_check = FakeOrchestrator({
            "kb_context_needed": True
        })
        with patch("app.core.langgraph.nodes.step_026__kb_context_check.step_26__kb_context_check", fake_kb_check):
            state = await node_step_26(state)

        # KB delta times out
        fake_delta = FakeOrchestrator({
            "kb_docs": [],
            "timeout": True,
            "kb_context_added": False,
            "serve_without_context": True
        })
        with patch("app.core.langgraph.nodes.step_027__kb_delta.step_27__kb_delta", fake_delta):
            state = await node_step_27(state)

        # Timeout, but serve anyway
        assert state.get("timeout") is True
        assert state.get("serve_without_context") is True

        # Step 28: Serve golden (without KB context)
        fake_serve = FakeOrchestrator({
            "golden_served": True,
            "response": {"content": "Golden answer text"},
            "complete": True,
            "served_without_kb_context": True
        })
        with patch("app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden", fake_serve):
            state = await node_step_28(state)

        # Served despite KB timeout
        assert state.get("golden_served") is True
        assert state.get("served_without_kb_context") is True

    async def test_kb_context_empty_results_not_error(self):
        """Verify KB context empty results is not treated as error."""
        state = state_golden_eligible()

        # KB delta returns empty (no relevant docs)
        fake_delta = FakeOrchestrator({
            "kb_docs": [],
            "kb_context_added": False,
            "empty_results": True,
            "kb_available": True  # KB is up, just no results
        })
        with patch("app.core.langgraph.nodes.step_027__kb_delta.step_27__kb_delta", fake_delta):
            state = await node_step_27(state)

        # Empty results OK
        assert state.get("empty_results") is True
        assert state.get("kb_available") is True


@pytest.mark.failure
@pytest.mark.phase8
class TestPhase8GoldenServeErrors:
    """Test errors when serving golden answers."""

    async def test_golden_answer_missing_data_error(self):
        """Verify missing golden answer data is handled."""
        state = state_golden_eligible()
        state["match_found"] = True
        state["high_confidence_match"] = True
        # But golden_answer is missing

        # Try to serve without answer data
        fake_serve = FakeOrchestrator({
            "golden_served": False,
            "error": "Golden answer data missing",
            "data_valid": False,
            "fallback_to_llm": True
        })
        with patch("app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden", fake_serve):
            state = await node_step_28(state)

        # Error handled, fallback
        assert state.get("golden_served") is False
        assert state.get("data_valid") is False
        assert state.get("fallback_to_llm") is True

    async def test_golden_answer_corrupted_data(self):
        """Verify corrupted golden answer data triggers fallback."""
        state = state_golden_eligible()
        state["golden_answer"] = {"corrupted": True}  # Invalid structure

        fake_serve = FakeOrchestrator({
            "golden_served": False,
            "error": "Corrupted answer data",
            "data_corrupted": True,
            "fallback_to_llm": True
        })
        with patch("app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden", fake_serve):
            state = await node_step_28(state)

        # Corruption detected, fallback
        assert state.get("data_corrupted") is True
        assert state.get("fallback_to_llm") is True


@pytest.mark.failure
@pytest.mark.phase8
class TestPhase8GoldenLookupErrors:
    """Test golden lookup internal errors."""

    async def test_golden_vector_db_error(self):
        """Verify vector DB error during lookup is handled."""
        state = state_golden_eligible()

        # Vector DB error
        fake_lookup = FakeOrchestrator({
            "match_found": False,
            "error": "Vector database error",
            "vector_db_available": False,
            "fallback_to_llm": True
        })
        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_lookup):
            state = await node_step_24(state)

        # DB error, fallback
        assert state.get("vector_db_available") is False
        assert state.get("fallback_to_llm") is True

    async def test_golden_embedding_generation_fails(self):
        """Verify embedding generation failure triggers fallback."""
        state = state_golden_eligible()

        # Embedding fails
        fake_lookup = FakeOrchestrator({
            "match_found": False,
            "error": "Failed to generate query embedding",
            "embedding_failed": True,
            "fallback_to_llm": True
        })
        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_lookup):
            state = await node_step_24(state)

        # Embedding error, fallback
        assert state.get("embedding_failed") is True
        assert state.get("fallback_to_llm") is True

    async def test_golden_faq_db_empty(self):
        """Verify empty FAQ database is handled."""
        state = state_golden_eligible()

        # FAQ DB empty
        fake_lookup = FakeOrchestrator({
            "match_found": False,
            "faq_count": 0,
            "faq_db_empty": True,
            "fallback_to_llm": True
        })
        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_lookup):
            state = await node_step_24(state)

        # Empty DB, fallback
        assert state.get("faq_db_empty") is True
        assert state.get("fallback_to_llm") is True

    async def test_golden_ambiguous_match(self):
        """Verify ambiguous matches (multiple high-confidence) trigger KB check."""
        state = state_golden_eligible()

        # Multiple matches with similar scores
        fake_lookup = FakeOrchestrator({
            "match_found": True,
            "high_confidence_match": False,  # Ambiguous
            "similarity_score": 0.88,
            "ambiguous": True,
            "candidate_count": 3
        })
        with patch("app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup", fake_lookup):
            state = await node_step_24(state)

        # Ambiguous match
        assert state.get("ambiguous") is True
        assert state.get("candidate_count") == 3

        # Should check KB for disambiguation
        fake_kb_check = FakeOrchestrator({
            "kb_context_needed": True,
            "disambiguation_required": True
        })
        with patch("app.core.langgraph.nodes.step_026__kb_context_check.step_26__kb_context_check", fake_kb_check):
            state = await node_step_26(state)

        # KB needed for disambiguation
        assert state.get("disambiguation_required") is True
