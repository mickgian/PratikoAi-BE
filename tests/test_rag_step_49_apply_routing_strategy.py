#!/usr/bin/env python3
"""Tests for RAG STEP 49: LLMFactory.get_optimal_provider Apply routing strategy."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Optional

from app.schemas.chat import Message
from app.core.llm.factory import RoutingStrategy, LLMFactory
from app.core.llm.base import LLMProvider, LLMProviderType

try:
    from app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy import (
        run,
        apply_routing_strategy
    )
except ImportError:
    # Will be created during implementation
    run = None
    apply_routing_strategy = None


class TestRAGStep49ApplyRoutingStrategy:
    """Test suite for RAG STEP 49: Apply routing strategy."""

    @pytest.fixture
    def mock_messages(self) -> List[Message]:
        """Mock conversation messages."""
        return [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What is the tax rate in Italy?"),
            Message(role="assistant", content="The standard tax rate in Italy varies."),
            Message(role="user", content="Can you provide more details?")
        ]

    @pytest.fixture
    def mock_openai_provider(self) -> Mock:
        """Mock OpenAI provider."""
        provider = Mock()
        provider.provider_type = LLMProviderType.OPENAI
        provider.model = "gpt-4"
        return provider

    @pytest.fixture
    def mock_claude_provider(self) -> Mock:
        """Mock Anthropic provider."""
        provider = Mock()
        provider.provider_type = LLMProviderType.ANTHROPIC
        provider.model = "claude-3-sonnet"
        return provider

    @pytest.fixture
    def mock_llm_factory(self) -> Mock:
        """Mock LLM factory."""
        factory = Mock(spec=LLMFactory)
        return factory

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_apply_cost_optimized_routing(
        self,
        mock_log,
        mock_messages,
        mock_openai_provider,
        mock_llm_factory
    ):
        """Test STEP 49: Apply COST_OPTIMIZED routing strategy."""
        if not apply_routing_strategy:
            pytest.skip("Implementation not yet available")

        # Setup
        mock_llm_factory.get_optimal_provider.return_value = mock_openai_provider

        # Execute
        result = apply_routing_strategy(
            messages=mock_messages,
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=0.015,
            llm_factory=mock_llm_factory
        )

        # Verify
        assert result == mock_openai_provider
        mock_llm_factory.get_optimal_provider.assert_called_once_with(
            messages=mock_messages,
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=0.015,
            preferred_provider=None
        )

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['step'] == 49
        assert log_call['step_id'] == "RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy"
        assert log_call['node_label'] == "RouteStrategy"
        assert log_call['routing_strategy'] == "cost_optimized"
        assert log_call['max_cost_eur'] == 0.015
        assert log_call['messages_count'] == 4
        assert log_call['processing_stage'] == "completed"

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_apply_quality_first_routing(
        self,
        mock_log,
        mock_messages,
        mock_claude_provider,
        mock_llm_factory
    ):
        """Test STEP 49: Apply QUALITY_FIRST routing strategy."""
        if not apply_routing_strategy:
            pytest.skip("Implementation not yet available")

        # Setup
        mock_llm_factory.get_optimal_provider.return_value = mock_claude_provider

        # Execute
        result = apply_routing_strategy(
            messages=mock_messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=0.030,
            llm_factory=mock_llm_factory
        )

        # Verify
        assert result == mock_claude_provider
        mock_llm_factory.get_optimal_provider.assert_called_once_with(
            messages=mock_messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=0.030,
            preferred_provider=None
        )

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['routing_strategy'] == "quality_first"
        assert log_call['provider_type'] == "anthropic"
        assert log_call['model'] == "claude-3-sonnet"

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_apply_balanced_routing(
        self,
        mock_log,
        mock_messages,
        mock_openai_provider,
        mock_llm_factory
    ):
        """Test STEP 49: Apply BALANCED routing strategy."""
        if not apply_routing_strategy:
            pytest.skip("Implementation not yet available")

        # Setup
        mock_llm_factory.get_optimal_provider.return_value = mock_openai_provider

        # Execute
        result = apply_routing_strategy(
            messages=mock_messages,
            strategy=RoutingStrategy.BALANCED,
            max_cost_eur=0.020,
            llm_factory=mock_llm_factory
        )

        # Verify
        assert result == mock_openai_provider
        mock_llm_factory.get_optimal_provider.assert_called_once_with(
            messages=mock_messages,
            strategy=RoutingStrategy.BALANCED,
            max_cost_eur=0.020,
            preferred_provider=None
        )

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['routing_strategy'] == "balanced"

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_apply_routing_with_preferred_provider(
        self,
        mock_log,
        mock_messages,
        mock_claude_provider,
        mock_llm_factory
    ):
        """Test STEP 49: Apply routing strategy with preferred provider."""
        if not apply_routing_strategy:
            pytest.skip("Implementation not yet available")

        # Setup
        mock_llm_factory.get_optimal_provider.return_value = mock_claude_provider

        # Execute
        result = apply_routing_strategy(
            messages=mock_messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=0.025,
            preferred_provider="anthropic",
            llm_factory=mock_llm_factory
        )

        # Verify
        assert result == mock_claude_provider
        mock_llm_factory.get_optimal_provider.assert_called_once_with(
            messages=mock_messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=0.025,
            preferred_provider="anthropic"
        )

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['preferred_provider'] == "anthropic"
        assert log_call['provider_type'] == "anthropic"

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_apply_routing_factory_error_fallback(
        self,
        mock_log,
        mock_messages,
        mock_llm_factory
    ):
        """Test STEP 49: Error handling and fallback when factory fails."""
        if not apply_routing_strategy:
            pytest.skip("Implementation not yet available")

        # Setup factory to raise error
        mock_llm_factory.get_optimal_provider.side_effect = ValueError("No suitable provider found")

        # Execute and verify exception is raised
        with pytest.raises(ValueError, match="No suitable provider found"):
            apply_routing_strategy(
                messages=mock_messages,
                strategy=RoutingStrategy.COST_OPTIMIZED,
                max_cost_eur=0.015,
                llm_factory=mock_llm_factory
            )

        # Verify error logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['step'] == 49
        assert log_call['processing_stage'] == "error"
        assert "No suitable provider found" in log_call['error']

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_edge_cases_and_defaults(
        self,
        mock_log,
        mock_openai_provider,
        mock_llm_factory
    ):
        """Test STEP 49: Edge cases and default values."""
        if not apply_routing_strategy:
            pytest.skip("Implementation not yet available")

        # Setup
        mock_llm_factory.get_optimal_provider.return_value = mock_openai_provider

        # Test with empty messages and no cost limit
        result = apply_routing_strategy(
            messages=[],
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=None,
            llm_factory=mock_llm_factory
        )

        # Verify
        assert result == mock_openai_provider
        mock_llm_factory.get_optimal_provider.assert_called_once_with(
            messages=[],
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=None,
            preferred_provider=None
        )

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['messages_count'] == 0
        assert log_call['messages_empty'] is True
        assert log_call['max_cost_eur'] is None

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_comprehensive_logging_format(
        self,
        mock_log,
        mock_messages,
        mock_openai_provider,
        mock_llm_factory
    ):
        """Test STEP 49: Comprehensive logging format and all attributes."""
        if not apply_routing_strategy:
            pytest.skip("Implementation not yet available")

        # Setup
        mock_llm_factory.get_optimal_provider.return_value = mock_openai_provider

        # Execute
        apply_routing_strategy(
            messages=mock_messages,
            strategy=RoutingStrategy.BALANCED,
            max_cost_eur=0.020,
            preferred_provider="openai",
            llm_factory=mock_llm_factory
        )

        # Verify comprehensive logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]

        # Required fields
        assert log_call['step'] == 49
        assert log_call['step_id'] == "RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy"
        assert log_call['node_label'] == "RouteStrategy"
        assert log_call['decision'] == "routing_strategy_applied"

        # Strategy details
        assert log_call['routing_strategy'] == "balanced"
        assert log_call['max_cost_eur'] == 0.020
        assert log_call['preferred_provider'] == "openai"

        # Provider details
        assert log_call['provider_type'] == "openai"
        assert log_call['model'] == "gpt-4"

        # Message context
        assert log_call['messages_count'] == 4
        assert log_call['messages_empty'] is False

        # Processing status
        assert log_call['processing_stage'] == "completed"

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_run_adapter_function(
        self,
        mock_log
    ):
        """Test STEP 49: Adapter function execution."""
        if not run:
            pytest.skip("Implementation not yet available")

        # Execute adapter
        payload = {
            "messages": [],
            "strategy": "COST_OPTIMIZED",
            "max_cost_eur": 0.015,
            "trace_id": "test-trace-123"
        }

        result = run(payload)

        # Verify adapter response
        assert result['step'] == 49
        assert result['step_id'] == "RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy"
        assert result['node'] == "RouteStrategy"
        assert result['ok'] is True

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['step'] == 49
        assert log_call['decision'] == "routing_strategy_adapter"
        assert log_call['trace_id'] == "test-trace-123"

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_routing_strategy_variations(
        self,
        mock_log,
        mock_messages,
        mock_openai_provider,
        mock_llm_factory
    ):
        """Test STEP 49: All routing strategy variations."""
        if not apply_routing_strategy:
            pytest.skip("Implementation not yet available")

        # Setup
        mock_llm_factory.get_optimal_provider.return_value = mock_openai_provider

        strategies = [
            (RoutingStrategy.COST_OPTIMIZED, 0.010),
            (RoutingStrategy.QUALITY_FIRST, 0.040),
            (RoutingStrategy.BALANCED, 0.025),
            (RoutingStrategy.FAILOVER, 0.030),
        ]

        for strategy, max_cost in strategies:
            mock_log.reset_mock()
            mock_llm_factory.reset_mock()
            mock_llm_factory.get_optimal_provider.return_value = mock_openai_provider

            # Execute
            result = apply_routing_strategy(
                messages=mock_messages,
                strategy=strategy,
                max_cost_eur=max_cost,
                llm_factory=mock_llm_factory
            )

            # Verify
            assert result == mock_openai_provider
            mock_llm_factory.get_optimal_provider.assert_called_once_with(
                messages=mock_messages,
                strategy=strategy,
                max_cost_eur=max_cost,
                preferred_provider=None
            )

            # Verify strategy-specific logging
            mock_log.assert_called()
            log_call = mock_log.call_args[1]
            assert log_call['routing_strategy'] == strategy.value
            assert log_call['max_cost_eur'] == max_cost

    @pytest.mark.asyncio
    @patch('app.ragsteps.facts.step_49_rag_facts_llmfactory_get_optimal_provider_apply_routing_strategy.rag_step_log')
    async def test_step_49_performance_tracking(
        self,
        mock_log,
        mock_messages,
        mock_openai_provider,
        mock_llm_factory
    ):
        """Test STEP 49: Performance tracking capabilities."""
        if not apply_routing_strategy:
            pytest.skip("Implementation not yet available")

        # Setup
        mock_llm_factory.get_optimal_provider.return_value = mock_openai_provider

        # Execute
        result = apply_routing_strategy(
            messages=mock_messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=0.030,
            llm_factory=mock_llm_factory
        )

        # Verify result
        assert result == mock_openai_provider

        # Verify performance-related logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert 'processing_stage' in log_call
        assert log_call['processing_stage'] == "completed"

        # Should include timing if rag_step_timer is used
        assert 'step' in log_call
        assert 'step_id' in log_call