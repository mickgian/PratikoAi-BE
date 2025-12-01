"""Unit tests for Golden Set Node Wrappers (Steps 24, 25, 28).

These tests protect critical bug fixes in the Golden Set retrieval flow:
- Bug #3: golden_match not mapped from Step 24 to Step 25
- Bug #6: golden_hit and golden_answer must be set at state TOP level (not nested)
- Bug #8: Step 28 must read answer from res["response"]["answer"], not res["answer"]

The tests verify that:
1. Step 24 correctly maps golden_match to state for Step 25 to consume
2. Step 25 correctly maps high_confidence_match to golden["hit"] and decisions["golden_hit"]
3. Step 28 correctly extracts answer from nested response structure
4. Step 28 sets golden_answer and golden_hit at TOP level state (not nested in golden dict)
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.langgraph.nodes.step_024__golden_lookup import node_step_24
from app.core.langgraph.nodes.step_025__golden_hit import node_step_25
from app.core.langgraph.nodes.step_028__serve_golden import node_step_28


# =============================================================================
# TestStep24GoldenLookupNodeWrapper - Bug #3 Regression Tests
# =============================================================================
class TestStep24GoldenLookupNodeWrapper:
    """Tests for Step 24: Golden Lookup node wrapper.

    Bug #3: golden_match was not being mapped from Step 24 output to state,
    causing Step 25 to not have access to the match data for confidence scoring.
    """

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_log")
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_timer")
    async def test_golden_match_mapped_to_state(self, mock_timer, mock_log, mock_orchestrator):
        """Test that res['golden_match'] is correctly mapped to state['golden_match'].

        This test protects against Bug #3 regression where golden_match data
        from Step 24 was not being passed to Step 25.
        """
        # Arrange
        mock_orchestrator.return_value = {
            "match_found": True,
            "golden_match": {
                "faq_id": "faq-12345",
                "question": "Come si calcola l'IVA?",
                "answer": "L'IVA si calcola applicando l'aliquota...",
                "similarity_score": 0.95,
                "source": "golden_set",
            },
            "high_confidence_match": True,
            "similarity_score": 0.95,
        }

        state = {
            "messages": [{"role": "user", "content": "Come si calcola l'IVA?"}],
            "request_id": "test-req-001",
        }

        # Configure mock timer context manager
        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_24(state)

        # Assert - CRITICAL: golden_match must be at TOP level for Step 25
        assert "golden_match" in result_state, "Bug #3 regression: golden_match must be at state top level for Step 25"
        assert result_state["golden_match"]["faq_id"] == "faq-12345"
        assert result_state["golden_match"]["similarity_score"] == 0.95
        assert result_state["golden_match"]["answer"] == "L'IVA si calcola applicando l'aliquota..."

        # Also verify it's stored in nested golden dict
        assert result_state["golden"]["match"] == result_state["golden_match"]

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_log")
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_timer")
    async def test_similarity_score_in_golden_match(self, mock_timer, mock_log, mock_orchestrator):
        """Test that similarity_score is correctly preserved in golden_match.

        Step 25 uses similarity_score to determine if match is high confidence (>= 0.90).
        """
        # Arrange
        similarity_value = 0.92
        mock_orchestrator.return_value = {
            "match_found": True,
            "golden_match": {
                "faq_id": "faq-99",
                "question": "Test question",
                "answer": "Test answer",
                "similarity_score": similarity_value,
            },
            "high_confidence_match": True,
            "similarity_score": similarity_value,
        }

        state = {
            "messages": [{"role": "user", "content": "Test query"}],
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_24(state)

        # Assert - similarity_score must be preserved
        assert result_state["golden_match"]["similarity_score"] == similarity_value
        # Also check mirrored top-level similarity_score
        assert result_state.get("similarity_score") == similarity_value

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_log")
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_timer")
    async def test_no_match_found_sets_match_found_false(self, mock_timer, mock_log, mock_orchestrator):
        """Test that when no golden match is found, match_found is correctly set to False."""
        # Arrange
        mock_orchestrator.return_value = {
            "match_found": False,
            "high_confidence_match": False,
        }

        state = {
            "messages": [{"role": "user", "content": "Obscure question"}],
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_24(state)

        # Assert
        assert result_state["golden"]["match_found"] is False
        assert result_state.get("match_found") is False
        assert "golden_match" not in result_state or result_state.get("golden_match") is None

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_log")
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_timer")
    async def test_golden_hit_mirrored_to_top_level(self, mock_timer, mock_log, mock_orchestrator):
        """Test that golden_hit is mirrored to state top level via mirror()."""
        # Arrange
        mock_orchestrator.return_value = {
            "match_found": True,
            "golden_match": {"faq_id": "faq-1", "answer": "Test"},
            "high_confidence_match": True,
        }

        state = {"messages": []}

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_24(state)

        # Assert - golden_hit should be mirrored
        assert result_state.get("golden_hit") is True


# =============================================================================
# TestStep25GoldenHitNodeWrapper - Bug #6 Regression Tests
# =============================================================================
class TestStep25GoldenHitNodeWrapper:
    """Tests for Step 25: Golden Hit decision node wrapper.

    Bug #6: golden_hit was only being set in nested golden dict, not at top level,
    causing routing logic to fail.
    """

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_025__golden_hit.step_25__golden_hit",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_log")
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_timer")
    async def test_high_confidence_maps_to_golden_hit(self, mock_timer, mock_log, mock_orchestrator):
        """Test that high_confidence_match maps to golden['hit'] and decisions['golden_hit'].

        This test verifies Bug #6 fix: high_confidence_match must update both
        golden['hit'] and decisions['golden_hit'] for routing logic.
        """
        # Arrange
        mock_orchestrator.return_value = {
            "high_confidence_match": True,
        }

        state = {
            "messages": [{"role": "user", "content": "Test"}],
            "golden_match": {
                "faq_id": "faq-123",
                "similarity_score": 0.95,
            },
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_25(state)

        # Assert - CRITICAL: Both locations must be set
        assert result_state["golden"]["hit"] is True, "golden['hit'] must be True when high_confidence_match is True"
        assert (
            result_state["decisions"]["golden_hit"] is True
        ), "decisions['golden_hit'] must be True for routing decisions"

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_025__golden_hit.step_25__golden_hit",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_log")
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_timer")
    async def test_low_confidence_maps_to_false(self, mock_timer, mock_log, mock_orchestrator):
        """Test that low confidence match (score < 0.90) sets golden_hit to False."""
        # Arrange
        mock_orchestrator.return_value = {
            "high_confidence_match": False,
        }

        state = {
            "messages": [],
            "golden_match": {
                "faq_id": "faq-456",
                "similarity_score": 0.85,  # Below threshold
            },
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_25(state)

        # Assert
        assert result_state["golden"]["hit"] is False
        assert result_state["decisions"]["golden_hit"] is False

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_025__golden_hit.step_25__golden_hit",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_log")
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_timer")
    async def test_decisions_dict_created_if_missing(self, mock_timer, mock_log, mock_orchestrator):
        """Test that decisions dict is created if not present in state."""
        # Arrange
        mock_orchestrator.return_value = {
            "high_confidence_match": True,
        }

        state = {
            "messages": [],
            # No decisions dict initially
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_25(state)

        # Assert
        assert "decisions" in result_state
        assert result_state["decisions"]["golden_hit"] is True

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_025__golden_hit.step_25__golden_hit",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_log")
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_timer")
    async def test_golden_dict_created_if_missing(self, mock_timer, mock_log, mock_orchestrator):
        """Test that golden dict is created if not present in state."""
        # Arrange
        mock_orchestrator.return_value = {
            "high_confidence_match": True,
        }

        state = {
            "messages": [],
            # No golden dict initially
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_25(state)

        # Assert
        assert "golden" in result_state
        assert result_state["golden"]["hit"] is True


# =============================================================================
# TestStep28ServeGoldenNodeWrapper - Bug #6 & #8 Regression Tests (CRITICAL)
# =============================================================================
class TestStep28ServeGoldenNodeWrapper:
    """Tests for Step 28: Serve Golden node wrapper.

    Bug #6: golden_hit and golden_answer must be set at state TOP level, not just nested.
    Bug #8: Answer must be extracted from res["response"]["answer"], not res["answer"].

    These are CRITICAL tests because Step 28 is the final step that serves the golden
    answer to the user. Incorrect data extraction breaks the entire golden set flow.
    """

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_answer_extracted_from_response_nested_key(self, mock_timer, mock_log, mock_orchestrator):
        """Test that answer is correctly extracted from res['response']['answer'].

        Bug #8: The orchestrator returns answer nested under 'response' key:
        res = {"response": {"answer": "...", "citations": [...]}}

        The node wrapper MUST extract from res["response"]["answer"],
        NOT from res["answer"] which would be None.
        """
        # Arrange
        expected_answer = "L'IVA (Imposta sul Valore Aggiunto) e calcolata..."
        expected_citations = [
            {"source": "DPR 633/72", "text": "Art. 1"},
        ]

        # Orchestrator returns NESTED structure
        mock_orchestrator.return_value = {
            "response": {
                "answer": expected_answer,
                "citations": expected_citations,
            },
            "complete": True,
        }

        state = {
            "messages": [{"role": "user", "content": "Come si calcola l'IVA?"}],
            "golden_match": {"faq_id": "faq-iva-001"},
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_28(state)

        # Assert - answer extracted correctly from nested structure
        assert (
            result_state["golden"]["answer"] == expected_answer
        ), "Bug #8 regression: answer must be extracted from res['response']['answer']"
        assert result_state["golden"]["citations"] == expected_citations

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_golden_answer_set_at_top_level(self, mock_timer, mock_log, mock_orchestrator):
        """Test that golden_answer is set at state TOP level, not just nested.

        Bug #6: The streaming response handler reads from state['golden_answer'],
        NOT from state['golden']['answer']. If golden_answer is not at top level,
        the streaming handler returns None.
        """
        # Arrange
        expected_answer = "La risposta e che..."

        mock_orchestrator.return_value = {
            "response": {
                "answer": expected_answer,
            },
            "complete": True,
        }

        state = {
            "messages": [],
            "golden_match": {"faq_id": "faq-1"},
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_28(state)

        # Assert - CRITICAL: golden_answer must be at TOP level
        assert "golden_answer" in result_state, "Bug #6 regression: golden_answer must exist at state top level"
        assert (
            result_state["golden_answer"] == expected_answer
        ), "Bug #6 regression: state['golden_answer'] must contain the answer string"

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_golden_answer_is_string_not_dict(self, mock_timer, mock_log, mock_orchestrator):
        """Test that golden_answer is a string, not a dict.

        If the node incorrectly assigns the entire response dict to golden_answer,
        the streaming handler will fail to serialize it properly.
        """
        # Arrange
        answer_text = "This is the golden answer text"

        mock_orchestrator.return_value = {
            "response": {
                "answer": answer_text,
                "citations": [],
                "metadata": {"source": "golden_set"},
            },
            "complete": True,
        }

        state = {"messages": [], "golden_match": {"faq_id": "faq-1"}}

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_28(state)

        # Assert - golden_answer must be a string
        assert isinstance(
            result_state["golden_answer"], str
        ), "golden_answer must be a string, not a dict or other type"
        assert result_state["golden_answer"] == answer_text

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_golden_hit_set_at_top_level(self, mock_timer, mock_log, mock_orchestrator):
        """Test that golden_hit is set to True at state TOP level after serving.

        Bug #6: The routing logic checks state['golden_hit'] to determine if
        a golden answer was served. This must be True after Step 28 completes.
        """
        # Arrange
        mock_orchestrator.return_value = {
            "response": {
                "answer": "Test answer",
            },
            "complete": True,
        }

        state = {
            "messages": [],
            "golden_match": {"faq_id": "faq-1"},
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_28(state)

        # Assert - CRITICAL: golden_hit must be True at top level
        assert "golden_hit" in result_state, "Bug #6 regression: golden_hit must exist at state top level"
        assert (
            result_state["golden_hit"] is True
        ), "Bug #6 regression: state['golden_hit'] must be True after serving golden answer"

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_golden_served_flag_set(self, mock_timer, mock_log, mock_orchestrator):
        """Test that golden['served'] is set to True after serving."""
        # Arrange
        mock_orchestrator.return_value = {
            "response": {
                "answer": "Test answer",
            },
            "complete": True,
        }

        state = {"messages": [], "golden_match": {"faq_id": "faq-1"}}

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_28(state)

        # Assert
        assert result_state["golden"]["served"] is True
        # Also check mirrored golden_served
        assert result_state.get("golden_served") is True

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_complete_flag_mirrored(self, mock_timer, mock_log, mock_orchestrator):
        """Test that complete flag from orchestrator is mirrored to state."""
        # Arrange
        mock_orchestrator.return_value = {
            "response": {
                "answer": "Done",
            },
            "complete": True,
        }

        state = {"messages": []}

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_28(state)

        # Assert
        assert result_state.get("complete") is True

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_handles_empty_answer_gracefully(self, mock_timer, mock_log, mock_orchestrator):
        """Test that empty/None answer is handled without setting golden_answer."""
        # Arrange
        mock_orchestrator.return_value = {
            "response": {
                "answer": None,  # No answer
            },
            "complete": False,
        }

        state = {"messages": []}

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_28(state)

        # Assert - golden_answer should not be set if answer is None/empty
        # The condition `if answer:` in node wrapper checks for truthy value
        assert result_state.get("golden_answer") is None

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_handles_missing_response_key_gracefully(self, mock_timer, mock_log, mock_orchestrator):
        """Test graceful handling when 'response' key is missing from orchestrator output."""
        # Arrange - orchestrator returns unexpected structure
        mock_orchestrator.return_value = {
            "answer": "Direct answer (wrong structure)",  # Wrong: should be in "response"
            "complete": True,
        }

        state = {"messages": []}

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_28(state)

        # Assert - should handle gracefully without crashing
        # answer will be None because res.get("response", {}).get("answer") returns None
        assert result_state.get("golden_answer") is None
        # golden_hit is still set to True (unconditionally in node wrapper)
        assert result_state["golden_hit"] is True
        assert result_state["golden"]["served"] is True

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_citations_stored_in_golden_dict(self, mock_timer, mock_log, mock_orchestrator):
        """Test that citations are correctly stored in golden dict."""
        # Arrange
        citations = [
            {"source": "Circolare 12/E", "text": "Art. 5 comma 3"},
            {"source": "DPR 633/72", "text": "Art. 1"},
        ]

        mock_orchestrator.return_value = {
            "response": {
                "answer": "Answer with citations",
                "citations": citations,
            },
            "complete": True,
        }

        state = {"messages": []}

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        result_state = await node_step_28(state)

        # Assert
        assert result_state["golden"]["citations"] == citations
        assert len(result_state["golden"]["citations"]) == 2


# =============================================================================
# Integration-style tests: End-to-end state flow between steps
# =============================================================================
class TestGoldenSetStateFlow:
    """Tests verifying correct state flow between Golden Set steps.

    These tests verify that the state mutations in each step are compatible
    with what subsequent steps expect to read.
    """

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_024__golden_lookup.step_24__golden_lookup",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_log")
    @patch("app.core.langgraph.nodes.step_024__golden_lookup.rag_step_timer")
    @patch(
        "app.core.langgraph.nodes.step_025__golden_hit.step_25__golden_hit",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_log")
    @patch("app.core.langgraph.nodes.step_025__golden_hit.rag_step_timer")
    async def test_step_24_output_consumed_by_step_25(
        self,
        mock_timer_25,
        mock_log_25,
        mock_orchestrator_25,
        mock_timer_24,
        mock_log_24,
        mock_orchestrator_24,
    ):
        """Test that Step 24 output can be consumed by Step 25.

        This verifies Bug #3 fix: golden_match from Step 24 must be accessible
        by Step 25 for confidence scoring.
        """
        # Arrange - Step 24 response
        mock_orchestrator_24.return_value = {
            "match_found": True,
            "golden_match": {
                "faq_id": "faq-flow-test",
                "question": "Test question",
                "answer": "Test answer",
                "similarity_score": 0.95,
            },
            "high_confidence_match": True,
            "similarity_score": 0.95,
        }

        # Step 25 will receive context and determine high_confidence
        mock_orchestrator_25.return_value = {
            "high_confidence_match": True,
        }

        initial_state = {
            "messages": [{"role": "user", "content": "Test"}],
        }

        # Configure mock timers
        for mock_timer in [mock_timer_24, mock_timer_25]:
            mock_timer.return_value.__enter__ = lambda s: None
            mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act - Simulate step flow
        state_after_24 = await node_step_24(initial_state)
        state_after_25 = await node_step_25(state_after_24)

        # Assert - Step 25 had access to golden_match
        mock_orchestrator_25.assert_called_once()
        call_kwargs = mock_orchestrator_25.call_args
        ctx_passed_to_25 = call_kwargs.kwargs.get("ctx") or call_kwargs[1].get("ctx")

        # Verify golden_match was in context passed to Step 25
        assert "golden_match" in ctx_passed_to_25, "Bug #3: golden_match must be passed to Step 25 orchestrator"
        assert ctx_passed_to_25["golden_match"]["faq_id"] == "faq-flow-test"

        # Verify final state has correct values
        assert state_after_25["decisions"]["golden_hit"] is True

    @pytest.mark.asyncio
    @patch(
        "app.core.langgraph.nodes.step_028__serve_golden.step_28__serve_golden",
        new_callable=AsyncMock,
    )
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_log")
    @patch("app.core.langgraph.nodes.step_028__serve_golden.rag_step_timer")
    async def test_step_28_final_state_ready_for_response_handler(self, mock_timer, mock_log, mock_orchestrator):
        """Test that Step 28 final state has all required fields for response handler.

        The response handler expects:
        - state["golden_hit"] = True (at TOP level)
        - state["golden_answer"] = "answer string" (at TOP level)
        """
        # Arrange
        mock_orchestrator.return_value = {
            "response": {
                "answer": "Final golden answer for user",
                "citations": [{"source": "test"}],
            },
            "complete": True,
        }

        state_before_28 = {
            "messages": [{"role": "user", "content": "Test"}],
            "golden_match": {"faq_id": "faq-final"},
            "golden": {"hit": True},
            "decisions": {"golden_hit": True},
        }

        mock_timer.return_value.__enter__ = lambda s: None
        mock_timer.return_value.__exit__ = lambda s, *args: None

        # Act
        final_state = await node_step_28(state_before_28)

        # Assert - All fields needed by response handler
        assert final_state["golden_hit"] is True, "Response handler needs state['golden_hit']"
        assert (
            final_state["golden_answer"] == "Final golden answer for user"
        ), "Response handler needs state['golden_answer']"
        assert isinstance(final_state["golden_answer"], str), "golden_answer must be string for serialization"
        assert final_state["golden"]["served"] is True
        assert final_state.get("complete") is True
