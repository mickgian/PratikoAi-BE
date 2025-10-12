"""Test node wrapper for Step 42: Classification Confidence Check."""

import pytest
from unittest.mock import patch, AsyncMock

from app.core.langgraph.types import RAGState
from app.core.langgraph.nodes.step_042__class_confidence import node_step_42


class TestNodeStep42:
    """Test Step 42 node wrapper delegates to orchestrator correctly."""

    @pytest.mark.asyncio
    async def test_node_step_42_sufficient_confidence(self):
        """Test step 42 when classification exists with sufficient confidence."""
        with patch('app.core.langgraph.nodes.step_042__class_confidence.step_42__class_confidence', new_callable=AsyncMock) as mock_orchestrator:
            with patch('app.core.langgraph.types.logger'):
                # Mock orchestrator response with sufficient confidence
                mock_orchestrator.return_value = {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "classification_exists": True,
                    "confidence_sufficient": True,
                    "confidence_value": 0.85,
                    "threshold": 0.6,
                    "domain": "finance",
                    "action": "query",
                    "fallback_used": False,
                    "reasoning": "Clear financial query"
                }

                initial_state = RAGState({
                    "request_id": "test-confidence-123",
                    "classification": {
                        "domain": "finance",
                        "action": "query",
                        "confidence": 0.85,
                        "fallback_used": False
                    }
                })

                result = await node_step_42(initial_state)

                # Verify orchestrator was called
                mock_orchestrator.assert_called_once()
                call_args = mock_orchestrator.call_args
                assert "ctx" in call_args[1]

                # Verify confidence check result is in state
                assert isinstance(result, dict)
                assert "confidence_check" in result
                assert result["confidence_check"]["classification_exists"] is True
                assert result["confidence_check"]["confidence_sufficient"] is True
                assert result["confidence_check"]["confidence_value"] == 0.85
                assert result["confidence_check"]["threshold"] == 0.6

    @pytest.mark.asyncio
    async def test_node_step_42_insufficient_confidence(self):
        """Test step 42 when classification exists but confidence is too low."""
        with patch('app.core.langgraph.nodes.step_042__class_confidence.step_42__class_confidence', new_callable=AsyncMock) as mock_orchestrator:
            with patch('app.core.langgraph.types.logger'):
                # Mock orchestrator response with insufficient confidence
                mock_orchestrator.return_value = {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "classification_exists": True,
                    "confidence_sufficient": False,
                    "confidence_value": 0.45,
                    "threshold": 0.6,
                    "domain": "general",
                    "action": "query",
                    "fallback_used": True,
                    "reasoning": "Ambiguous query"
                }

                initial_state = RAGState({
                    "request_id": "test-low-confidence-456",
                    "classification": {
                        "domain": "general",
                        "action": "query",
                        "confidence": 0.45,
                        "fallback_used": True
                    }
                })

                result = await node_step_42(initial_state)

                # Verify insufficient confidence is flagged
                assert result["confidence_check"]["classification_exists"] is True
                assert result["confidence_check"]["confidence_sufficient"] is False
                assert result["confidence_check"]["confidence_value"] == 0.45
                assert result["confidence_check"]["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_node_step_42_no_classification(self):
        """Test step 42 when no classification exists."""
        with patch('app.core.langgraph.nodes.step_042__class_confidence.step_42__class_confidence', new_callable=AsyncMock) as mock_orchestrator:
            with patch('app.core.langgraph.types.logger'):
                # Mock orchestrator response with no classification
                mock_orchestrator.return_value = {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "classification_exists": False,
                    "confidence_sufficient": False,
                    "confidence_value": 0.0,
                    "threshold": 0.6,
                    "domain": None,
                    "action": None,
                    "fallback_used": False,
                    "reasoning": None
                }

                initial_state = RAGState({
                    "request_id": "test-no-class-789"
                })

                result = await node_step_42(initial_state)

                # Verify no classification is detected
                assert result["confidence_check"]["classification_exists"] is False
                assert result["confidence_check"]["confidence_sufficient"] is False
                assert result["confidence_check"]["confidence_value"] == 0.0
                assert result["confidence_check"]["domain"] is None

    @pytest.mark.asyncio
    async def test_node_step_42_state_preservation(self):
        """Test that existing state is preserved."""
        with patch('app.core.langgraph.nodes.step_042__class_confidence.step_42__class_confidence', new_callable=AsyncMock) as mock_orchestrator:
            with patch('app.core.langgraph.types.logger'):
                mock_orchestrator.return_value = {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "classification_exists": True,
                    "confidence_sufficient": True,
                    "confidence_value": 0.75,
                    "threshold": 0.6,
                    "domain": "hr",
                    "action": "info",
                    "fallback_used": False,
                    "reasoning": "HR query"
                }

                initial_state = RAGState({
                    "request_id": "test-preserve-001",
                    "session_id": "session-abc",
                    "classification": {
                        "domain": "hr",
                        "confidence": 0.75
                    },
                    "existing_data": "should_remain"
                })

                result = await node_step_42(initial_state)

                # Verify existing state is preserved
                assert result["request_id"] == "test-preserve-001"
                assert result["session_id"] == "session-abc"
                assert result["existing_data"] == "should_remain"
                # And new confidence check data is added
                assert "confidence_check" in result
                assert result["confidence_check"]["confidence_value"] == 0.75
