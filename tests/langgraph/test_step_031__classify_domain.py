"""Test node wrapper for Step 31: Classify Domain."""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime

from app.core.langgraph.types import RAGState
from app.core.langgraph.nodes.step_031__classify_domain import node_step_31


class TestNodeStep31:
    """Test Step 31 node wrapper delegates to orchestrator correctly."""

    @pytest.mark.asyncio
    async def test_node_step_31_successful_classification(self):
        """Test step 31 node wrapper with successful classification."""
        with patch('app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain', new_callable=AsyncMock) as mock_orchestrator:
            with patch('app.core.langgraph.types.logger'):
                # Mock orchestrator response
                mock_orchestrator.return_value = {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "classification": {"domain": "finance", "action": "query"},
                    "domain": "finance",
                    "action": "query",
                    "confidence": 0.85,
                    "fallback_used": False,
                    "query_length": 50,
                    "error": None
                }

                initial_state = RAGState({
                    "request_id": "test-classify-123",
                    "messages": [{"role": "user", "content": "What is my salary?"}],
                    "user_query": "What is my salary?"
                })

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
        with patch('app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain', new_callable=AsyncMock) as mock_orchestrator:
            with patch('app.core.langgraph.types.logger'):
                # Mock orchestrator response with fallback
                mock_orchestrator.return_value = {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "classification": {"domain": "tax", "action": "calculate"},
                    "domain": "tax",
                    "action": "calculate",
                    "confidence": 0.75,
                    "fallback_used": True,
                    "query_length": 100,
                    "error": None
                }

                initial_state = RAGState({
                    "request_id": "test-fallback-456",
                    "messages": [{"role": "user", "content": "Calculate my F24 taxes"}],
                    "user_query": "Calculate my F24 taxes"
                })

                result = await node_step_31(initial_state)

                # Verify fallback was indicated
                assert result["classification"]["fallback_used"] is True
                assert result["classification"]["domain"] == "tax"
                assert result["classification"]["confidence"] == 0.75

    @pytest.mark.asyncio
    async def test_node_step_31_classification_error(self):
        """Test step 31 when classification fails."""
        with patch('app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain', new_callable=AsyncMock) as mock_orchestrator:
            with patch('app.core.langgraph.types.logger'):
                # Mock orchestrator error response
                mock_orchestrator.return_value = {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "classification": None,
                    "domain": None,
                    "action": None,
                    "confidence": 0.0,
                    "fallback_used": False,
                    "query_length": 0,
                    "error": "No user query provided"
                }

                initial_state = RAGState({
                    "request_id": "test-error-789",
                    "messages": []
                })

                result = await node_step_31(initial_state)

                # Verify error is captured
                assert result["classification"]["error"] == "No user query provided"
                assert result["classification"]["domain"] is None
                assert result["classification"]["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_node_step_31_state_preservation(self):
        """Test that existing state is preserved."""
        with patch('app.core.langgraph.nodes.step_031__classify_domain.step_31__classify_domain', new_callable=AsyncMock) as mock_orchestrator:
            with patch('app.core.langgraph.types.logger'):
                mock_orchestrator.return_value = {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "classification": {"domain": "hr", "action": "info"},
                    "domain": "hr",
                    "action": "info",
                    "confidence": 0.90,
                    "fallback_used": False,
                    "query_length": 30,
                    "error": None
                }

                initial_state = RAGState({
                    "request_id": "test-preserve-001",
                    "session_id": "session-abc",
                    "user_query": "Tell me about benefits",
                    "existing_data": "should_remain"
                })

                result = await node_step_31(initial_state)

                # Verify existing state is preserved
                assert result["request_id"] == "test-preserve-001"
                assert result["session_id"] == "session-abc"
                assert result["existing_data"] == "should_remain"
                # And new classification data is added
                assert "classification" in result
                assert result["classification"]["domain"] == "hr"
