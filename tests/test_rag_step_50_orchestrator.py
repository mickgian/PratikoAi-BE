#!/usr/bin/env python3
"""
Tests for RAG STEP 50 Orchestrator — Routing strategy decision

This test file specifically tests the orchestrator function step_50__strategy_type
to ensure it properly handles routing strategy decisions.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.schemas.chat import Message
from app.core.llm.factory import RoutingStrategy


class TestRAGStep50Orchestrator:
    """Test suite for RAG STEP 50 orchestrator function"""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_cost_optimized_decision(self, mock_logger, mock_rag_log):
        """Test Step 50 orchestrator: COST_OPTIMIZED routing decision"""
        from app.orchestrators.platform import step_50__strategy_type

        messages = [
            Message(role="user", content="Calculate my tax deductions")
        ]

        # Context from Step 49
        ctx = {
            'routing_strategy': RoutingStrategy.COST_OPTIMIZED,
            'messages': messages,
            'provider': MagicMock(),
            'provider_type': 'openai',
            'model': 'gpt-4',
            'max_cost_eur': 0.5,
            'preferred_provider': 'openai'
        }

        # Call the orchestrator function
        result = step_50__strategy_type(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result['decision'] == 'routing_to_cost_optimized'
        assert result['next_step'] == 'CheapProvider'
        assert result['routing_strategy'] == 'cost_optimized'
        assert result['provider_type'] == 'openai'
        assert result['model'] == 'gpt-4'
        assert result['max_cost_eur'] == 0.5
        assert result['preferred_provider'] == 'openai'
        assert result['messages'] == messages
        assert 'timestamp' in result

        # Verify logging was called
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args
        assert 'Routing strategy decision completed' in log_call[0][0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_quality_first_decision(self, mock_logger, mock_rag_log):
        """Test Step 50 orchestrator: QUALITY_FIRST routing decision"""
        from app.orchestrators.platform import step_50__strategy_type

        messages = [
            Message(role="user", content="Complex legal analysis")
        ]

        ctx = {
            'routing_strategy': RoutingStrategy.QUALITY_FIRST,
            'messages': messages,
            'provider': MagicMock(),
            'provider_type': 'anthropic',
            'model': 'claude-3',
            'max_cost_eur': 2.0
        }

        result = step_50__strategy_type(ctx=ctx)

        assert result['decision'] == 'routing_to_quality_first'
        assert result['next_step'] == 'BestProvider'
        assert result['routing_strategy'] == 'quality_first'
        assert result['provider_type'] == 'anthropic'
        assert result['model'] == 'claude-3'
        assert result['max_cost_eur'] == 2.0

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_balanced_decision(self, mock_logger, mock_rag_log):
        """Test Step 50 orchestrator: BALANCED routing decision"""
        from app.orchestrators.platform import step_50__strategy_type

        messages = [Message(role="user", content="Standard query")]

        ctx = {
            'routing_strategy': RoutingStrategy.BALANCED,
            'messages': messages,
            'provider': MagicMock(),
            'max_cost_eur': 1.0
        }

        result = step_50__strategy_type(ctx=ctx)

        assert result['decision'] == 'routing_to_balanced'
        assert result['next_step'] == 'BalanceProvider'
        assert result['routing_strategy'] == 'balanced'
        assert result['max_cost_eur'] == 1.0

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_failover_decision(self, mock_logger, mock_rag_log):
        """Test Step 50 orchestrator: FAILOVER routing decision"""
        from app.orchestrators.platform import step_50__strategy_type

        messages = [Message(role="user", content="Important query")]

        ctx = {
            'routing_strategy': RoutingStrategy.FAILOVER,
            'messages': messages,
            'provider': MagicMock(),
            'max_cost_eur': 1.5
        }

        result = step_50__strategy_type(ctx=ctx)

        assert result['decision'] == 'routing_to_failover'
        assert result['next_step'] == 'PrimaryProvider'
        assert result['routing_strategy'] == 'failover'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_unsupported_strategy_fallback(self, mock_logger, mock_rag_log):
        """Test Step 50 orchestrator: Fallback for unsupported routing strategy"""
        from app.orchestrators.platform import step_50__strategy_type

        messages = [Message(role="user", content="Test query")]

        # Create a mock unsupported strategy
        unsupported_strategy = MagicMock()
        unsupported_strategy.value = "unsupported_strategy"

        ctx = {
            'routing_strategy': unsupported_strategy,
            'messages': messages,
            'provider': MagicMock()
        }

        result = step_50__strategy_type(ctx=ctx)

        # Should fallback to balanced
        assert result['decision'] == 'routing_fallback_to_balanced'
        assert result['next_step'] == 'BalanceProvider'
        assert result['routing_strategy'] == 'unsupported_strategy'
        assert result['fallback_reason'] == 'unsupported_strategy'

        # Verify warning was logged
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_missing_routing_strategy(self, mock_logger, mock_rag_log):
        """Test Step 50 orchestrator: Handle missing routing strategy"""
        from app.orchestrators.platform import step_50__strategy_type

        messages = [Message(role="user", content="Test query")]

        ctx = {
            'messages': messages,
            'provider': MagicMock()
            # Missing routing_strategy
        }

        result = step_50__strategy_type(ctx=ctx)

        assert result['decision'] == 'routing_strategy_missing'
        assert result['next_step'] is None
        assert result['error'] == 'Missing required parameter: routing_strategy'

        # Verify error was logged
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 50 orchestrator: Parameters passed via kwargs"""
        from app.orchestrators.platform import step_50__strategy_type

        messages = [Message(role="user", content="Test query")]

        # Call with kwargs instead of ctx
        result = step_50__strategy_type(
            messages=messages,
            routing_strategy=RoutingStrategy.BALANCED,
            provider=MagicMock(),
            max_cost_eur=0.8,
            user_id='user_789'
        )

        assert result['decision'] == 'routing_to_balanced'
        assert result['next_step'] == 'BalanceProvider'
        assert result['messages'] == messages
        assert result['max_cost_eur'] == 0.8
        assert result['user_id'] == 'user_789'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_timer')
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_performance_tracking(self, mock_logger, mock_rag_log, mock_timer):
        """Test Step 50 orchestrator: Performance tracking with timer"""
        from app.orchestrators.platform import step_50__strategy_type

        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        messages = [Message(role="user", content="Test")]

        step_50__strategy_type(ctx={
            'messages': messages,
            'routing_strategy': RoutingStrategy.COST_OPTIMIZED,
            'provider': MagicMock()
        })

        # Verify timer was used
        mock_timer.assert_called_with(
            50,
            'RAG.platform.routing.strategy',
            'StrategyType',
            stage='start'
        )

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 50 orchestrator: Comprehensive logging format"""
        from app.orchestrators.platform import step_50__strategy_type

        messages = [
            Message(role="system", content="You are an assistant"),
            Message(role="user", content="Help me with taxes")
        ]

        ctx = {
            'routing_strategy': RoutingStrategy.QUALITY_FIRST,
            'messages': messages,
            'provider': MagicMock(),
            'provider_type': 'anthropic',
            'model': 'claude-3',
            'max_cost_eur': 1.5,
            'preferred_provider': 'anthropic',
            'user_id': 'user_123',
            'session_id': 'session_456',
            'complexity': 'high'
        }

        result = step_50__strategy_type(ctx=ctx)

        # Verify result
        assert result['decision'] == 'routing_to_quality_first'
        assert result['next_step'] == 'BestProvider'

        # Verify comprehensive logging was called
        mock_rag_log.assert_called()
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label', 'decision',
            'routing_strategy', 'next_step', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]['step'] == 50
        assert log_call[1]['step_id'] == 'RAG.platform.routing.strategy'
        assert log_call[1]['node_label'] == 'StrategyType'
        assert log_call[1]['decision'] == 'routing_to_quality_first'
        assert log_call[1]['routing_strategy'] == 'quality_first'
        assert log_call[1]['next_step'] == 'BestProvider'
        assert log_call[1]['messages_count'] == 2
        assert log_call[1]['preferred_provider'] == 'anthropic'
        assert log_call[1]['complexity'] == 'high'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_50_ready_for_provider_steps(self, mock_logger, mock_rag_log):
        """Test Step 50 orchestrator: Output is ready for provider steps (51-58)"""
        from app.orchestrators.platform import step_50__strategy_type

        messages = [Message(role="user", content="Tax calculation")]

        ctx = {
            'routing_strategy': RoutingStrategy.BALANCED,
            'messages': messages,
            'provider': MagicMock(),
            'provider_type': 'openai',
            'model': 'gpt-4',
            'max_cost_eur': 1.0,
            'preferred_provider': 'openai'
        }

        result = step_50__strategy_type(ctx=ctx)

        # Verify output is properly formatted for provider steps
        assert result['decision'] == 'routing_to_balanced'
        assert result['next_step'] == 'BalanceProvider'
        assert 'provider' in result
        assert 'routing_strategy' in result
        assert 'provider_type' in result
        assert 'model' in result
        assert 'messages' in result

        # Verify all necessary data is preserved for provider steps
        assert result['provider_type'] == 'openai'
        assert result['model'] == 'gpt-4'
        assert result['max_cost_eur'] == 1.0
        assert result['preferred_provider'] == 'openai'
        assert result['messages'] == messages

        # Verify the result structure is compatible with provider steps' expected input
        assert isinstance(result, dict)
        expected_keys = [
            'decision', 'next_step', 'routing_strategy', 'provider',
            'provider_type', 'model', 'max_cost_eur', 'messages', 'timestamp'
        ]
        assert all(key in result for key in expected_keys)