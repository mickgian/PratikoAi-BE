#!/usr/bin/env python3
"""
Quick tests for RAG STEPS 52-54 provider orchestrators to verify basic functionality
"""

from unittest.mock import MagicMock, patch
import pytest

from app.schemas.chat import Message
from app.core.llm.factory import RoutingStrategy
from app.core.llm.base import LLMProviderType


class TestRAGProviderSteps:
    """Quick test suite for provider steps 52-53-54"""

    @pytest.fixture
    def mock_messages(self):
        return [Message(role="user", content="Test query")]

    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.provider_type = LLMProviderType.OPENAI
        provider.model = "gpt-4"
        provider.cost_per_token = 0.001
        return provider

    @pytest.mark.asyncio
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_52_best_provider_success(self, mock_get_factory, mock_messages, mock_provider):
        """Test Step 52: Best provider selection"""
        from app.orchestrators.providers import step_52__best_provider

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_provider
        mock_get_factory.return_value = mock_factory

        ctx = {'messages': mock_messages, 'max_cost_eur': 2.0}
        result = step_52__best_provider(ctx=ctx)

        assert result['provider_selected'] is True
        assert result['provider'] == mock_provider
        assert result['ready_for_cost_estimation'] is True
        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=mock_messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=2.0,
            preferred_provider=None
        )

    @pytest.mark.asyncio
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_53_balance_provider_success(self, mock_get_factory, mock_messages, mock_provider):
        """Test Step 53: Balanced provider selection"""
        from app.orchestrators.providers import step_53__balance_provider

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_provider
        mock_get_factory.return_value = mock_factory

        ctx = {'messages': mock_messages, 'max_cost_eur': 1.0}
        result = step_53__balance_provider(ctx=ctx)

        assert result['provider_selected'] is True
        assert result['provider'] == mock_provider
        assert result['ready_for_cost_estimation'] is True
        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=mock_messages,
            strategy=RoutingStrategy.BALANCED,
            max_cost_eur=1.0,
            preferred_provider=None
        )

    @pytest.mark.asyncio
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_54_primary_provider_success(self, mock_get_factory, mock_messages, mock_provider):
        """Test Step 54: Primary provider selection"""
        from app.orchestrators.providers import step_54__primary_provider

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_provider
        mock_get_factory.return_value = mock_factory

        ctx = {'messages': mock_messages, 'preferred_provider': 'openai'}
        result = step_54__primary_provider(ctx=ctx)

        assert result['provider_selected'] is True
        assert result['provider'] == mock_provider
        assert result['ready_for_cost_estimation'] is True
        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=mock_messages,
            strategy=RoutingStrategy.FAILOVER,
            max_cost_eur=None,
            preferred_provider='openai'
        )

    @pytest.mark.asyncio
    async def test_step_52_missing_messages(self):
        """Test Step 52: Handle missing messages"""
        from app.orchestrators.providers import step_52__best_provider

        result = step_52__best_provider(ctx={})
        assert result['provider_selected'] is False
        assert result['error'] == 'Missing required parameter: messages'

    @pytest.mark.asyncio
    async def test_step_53_missing_messages(self):
        """Test Step 53: Handle missing messages"""
        from app.orchestrators.providers import step_53__balance_provider

        result = step_53__balance_provider(ctx={})
        assert result['provider_selected'] is False
        assert result['error'] == 'Missing required parameter: messages'

    @pytest.mark.asyncio
    async def test_step_54_missing_messages(self):
        """Test Step 54: Handle missing messages"""
        from app.orchestrators.providers import step_54__primary_provider

        result = step_54__primary_provider(ctx={})
        assert result['provider_selected'] is False
        assert result['error'] == 'Missing required parameter: messages'