"""Test cache hit path in Phase 4 lane."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Any, Dict

from app.core.langgraph.types import RAGState
from app.core.langgraph.nodes.step_059__check_cache import node_step_59
from app.core.langgraph.nodes.step_062__cache_hit import node_step_62
from app.core.langgraph.nodes.step_066__return_cached import node_step_66


class TestPhase4CacheHitPath:
    """Test suite for Phase 4 cache hit path."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_state = RAGState(
            messages=[{"role": "user", "content": "test message"}],
            session_id="test-session-123"
        )

    @patch('app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache')
    @patch('app.core.langgraph.nodes.step_059__check_cache.rag_step_log')
    @patch('app.core.langgraph.nodes.step_059__check_cache.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_59_cache_check(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 59: CheckCache node populates cache state."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            'cache_key': 'test-cache-key-123',
            'cached_response': {'content': 'cached response'},
            'epochs_resolved': True
        }

        # Execute
        result = await node_step_59(self.sample_state)

        # Assert cache state structure
        assert 'cache' in result
        assert result['cache']['key'] == 'test-cache-key-123'
        assert result['cache']['hit'] is True
        assert result['cache']['value'] == {'content': 'cached response'}

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(59)

    @patch('app.core.langgraph.nodes.step_062__cache_hit.step_62__cache_hit')
    @patch('app.core.langgraph.nodes.step_062__cache_hit.rag_step_log')
    @patch('app.core.langgraph.nodes.step_062__cache_hit.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_62_cache_hit_decision(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 62: CacheHit node sets decision for routing."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {}

        # Set up state with cache hit
        state_with_cache = self.sample_state.copy()
        state_with_cache['cache'] = {
            'key': 'test-key',
            'hit': True,
            'value': {'content': 'cached response'}
        }

        # Execute
        result = await node_step_62(state_with_cache)

        # Assert decision is set for routing
        assert result['cache_hit_decision'] is True

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(62)

    @patch('app.core.langgraph.nodes.step_062__cache_hit.step_62__cache_hit')
    @patch('app.core.langgraph.nodes.step_062__cache_hit.rag_step_log')
    @patch('app.core.langgraph.nodes.step_062__cache_hit.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_62_cache_miss_decision(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 62: CacheHit node with cache miss."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {}

        # Set up state with cache miss
        state_with_cache = self.sample_state.copy()
        state_with_cache['cache'] = {
            'key': 'test-key',
            'hit': False,
            'value': None
        }

        # Execute
        result = await node_step_62(state_with_cache)

        # Assert decision is set for routing
        assert result['cache_hit_decision'] is False

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(62)

    @patch('app.core.langgraph.nodes.step_066__return_cached.step_66__return_cached')
    @patch('app.core.langgraph.nodes.step_066__return_cached.rag_step_log')
    @patch('app.core.langgraph.nodes.step_066__return_cached.rag_step_timer')
    @pytest.mark.asyncio
    async def test_node_step_66_return_cached(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 66: ReturnCached node returns cached response."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            'response': {'content': 'cached response'},
            'cache_hit': True
        }

        # Set up state with cache hit
        state_with_cache = self.sample_state.copy()
        state_with_cache['cache'] = {
            'key': 'test-key',
            'hit': True,
            'value': {'content': 'cached response'}
        }

        # Execute
        result = await node_step_66(state_with_cache)

        # Assert cached response is returned
        assert result['returning_cached'] is True
        assert 'response' in result

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(66)

    @pytest.mark.asyncio
    async def test_cache_hit_flow_end_to_end(self):
        """Test complete cache hit flow: CheckCache → CacheHit → ReturnCached."""
        # This would be an integration test that verifies the entire flow
        # For now, we verify that the state keys are consistent across nodes

        # Step 59: CheckCache sets cache state
        with patch('app.core.langgraph.nodes.step_059__check_cache.step_59__check_cache') as mock_59:
            with patch('app.core.langgraph.nodes.step_059__check_cache.rag_step_timer'):
                mock_59.return_value = {
                    'cache_key': 'test-key',
                    'cached_response': {'content': 'cached'},
                }

                state_after_59 = await node_step_59(self.sample_state)

                # Verify cache state is populated
                assert state_after_59['cache']['hit'] is True
                assert state_after_59['cache']['key'] == 'test-key'

        # Step 62: CacheHit reads cache state and sets decision
        with patch('app.core.langgraph.nodes.step_062__cache_hit.step_62__cache_hit') as mock_62:
            with patch('app.core.langgraph.nodes.step_062__cache_hit.rag_step_timer'):
                mock_62.return_value = {}

                state_after_62 = await node_step_62(state_after_59)

                # Verify decision is set based on cache state
                assert state_after_62['cache_hit_decision'] is True

        # Step 66: ReturnCached should work with cache hit
        with patch('app.core.langgraph.nodes.step_066__return_cached.step_66__return_cached') as mock_66:
            with patch('app.core.langgraph.nodes.step_066__return_cached.rag_step_timer'):
                mock_66.return_value = {'returning_cached': True}

                state_after_66 = await node_step_66(state_after_62)

                # Verify cached response is returned
                assert state_after_66['returning_cached'] is True