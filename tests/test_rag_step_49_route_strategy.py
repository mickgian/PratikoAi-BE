#!/usr/bin/env python3
"""
Tests for RAG STEP 49 — LLMFactory.get_optimal_provider Apply routing strategy

This step applies the routing strategy using LLMFactory to select the optimal provider.
It receives context from Step 48 and prepares for Step 50 (strategy type decision).
"""

from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from app.schemas.chat import Message
from app.core.llm.factory import RoutingStrategy
from app.core.llm.base import LLMProviderType
from app.core.llm.providers.openai_provider import OpenAIProvider


class TestRAGStep49RouteStrategy:
    """Test suite for RAG STEP 49 - Apply routing strategy"""

    @pytest.fixture
    def mock_openai_provider(self):
        """Mock OpenAI provider."""
        provider = MagicMock(spec=OpenAIProvider)
        provider.provider_type = LLMProviderType.OPENAI
        provider.model = "gpt-4"
        return provider

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.orchestrators.facts.get_llm_factory')
    async def test_step_49_apply_routing_strategy_success(self, mock_get_factory, mock_logger, mock_rag_log, mock_openai_provider):
        """Test Step 49: Successfully apply routing strategy"""
        from app.orchestrators.facts import step_49__route_strategy

        # Mock factory
        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_openai_provider
        mock_get_factory.return_value = mock_factory

        messages = [
            Message(role="user", content="Calculate my tax deductions")
        ]

        # Context from Step 48
        ctx = {
            'messages': messages,
            'routing_strategy': RoutingStrategy.COST_OPTIMIZED,
            'max_cost_eur': 0.5,
            'preferred_provider': 'openai',
            'user_id': 'user_123',
            'session_id': 'session_456'
        }

        # Call the orchestrator function
        result = step_49__route_strategy(ctx=ctx)

        # Verify factory was called correctly
        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=messages,
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=0.5,
            preferred_provider='openai'
        )

        # Verify result structure
        assert isinstance(result, dict)
        assert result['routing_applied'] is True
        assert result['provider'] == mock_openai_provider
        assert result['routing_strategy'] == RoutingStrategy.COST_OPTIMIZED
        assert result['provider_type'] == LLMProviderType.OPENAI.value
        assert result['model'] == 'gpt-4'

        # Verify logging
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.orchestrators.facts.get_llm_factory')
    async def test_step_49_quality_first_strategy(self, mock_get_factory, mock_logger, mock_rag_log, mock_openai_provider):
        """Test Step 49: Apply quality-first routing strategy"""
        from app.orchestrators.facts import step_49__route_strategy

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_openai_provider
        mock_get_factory.return_value = mock_factory

        messages = [
            Message(role="user", content="Complex legal document analysis")
        ]

        ctx = {
            'messages': messages,
            'routing_strategy': RoutingStrategy.QUALITY_FIRST,
            'max_cost_eur': 2.0
        }

        result = step_49__route_strategy(ctx=ctx)

        # Verify quality-first strategy was applied
        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=2.0,
            preferred_provider=None
        )

        assert result['routing_strategy'] == RoutingStrategy.QUALITY_FIRST
        assert result['routing_applied'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.orchestrators.facts.get_llm_factory')
    async def test_step_49_handle_factory_error(self, mock_get_factory, mock_logger, mock_rag_log):
        """Test Step 49: Handle factory error gracefully"""
        from app.orchestrators.facts import step_49__route_strategy

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.side_effect = ValueError("No providers configured")
        mock_get_factory.return_value = mock_factory

        messages = [Message(role="user", content="Test query")]

        ctx = {
            'messages': messages,
            'routing_strategy': RoutingStrategy.BALANCED
        }

        result = step_49__route_strategy(ctx=ctx)

        # Should handle error gracefully
        assert result['routing_applied'] is False
        assert result['error'] == "No providers configured"
        assert result['provider'] is None

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_49_missing_messages(self, mock_logger, mock_rag_log):
        """Test Step 49: Handle missing messages"""
        from app.orchestrators.facts import step_49__route_strategy

        ctx = {
            'routing_strategy': RoutingStrategy.COST_OPTIMIZED
            # Missing messages
        }

        result = step_49__route_strategy(ctx=ctx)

        assert result['routing_applied'] is False
        assert result['error'] == 'Missing required parameter: messages'

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.orchestrators.facts.get_llm_factory')
    async def test_step_49_balanced_strategy_with_budget(self, mock_get_factory, mock_logger, mock_rag_log, mock_openai_provider):
        """Test Step 49: Balanced strategy with budget constraint"""
        from app.orchestrators.facts import step_49__route_strategy

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_openai_provider
        mock_get_factory.return_value = mock_factory

        messages = [Message(role="user", content="Standard query")]

        ctx = {
            'messages': messages,
            'routing_strategy': RoutingStrategy.BALANCED,
            'max_cost_eur': 1.0,
            'preferred_provider': 'anthropic'
        }

        result = step_49__route_strategy(ctx=ctx)

        # Verify balanced strategy parameters
        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=messages,
            strategy=RoutingStrategy.BALANCED,
            max_cost_eur=1.0,
            preferred_provider='anthropic'
        )

        assert result['routing_applied'] is True
        assert result['routing_strategy'] == RoutingStrategy.BALANCED
        assert result['max_cost_eur'] == 1.0

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.orchestrators.facts.get_llm_factory')
    async def test_step_49_kwargs_parameters(self, mock_get_factory, mock_logger, mock_rag_log, mock_openai_provider):
        """Test Step 49: Parameters passed via kwargs"""
        from app.orchestrators.facts import step_49__route_strategy

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_openai_provider
        mock_get_factory.return_value = mock_factory

        messages = [Message(role="user", content="Test")]

        # Call with kwargs instead of ctx
        result = step_49__route_strategy(
            messages=messages,
            routing_strategy=RoutingStrategy.FAILOVER,
            preferred_provider='openai',
            fallback_provider='anthropic'
        )

        assert result['routing_applied'] is True
        assert result['routing_strategy'] == RoutingStrategy.FAILOVER
        assert result['provider'] == mock_openai_provider

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_timer')
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.orchestrators.facts.get_llm_factory')
    async def test_step_49_performance_tracking(self, mock_get_factory, mock_logger, mock_rag_log, mock_timer, mock_openai_provider):
        """Test Step 49: Performance tracking with timer"""
        from app.orchestrators.facts import step_49__route_strategy

        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_openai_provider
        mock_get_factory.return_value = mock_factory

        messages = [Message(role="user", content="Test")]

        step_49__route_strategy(ctx={'messages': messages, 'routing_strategy': RoutingStrategy.COST_OPTIMIZED})

        # Verify timer was used
        mock_timer.assert_called_with(
            49,
            'RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy',
            'RouteStrategy',
            stage='start'
        )

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.orchestrators.facts.get_llm_factory')
    async def test_step_49_ready_for_step_50(self, mock_get_factory, mock_logger, mock_rag_log, mock_openai_provider):
        """Test Step 49: Output ready for Step 50 (StrategyType decision)"""
        from app.orchestrators.facts import step_49__route_strategy

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_openai_provider
        mock_get_factory.return_value = mock_factory

        messages = [Message(role="user", content="Test")]

        ctx = {
            'messages': messages,
            'routing_strategy': RoutingStrategy.COST_OPTIMIZED,
            'max_cost_eur': 0.5
        }

        result = step_49__route_strategy(ctx=ctx)

        # Verify output is ready for Step 50
        assert result['ready_for_decision'] is True
        assert 'provider' in result
        assert 'routing_strategy' in result
        assert 'provider_type' in result
        assert 'model' in result

        # These fields needed for Step 50 decision
        assert isinstance(result['routing_strategy'], RoutingStrategy)
        assert result['provider'] is not None

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.orchestrators.facts.get_llm_factory')
    async def test_step_49_comprehensive_logging(self, mock_get_factory, mock_logger, mock_rag_log, mock_openai_provider):
        """Test Step 49: Comprehensive logging format"""
        from app.orchestrators.facts import step_49__route_strategy

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_openai_provider
        mock_get_factory.return_value = mock_factory

        messages = [Message(role="user", content="Test")]

        ctx = {
            'messages': messages,
            'routing_strategy': RoutingStrategy.BALANCED,
            'max_cost_eur': 1.0
        }

        step_49__route_strategy(ctx=ctx)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label',
            'routing_applied', 'routing_strategy',
            'provider_type', 'model', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]['step'] == 49
        assert log_call[1]['step_id'] == 'RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy'
        assert log_call[1]['node_label'] == 'RouteStrategy'

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.orchestrators.facts.get_llm_factory')
    async def test_step_49_parity_test(self, mock_get_factory, mock_logger, mock_rag_log, mock_openai_provider):
        """Test Step 49: Parity test - ensure behavior matches LLMFactory.get_optimal_provider"""
        from app.orchestrators.facts import step_49__route_strategy

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_openai_provider
        mock_get_factory.return_value = mock_factory

        messages = [
            Message(role="system", content="You are an assistant"),
            Message(role="user", content="Help me with taxes")
        ]

        ctx = {
            'messages': messages,
            'routing_strategy': RoutingStrategy.COST_OPTIMIZED,
            'max_cost_eur': 0.75,
            'preferred_provider': 'openai'
        }

        result = step_49__route_strategy(ctx=ctx)

        # The orchestrator should:
        # 1. Call LLMFactory.get_optimal_provider with exact same params
        # 2. Return the exact same provider
        # 3. Add metadata but not modify core behavior

        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=messages,
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=0.75,
            preferred_provider='openai'
        )

        assert result['provider'] == mock_openai_provider  # Exact same provider returned
        assert result['routing_applied'] is True