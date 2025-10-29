#!/usr/bin/env python3
"""
Quick tests for RAG STEPS 55-58 to verify basic functionality
"""

from unittest.mock import MagicMock, patch
import pytest

from app.schemas.chat import Message


class TestRAGSteps55To58:
    """Quick test suite for steps 55-56-57-58"""

    @pytest.fixture
    def mock_messages(self):
        return [Message(role="user", content="Calculate my taxes")]

    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.provider_type = MagicMock()
        provider.provider_type.value = "openai"
        provider.model = "gpt-3.5-turbo"
        provider.cost_per_token = 0.0005
        return provider

    @pytest.mark.asyncio
    async def test_step_55_estimate_cost_success(self, mock_messages, mock_provider):
        """Test Step 55: Cost estimation"""
        from app.orchestrators.providers import step_55__estimate_cost

        ctx = {
            'messages': mock_messages,
            'provider': mock_provider,
            'provider_type': 'openai',
            'model': 'gpt-3.5-turbo',
            'cost_per_token': 0.0005,
            'max_cost_eur': 1.0
        }

        result = step_55__estimate_cost(ctx=ctx)

        assert result['cost_estimated'] is True
        assert result['ready_for_cost_check'] is True
        assert result['estimated_cost'] > 0
        assert result['estimated_tokens'] > 0
        assert result['provider'] == mock_provider

    @pytest.mark.asyncio
    async def test_step_56_cost_within_budget(self):
        """Test Step 56: Cost check within budget"""
        from app.orchestrators.providers import step_56__cost_check

        ctx = {
            'estimated_cost': 0.5,
            'max_cost_eur': 1.0,
            'provider_type': 'openai',
            'model': 'gpt-3.5-turbo'
        }

        result = step_56__cost_check(ctx=ctx)

        assert result['within_budget'] is True
        assert result['decision'] == 'cost_within_budget'
        assert result['next_step'] == 'CreateProvider'

    @pytest.mark.asyncio
    async def test_step_56_cost_over_budget(self):
        """Test Step 56: Cost check over budget"""
        from app.orchestrators.providers import step_56__cost_check

        ctx = {
            'estimated_cost': 1.5,
            'max_cost_eur': 1.0,
            'provider_type': 'openai',
            'model': 'gpt-4'
        }

        result = step_56__cost_check(ctx=ctx)

        assert result['within_budget'] is False
        assert result['decision'] == 'cost_over_budget'
        assert result['next_step'] == 'CheaperProvider'
        assert result['cost_difference'] == 0.5

    @pytest.mark.asyncio
    async def test_step_57_create_provider_success(self, mock_provider):
        """Test Step 57: Create provider instance"""
        from app.orchestrators.providers import step_57__create_provider

        ctx = {
            'provider': mock_provider,
            'provider_type': 'openai',
            'model': 'gpt-3.5-turbo',
            'estimated_cost': 0.5,
            'estimated_tokens': 100
        }

        result = step_57__create_provider(ctx=ctx)

        assert result['provider_created'] is True
        assert result['ready_for_processing'] is True
        assert result['provider_instance'] == mock_provider

    @pytest.mark.asyncio
    @patch('app.core.llm.factory.get_llm_factory')
    async def test_step_58_cheaper_provider_found(self, mock_get_factory, mock_messages):
        """Test Step 58: Find cheaper provider"""
        from app.orchestrators.providers import step_58__cheaper_provider

        cheaper_provider = MagicMock()
        cheaper_provider.provider_type.value = "openai"
        cheaper_provider.model = "gpt-3.5-turbo"
        cheaper_provider.cost_per_token = 0.0001

        mock_factory = MagicMock()
        mock_factory.get_optimal_provider.return_value = cheaper_provider
        mock_get_factory.return_value = mock_factory

        ctx = {
            'messages': mock_messages,
            'max_cost_eur': 1.0,
            'estimated_cost': 1.2,
            'provider_type': 'openai',
            'model': 'gpt-4'
        }

        result = step_58__cheaper_provider(ctx=ctx)

        assert result['cheaper_provider_found'] is True
        assert result['provider'] == cheaper_provider
        assert result['needs_cost_recheck'] is True
        assert result['reduced_budget'] == 0.8  # 80% of 1.0

    @pytest.mark.asyncio
    async def test_step_55_missing_parameters(self):
        """Test Step 55: Handle missing parameters"""
        from app.orchestrators.providers import step_55__estimate_cost

        result = step_55__estimate_cost(ctx={})
        assert result['cost_estimated'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_step_57_missing_provider(self):
        """Test Step 57: Handle missing provider"""
        from app.orchestrators.providers import step_57__create_provider

        result = step_57__create_provider(ctx={})
        assert result['provider_created'] is False
        assert result['error'] == 'Missing required parameter: provider'

    @pytest.mark.asyncio
    async def test_step_58_missing_messages(self):
        """Test Step 58: Handle missing messages"""
        from app.orchestrators.providers import step_58__cheaper_provider

        result = step_58__cheaper_provider(ctx={})
        assert result['cheaper_provider_found'] is False
        assert result['error'] == 'Missing required parameter: messages'