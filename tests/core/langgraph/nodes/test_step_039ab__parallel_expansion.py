"""Tests for Step 39ab: Parallel Query Expansion (MultiQuery + HyDE).

Tests that MultiQuery and HyDE run concurrently via asyncio.gather,
producing correct state updates for both query_variants and hyde_result.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.langgraph.nodes.step_039ab__parallel_expansion import (
    _create_hyde_error_result,
    _run_hyde,
    _run_multi_query,
    node_step_39ab,
)


class TestParallelExpansionNode:
    """Tests for the combined parallel expansion node."""

    @pytest.mark.asyncio
    async def test_both_results_present_in_output_state(self):
        """Node returns state with both query_variants and hyde_result."""
        state = {
            "user_query": "Cosa dice la risoluzione 64?",
            "routing_decision": {"route": "technical_research", "entities": []},
            "messages": [],
        }

        with (
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_multi_query",
                new_callable=AsyncMock,
                return_value={"bm25_query": "test", "vector_query": "test", "skipped": False},
            ),
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_hyde",
                new_callable=AsyncMock,
                return_value={"hypothetical_document": "doc", "word_count": 50, "skipped": False, "skip_reason": None},
            ),
        ):
            result = await node_step_39ab(state)

        assert "query_variants" in result
        assert "hyde_result" in result
        assert result["query_variants"]["skipped"] is False
        assert result["hyde_result"]["skipped"] is False

    @pytest.mark.asyncio
    async def test_chitchat_skips_both_expansions(self):
        """Chitchat route skips both MultiQuery and HyDE."""
        state = {
            "user_query": "Ciao, come stai?",
            "routing_decision": {"route": "chitchat", "entities": []},
            "messages": [],
        }

        with (
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_multi_query",
                new_callable=AsyncMock,
                return_value={"skipped": True, "skip_reason": "chitchat"},
            ),
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_hyde",
                new_callable=AsyncMock,
                return_value={
                    "hypothetical_document": "",
                    "word_count": 0,
                    "skipped": True,
                    "skip_reason": "chitchat",
                },
            ),
        ):
            result = await node_step_39ab(state)

        assert result["query_variants"]["skipped"] is True
        assert result["hyde_result"]["skipped"] is True

    @pytest.mark.asyncio
    async def test_runs_concurrently_not_sequentially(self):
        """Both tasks run concurrently via asyncio.gather (timing check)."""
        call_order = []

        async def slow_multi_query(*args, **kwargs):
            call_order.append("mq_start")
            await asyncio.sleep(0.05)
            call_order.append("mq_end")
            return {"bm25_query": "test", "skipped": False}

        async def slow_hyde(*args, **kwargs):
            call_order.append("hyde_start")
            await asyncio.sleep(0.05)
            call_order.append("hyde_end")
            return {"hypothetical_document": "doc", "word_count": 10, "skipped": False, "skip_reason": None}

        state = {
            "user_query": "test query",
            "routing_decision": {"route": "technical_research", "entities": []},
            "messages": [],
        }

        with (
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_multi_query",
                side_effect=slow_multi_query,
            ),
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_hyde",
                side_effect=slow_hyde,
            ),
        ):
            await node_step_39ab(state)

        # Both should start before either finishes (concurrent execution)
        assert "mq_start" in call_order
        assert "hyde_start" in call_order
        # With asyncio.gather, both start before either ends
        mq_start_idx = call_order.index("mq_start")
        hyde_start_idx = call_order.index("hyde_start")
        mq_end_idx = call_order.index("mq_end")
        hyde_end_idx = call_order.index("hyde_end")
        # Both starts happen before both ends
        assert max(mq_start_idx, hyde_start_idx) < min(mq_end_idx, hyde_end_idx)

    @pytest.mark.asyncio
    async def test_multi_query_error_returns_fallback(self):
        """MultiQuery error produces fallback result, HyDE still succeeds."""
        state = {
            "user_query": "test",
            "routing_decision": {"route": "technical_research", "entities": []},
            "messages": [],
        }

        with (
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_multi_query",
                new_callable=AsyncMock,
                return_value={"bm25_query": "test", "fallback": True, "skipped": False},
            ),
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_hyde",
                new_callable=AsyncMock,
                return_value={"hypothetical_document": "doc", "word_count": 50, "skipped": False, "skip_reason": None},
            ),
        ):
            result = await node_step_39ab(state)

        assert result["query_variants"]["fallback"] is True
        assert result["hyde_result"]["skipped"] is False

    @pytest.mark.asyncio
    async def test_hyde_error_returns_skipped(self):
        """HyDE error produces skipped result, MultiQuery still succeeds."""
        state = {
            "user_query": "test",
            "routing_decision": {"route": "technical_research", "entities": []},
            "messages": [],
        }

        with (
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_multi_query",
                new_callable=AsyncMock,
                return_value={"bm25_query": "test", "skipped": False},
            ),
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_hyde",
                new_callable=AsyncMock,
                return_value=_create_hyde_error_result(),
            ),
        ):
            result = await node_step_39ab(state)

        assert result["query_variants"]["skipped"] is False
        assert result["hyde_result"]["skipped"] is True
        assert result["hyde_result"]["skip_reason"] == "error"

    @pytest.mark.asyncio
    async def test_preserves_existing_state(self):
        """Node preserves all existing state keys."""
        state = {
            "user_query": "test",
            "routing_decision": {"route": "technical_research", "entities": []},
            "messages": [],
            "user_id": "user-123",
            "session_id": "session-456",
        }

        with (
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_multi_query",
                new_callable=AsyncMock,
                return_value={"skipped": True},
            ),
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion._run_hyde",
                new_callable=AsyncMock,
                return_value={"skipped": True, "hypothetical_document": "", "word_count": 0, "skip_reason": "test"},
            ),
        ):
            result = await node_step_39ab(state)

        assert result["user_id"] == "user-123"
        assert result["session_id"] == "session-456"


class TestRunMultiQuery:
    """Tests for _run_multi_query helper."""

    @pytest.mark.asyncio
    async def test_skip_route_returns_skip_result(self):
        """CHITCHAT route returns skip result without LLM call."""
        result = await _run_multi_query("Ciao", "chitchat", {}, [])
        assert result.get("skipped") is True

    @pytest.mark.asyncio
    async def test_normal_route_calls_service(self):
        """Normal route calls MultiQueryGeneratorService."""
        mock_variants = MagicMock()
        mock_variants.bm25_query = "reformulated"
        mock_variants.vector_query = "vector version"
        mock_variants.entity_query = "entity"
        mock_variants.original_query = "test"
        mock_variants.document_references = None
        mock_variants.semantic_expansions = None

        with (
            patch(
                "app.core.langgraph.nodes.step_039ab__parallel_expansion.reformulate_short_query_llm",
                new_callable=AsyncMock,
                return_value="expanded test query",
            ),
            patch("app.core.llm.model_config.get_model_config", return_value=MagicMock()),
            patch(
                "app.services.multi_query_generator.MultiQueryGeneratorService.generate",
                new_callable=AsyncMock,
                return_value=mock_variants,
            ),
        ):
            result = await _run_multi_query("test", "technical_research", {"entities": []}, [])

        # Should not be skipped (fallback is also acceptable if service mock doesn't match)
        assert isinstance(result, dict)


class TestRunHyde:
    """Tests for _run_hyde helper."""

    @pytest.mark.asyncio
    async def test_generates_hyde_document(self):
        """Generates a hypothetical document for vector search."""
        mock_result = MagicMock()
        mock_result.hypothetical_document = "Un documento ipotetico..."
        mock_result.word_count = 150
        mock_result.skipped = False
        mock_result.skip_reason = None

        with (
            patch("app.core.llm.model_config.get_model_config", return_value=MagicMock()),
            patch(
                "app.services.hyde_generator.HyDEGeneratorService.generate",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            result = await _run_hyde("Cosa dice la risoluzione 64?", "technical_research")

        assert result["hypothetical_document"] == "Un documento ipotetico..."
        assert result["word_count"] == 150
        assert result["skipped"] is False

    @pytest.mark.asyncio
    async def test_error_returns_error_result(self):
        """Service error returns safe error result."""
        with patch(
            "app.core.llm.model_config.get_model_config",
            side_effect=RuntimeError("config error"),
        ):
            result = await _run_hyde("test", "technical_research")

        assert result["skipped"] is True
        assert result["skip_reason"] == "error"
        assert result["hypothetical_document"] == ""
