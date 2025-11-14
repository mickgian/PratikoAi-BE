#!/usr/bin/env python3
"""
Tests for RAG STEP 51 — Select cheapest provider

This step selects the cheapest LLM provider from available options.
Receives context from Step 50 (StrategyType) and prepares for Step 55 (EstimateCost).
"""

from unittest.mock import MagicMock, patch
import pytest

from app.schemas.chat import Message
from app.core.llm.factory import RoutingStrategy
from app.core.llm.base import LLMProviderType


class TestRAGStep51CheapProvider:
    """Test suite for RAG STEP 51 - Select cheapest provider"""

    @pytest.fixture
    def mock_messages(self):
        """Mock conversation messages."""
        return [
            Message(role="user", content="Calculate my tax deductions")
        ]

    @pytest.fixture
    def mock_cheap_provider(self):
        """Mock cheap provider."""
        provider = MagicMock()
        provider.provider_type = LLMProviderType.OPENAI
        provider.model = "gpt-3.5-turbo"
        provider.cost_per_token = 0.0005
        return provider

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_51_select_cheapest_provider_success(self, mock_get_factory, mock_logger, mock_rag_log, mock_messages, mock_cheap_provider):
        """Test Step 51: Successfully select cheapest provider"""
        from app.orchestrators.providers import step_51__cheap_provider

        # Mock factory
        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_cheap_provider
        mock_get_factory.return_value = mock_factory

        # Context from Step 50
        ctx = {
            'decision': 'routing_to_cost_optimized',
            'next_step': 'CheapProvider',
            'routing_strategy': 'cost_optimized',
            'messages': mock_messages,
            'max_cost_eur': 0.5,
            'preferred_provider': 'openai',
            'user_id': 'user_123'
        }

        # Call the orchestrator function
        result = step_51__cheap_provider(ctx=ctx)

        # Verify factory was called correctly
        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=mock_messages,
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=0.5,
            preferred_provider='openai'
        )

        # Verify result structure
        assert isinstance(result, dict)
        assert result['provider_selected'] is True
        assert result['provider'] == mock_cheap_provider
        assert result['provider_type'] == LLMProviderType.OPENAI.value
        assert result['model'] == 'gpt-3.5-turbo'
        assert result['cost_per_token'] == 0.0005
        assert result['messages'] == mock_messages

        # Verify logging
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_51_no_cheap_provider_available(self, mock_get_factory, mock_logger, mock_rag_log, mock_messages):
        """Test Step 51: No cheap provider available within budget"""
        from app.orchestrators.providers import step_51__cheap_provider

        # Mock factory returning None (no provider within budget)
        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = None
        mock_get_factory.return_value = mock_factory

        ctx = {
            'messages': mock_messages,
            'max_cost_eur': 0.01,  # Very low budget
            'routing_strategy': 'cost_optimized'
        }

        result = step_51__cheap_provider(ctx=ctx)

        # Should handle gracefully
        assert result['provider_selected'] is False
        assert result['provider'] is None
        assert result['reason'] == 'no_provider_within_budget'

        # Verify warning logging
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_51_factory_error(self, mock_get_factory, mock_logger, mock_rag_log, mock_messages):
        """Test Step 51: Handle factory error gracefully"""
        from app.orchestrators.providers import step_51__cheap_provider

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.side_effect = ValueError("No providers configured")
        mock_get_factory.return_value = mock_factory

        ctx = {
            'messages': mock_messages,
            'max_cost_eur': 0.5
        }

        result = step_51__cheap_provider(ctx=ctx)

        # Should handle error gracefully
        assert result['provider_selected'] is False
        assert result['error'] == "No providers configured"
        assert result['provider'] is None

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_51_missing_messages(self, mock_logger, mock_rag_log):
        """Test Step 51: Handle missing messages"""
        from app.orchestrators.providers import step_51__cheap_provider

        ctx = {
            'max_cost_eur': 0.5
            # Missing messages
        }

        result = step_51__cheap_provider(ctx=ctx)

        assert result['provider_selected'] is False
        assert result['error'] == 'Missing required parameter: messages'

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_51_with_preferences(self, mock_get_factory, mock_logger, mock_rag_log, mock_messages, mock_cheap_provider):
        """Test Step 51: Provider selection with preferences"""
        from app.orchestrators.providers import step_51__cheap_provider

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_cheap_provider
        mock_get_factory.return_value = mock_factory

        ctx = {
            'messages': mock_messages,
            'max_cost_eur': 1.0,
            'preferred_provider': 'anthropic',
            'fallback_provider': 'openai'
        }

        result = step_51__cheap_provider(ctx=ctx)

        # Verify preferences were passed to factory
        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=mock_messages,
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=1.0,
            preferred_provider='anthropic'
        )

        assert result['provider_selected'] is True
        assert result['preferred_provider'] == 'anthropic'
        assert result['fallback_provider'] == 'openai'

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_51_ready_for_step_55(self, mock_get_factory, mock_logger, mock_rag_log, mock_messages, mock_cheap_provider):
        """Test Step 51: Output ready for Step 55 (EstimateCost)"""
        from app.orchestrators.providers import step_51__cheap_provider

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_cheap_provider
        mock_get_factory.return_value = mock_factory

        ctx = {
            'messages': mock_messages,
            'max_cost_eur': 0.5,
            'routing_strategy': 'cost_optimized'
        }

        result = step_51__cheap_provider(ctx=ctx)

        # Verify output is ready for Step 55
        assert result['ready_for_cost_estimation'] is True
        assert 'provider' in result
        assert 'messages' in result
        assert 'max_cost_eur' in result

        # These fields needed for Step 55 cost estimation
        assert result['provider'] is not None
        assert result['messages'] == mock_messages
        assert result['max_cost_eur'] == 0.5

    @pytest.mark.asyncio
    @patch('app.orchestrators.providers.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_51_comprehensive_logging(self, mock_get_factory, mock_logger, mock_rag_log, mock_messages, mock_cheap_provider):
        """Test Step 51: Comprehensive logging format"""
        from app.orchestrators.providers import step_51__cheap_provider

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_cheap_provider
        mock_get_factory.return_value = mock_factory

        ctx = {
            'messages': mock_messages,
            'max_cost_eur': 0.5,
            'preferred_provider': 'openai'
        }

        step_51__cheap_provider(ctx=ctx)

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
            'provider_selected', 'provider_type', 'model',
            'cost_per_token', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]['step'] == 51
        assert log_call[1]['step_id'] == 'RAG.providers.select.cheapest.provider'
        assert log_call[1]['node_label'] == 'CheapProvider'