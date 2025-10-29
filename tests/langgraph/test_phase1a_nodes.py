"""Unit tests for Phase 1A RAG nodes."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Any, Dict

from app.core.langgraph.nodes import (
    node_step_1,
    node_step_3,
    node_step_6,
    node_step_9,
    node_step_59,
    node_step_62,
    node_step_64,
    node_step_67,
    node_step_112,
)
from app.schemas.graph import GraphState


class TestPhase1ANodes:
    """Test suite for Phase 1A node implementations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_state = GraphState(
            messages=[{"role": "user", "content": "test message"}],
            session_id="test-session-123"
        )

    @patch('app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request')
    @patch('app.core.langgraph.nodes.step_001__validate_request.rag_step_log')
    @patch('app.core.langgraph.nodes.step_001__validate_request.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_1_validate_request(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 1: ValidateRequest node."""
        # Setup - make timer a context manager
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {'request_valid': True, 'user_authenticated': True}

        # Execute
        result = await node_step_1(self.sample_state)

        # Assert
        assert isinstance(result, dict)
        assert result['request_valid'] is True
        assert result['user_authenticated'] is True
        assert 'ValidateRequest' in result['node_history']
        assert result['processing_stage'] == 'validated'

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()

        # Verify logging (calls should happen but counts may vary due to mocking complexity)
        assert mock_log.call_count >= 1  # at least one call
        # Check that the mock was called with expected parameters
        mock_log.assert_called()

    @patch('app.core.langgraph.nodes.step_003__valid_check.step_3__valid_check')
    @patch('app.observability.rag_logging.rag_step_log')
    @patch('app.observability.rag_logging.rag_step_timer')
    def test_node_step_3_valid_request(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 3: ValidCheck node with valid request."""
        # Setup
        mock_timer.return_value.__enter__ = Mock()
        mock_timer.return_value.__exit__ = Mock()
        mock_orchestrator.return_value = {'request_valid': True}

        # Execute
        result = node_step_3(self.sample_state)

        # Assert
        assert result['request_valid'] is True
        assert result['gdpr_logged'] is True
        assert result['next_node'] == 'PrivacyCheck'
        assert 'ValidCheck' in result['node_history']

    @patch('app.core.langgraph.nodes.step_003__valid_check.step_3__valid_check')
    @patch('app.observability.rag_logging.rag_step_log')
    @patch('app.observability.rag_logging.rag_step_timer')
    def test_node_step_3_invalid_request(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 3: ValidCheck node with invalid request."""
        # Setup
        mock_timer.return_value.__enter__ = Mock()
        mock_timer.return_value.__exit__ = Mock()
        mock_orchestrator.return_value = {'request_valid': False}

        # Execute
        result = node_step_3(self.sample_state)

        # Assert
        assert result['request_valid'] is False
        assert result['error_code'] == 400
        assert result['next_node'] == 'End'

    @patch('app.core.langgraph.nodes.step_006__privacy_check.step_6__privacy_check')
    @patch('app.observability.rag_logging.rag_step_log')
    @patch('app.observability.rag_logging.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_6_privacy_enabled(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 6: PrivacyCheck node with privacy enabled."""
        # Setup
        mock_timer.return_value.__enter__ = Mock()
        mock_timer.return_value.__exit__ = Mock()
        mock_orchestrator.return_value = {'privacy_enabled': True}

        # Execute
        result = await node_step_6(self.sample_state)

        # Assert
        assert result['privacy_enabled'] is True
        assert result['anonymized'] is True
        assert result['next_node'] == 'PIICheck'

    @patch('app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache')
    @patch('app.observability.rag_logging.rag_step_log')
    @patch('app.observability.rag_logging.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_59_check_cache(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 59: CheckCache node."""
        # Setup
        mock_timer.return_value.__enter__ = Mock()
        mock_timer.return_value.__exit__ = Mock()
        mock_orchestrator.return_value = {}

        # Execute
        result = await node_step_59(self.sample_state)

        # Assert
        assert result['epochs_resolved'] is True
        assert 'cache_key' in result
        assert result['next_node'] == 'CacheHit'

    @patch('app.core.langgraph.nodes.step_062__cache_hit.step_62__cache_hit')
    @patch('app.observability.rag_logging.rag_step_log')
    @patch('app.observability.rag_logging.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_62_cache_hit(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 62: CacheHit node with cache hit."""
        # Setup
        mock_timer.return_value.__enter__ = Mock()
        mock_timer.return_value.__exit__ = Mock()
        mock_orchestrator.return_value = {'cache_hit': True}

        # Execute
        result = await node_step_62(self.sample_state)

        # Assert
        assert result['cache_hit'] is True
        assert result['cache_hit_tracked'] is True
        assert result['next_node'] == 'End'

    @patch('app.core.langgraph.nodes.step_062__cache_hit.step_62__cache_hit')
    @patch('app.observability.rag_logging.rag_step_log')
    @patch('app.observability.rag_logging.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_62_cache_miss(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 62: CacheHit node with cache miss."""
        # Setup
        mock_timer.return_value.__enter__ = Mock()
        mock_timer.return_value.__exit__ = Mock()
        mock_orchestrator.return_value = {'cache_hit': False}

        # Execute
        result = await node_step_62(self.sample_state)

        # Assert
        assert result['cache_hit'] is False
        assert result['next_node'] == 'LLMCall'

    @patch('app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall')
    @patch('app.observability.rag_logging.rag_step_log')
    @patch('app.observability.rag_logging.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_64_llm_call(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 64: LLMCall node."""
        # Setup
        mock_timer.return_value.__enter__ = Mock()
        mock_timer.return_value.__exit__ = Mock()
        mock_orchestrator.return_value = {'llm_response': 'test response'}

        # Execute
        result = await node_step_64(self.sample_state)

        # Assert
        assert result['llm_response'] == 'test response'
        assert result['next_node'] == 'LLMSuccess'
        assert 'LLMCall' in result['node_history']

    @patch('app.core.langgraph.nodes.step_067__llm_success.step_67__llmsuccess')
    @patch('app.observability.rag_logging.rag_step_log')
    @patch('app.observability.rag_logging.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_67_llm_success(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 67: LLMSuccess node."""
        # Setup
        mock_timer.return_value.__enter__ = Mock()
        mock_timer.return_value.__exit__ = Mock()
        mock_orchestrator.return_value = {'llm_success': True}

        # Execute
        result = await node_step_67(self.sample_state)

        # Assert
        assert result['llm_success'] is True
        assert result['response_cached'] is True
        assert result['usage_tracked'] is True
        assert result['next_node'] == 'End'

    @patch('app.core.langgraph.nodes.step_112__end.step_112__end')
    @patch('app.observability.rag_logging.rag_step_log')
    @patch('app.observability.rag_logging.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_112_end_with_llm_response(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 112: End node with LLM response."""
        # Setup
        mock_timer.return_value.__enter__ = Mock()
        mock_timer.return_value.__exit__ = Mock()
        mock_orchestrator.return_value = {}

        state_with_response = GraphState(
            messages=[{"role": "user", "content": "test"}],
            session_id="test-session"
        )
        state_dict = state_with_response.model_dump()
        state_dict['llm_response'] = 'test llm response'

        # Execute
        result = await node_step_112(state_dict)

        # Assert
        assert result['final_response']['content'] == 'test llm response'
        assert result['final_response']['source'] == 'llm'
        assert result['processing_stage'] == 'completed'
        assert 'End' in result['node_history']