"""Test node wrapper for Step 31: Classify Domain."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.langgraph.nodes.step_031__classify_domain import node_step_31
from app.core.langgraph.types import RAGState


class TestNodeStep31:
    """Test Step 31 node wrapper delegates to orchestrator correctly."""

    @pytest.mark.asyncio
    async def test_node_step_31_successful_classification(self):
        """Test step 31 node wrapper with successful classification."""
        with (
            patch(
                "app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            # Mock orchestrator response
            mock_orchestrator.return_value = {
                "timestamp": "2024-01-01T12:00:00Z",
                "classification": {"domain": "finance", "action": "query"},
                "domain": "finance",
                "action": "query",
                "confidence": 0.85,
                "fallback_used": False,
                "query_length": 50,
                "error": None,
            }

            initial_state = RAGState(
                {
                    "request_id": "test-classify-123",
                    "messages": [{"role": "user", "content": "What is my salary?"}],
                    "user_query": "What is my salary?",
                }
            )

            result = await node_step_31(initial_state)

            # Verify orchestrator was called
            mock_orchestrator.assert_called_once()
            call_args = mock_orchestrator.call_args
            assert "ctx" in call_args[1]

            # Verify classification data is in state
            assert isinstance(result, dict)
            assert "classification" in result
            assert result["classification"]["domain"] == "finance"
            assert result["classification"]["action"] == "query"
            assert result["classification"]["confidence"] == 0.85
            assert result["classification"]["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_node_step_31_with_llm_fallback(self):
        """Test step 31 when LLM fallback is used."""
        with (
            patch(
                "app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            # Mock orchestrator response with fallback
            mock_orchestrator.return_value = {
                "timestamp": "2024-01-01T12:00:00Z",
                "classification": {"domain": "tax", "action": "calculate"},
                "domain": "tax",
                "action": "calculate",
                "confidence": 0.75,
                "fallback_used": True,
                "query_length": 100,
                "error": None,
            }

            initial_state = RAGState(
                {
                    "request_id": "test-fallback-456",
                    "messages": [{"role": "user", "content": "Calculate my F24 taxes"}],
                    "user_query": "Calculate my F24 taxes",
                }
            )

            result = await node_step_31(initial_state)

            # Verify fallback was indicated
            assert result["classification"]["fallback_used"] is True
            assert result["classification"]["domain"] == "tax"
            assert result["classification"]["confidence"] == 0.75

    @pytest.mark.asyncio
    async def test_node_step_31_classification_error(self):
        """Test step 31 when classification fails."""
        with (
            patch(
                "app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            # Mock orchestrator error response
            mock_orchestrator.return_value = {
                "timestamp": "2024-01-01T12:00:00Z",
                "classification": None,
                "domain": None,
                "action": None,
                "confidence": 0.0,
                "fallback_used": False,
                "query_length": 0,
                "error": "No user query provided",
            }

            initial_state = RAGState({"request_id": "test-error-789", "messages": []})

            result = await node_step_31(initial_state)

            # Verify error is captured
            assert result["classification"]["error"] == "No user query provided"
            assert result["classification"]["domain"] is None
            assert result["classification"]["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_node_step_31_state_preservation(self):
        """Test that existing state is preserved."""
        with (
            patch(
                "app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            mock_orchestrator.return_value = {
                "timestamp": "2024-01-01T12:00:00Z",
                "classification": {"domain": "hr", "action": "info"},
                "domain": "hr",
                "action": "info",
                "confidence": 0.90,
                "fallback_used": False,
                "query_length": 30,
                "error": None,
            }

            initial_state = RAGState(
                {
                    "request_id": "test-preserve-001",
                    "session_id": "session-abc",
                    "user_query": "Tell me about benefits",
                    "existing_data": "should_remain",
                }
            )

            result = await node_step_31(initial_state)

            # Verify existing state is preserved
            assert result["request_id"] == "test-preserve-001"
            assert result["session_id"] == "session-abc"
            assert result["existing_data"] == "should_remain"
            # And new classification data is added
            assert "classification" in result
            assert result["classification"]["domain"] == "hr"

    @pytest.mark.asyncio
    async def test_node_step_31_query_composition_propagated(self):
        """Test that query_composition from orchestrator is copied to state.

        DEV-007 Issue 11: query_composition must be propagated for conditional
        prompt injection (document_analysis.md) to work.
        """
        with (
            patch(
                "app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            # Mock orchestrator returning query_composition for document analysis
            mock_orchestrator.return_value = {
                "timestamp": "2024-01-01T12:00:00Z",
                "classification": {"domain": "finance", "action": "analyze"},
                "domain": "finance",
                "action": "analyze",
                "confidence": 0.88,
                "fallback_used": False,
                "query_length": 40,
                "query_composition": "pure_doc",  # DEV-007: Document-only query
                "has_attachments": True,
                "error": None,
            }

            initial_state = RAGState(
                {
                    "request_id": "test-composition-123",
                    "messages": [{"role": "user", "content": "Analizza questo documento"}],
                    "user_query": "Analizza questo documento",
                    "attachments": [{"id": "doc-1", "filename": "test.xlsx"}],
                }
            )

            result = await node_step_31(initial_state)

            # CRITICAL: query_composition MUST be in state for prompting.py to use it
            assert "query_composition" in result
            assert result["query_composition"] == "pure_doc"

    @pytest.mark.asyncio
    async def test_node_step_31_query_composition_hybrid(self):
        """Test query_composition=hybrid for mixed document+KB queries."""
        with (
            patch(
                "app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            mock_orchestrator.return_value = {
                "timestamp": "2024-01-01T12:00:00Z",
                "domain": "tax",
                "action": "verify",
                "confidence": 0.82,
                "fallback_used": False,
                "query_length": 80,
                "query_composition": "hybrid",  # Document + KB query
                "has_attachments": True,
                "error": None,
            }

            initial_state = RAGState(
                {
                    "request_id": "test-hybrid-456",
                    "messages": [{"role": "user", "content": "Verifica il CUD secondo normativa INPS"}],
                    "user_query": "Verifica il CUD secondo normativa INPS",
                }
            )

            result = await node_step_31(initial_state)

            assert result["query_composition"] == "hybrid"

    @pytest.mark.asyncio
    async def test_node_step_31_query_composition_none_defaults_gracefully(self):
        """Test that missing query_composition doesn't break the node."""
        with (
            patch(
                "app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            # Old orchestrator response without query_composition
            mock_orchestrator.return_value = {
                "timestamp": "2024-01-01T12:00:00Z",
                "domain": "general",
                "action": "info",
                "confidence": 0.70,
                "fallback_used": False,
                "query_length": 20,
                "error": None,
                # NOTE: query_composition NOT in response (backward compatibility)
            }

            initial_state = RAGState(
                {
                    "request_id": "test-legacy-789",
                    "messages": [{"role": "user", "content": "Ciao!"}],
                    "user_query": "Ciao!",
                }
            )

            result = await node_step_31(initial_state)

            # Should have query_composition=None (not crash)
            assert "query_composition" in result
            assert result["query_composition"] is None
