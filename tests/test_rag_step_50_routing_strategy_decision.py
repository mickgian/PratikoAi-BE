#!/usr/bin/env python3
"""Tests for RAG STEP 50: Routing strategy? decision."""

from typing import List
from unittest.mock import Mock, patch

import pytest

from app.core.llm.factory import RoutingStrategy
from app.schemas.chat import Message

try:
    from app.ragsteps.platform.step_50_rag_platform_routing_strategy import (
        run,
        determine_routing_strategy_path
    )
except ImportError:
    # Will be created during implementation
    run = None
    determine_routing_strategy_path = None


class TestRAGStep50RoutingStrategyDecision:
    """Test suite for RAG STEP 50: Routing strategy? decision."""

    @pytest.fixture
    def mock_messages(self) -> List[Message]:
        """Mock conversation messages."""
        return [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What is the tax rate in Italy?"),
            Message(role="assistant", content="The standard tax rate in Italy varies."),
            Message(role="user", content="Can you provide more details?")
        ]

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_cost_optimized_routing_decision(
        self,
        mock_log,
        mock_messages
    ):
        """Test STEP 50: COST_OPTIMIZED routing strategy decision."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Execute
        result = determine_routing_strategy_path(
            messages=mock_messages,
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=0.015
        )

        # Verify routing decision
        assert result == "CheapProvider"

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['step'] == 50
        assert log_call['step_id'] == "RAG.platform.routing.strategy"
        assert log_call['node_label'] == "StrategyType"
        assert log_call['decision'] == "routing_to_cost_optimized"
        assert log_call['routing_strategy'] == "cost_optimized"
        assert log_call['next_step'] == "CheapProvider"
        assert log_call['max_cost_eur'] == 0.015
        assert log_call['messages_count'] == 4
        assert log_call['processing_stage'] == "completed"

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_quality_first_routing_decision(
        self,
        mock_log,
        mock_messages
    ):
        """Test STEP 50: QUALITY_FIRST routing strategy decision."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Execute
        result = determine_routing_strategy_path(
            messages=mock_messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=0.030
        )

        # Verify routing decision
        assert result == "BestProvider"

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['decision'] == "routing_to_quality_first"
        assert log_call['routing_strategy'] == "quality_first"
        assert log_call['next_step'] == "BestProvider"
        assert log_call['max_cost_eur'] == 0.030

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_balanced_routing_decision(
        self,
        mock_log,
        mock_messages
    ):
        """Test STEP 50: BALANCED routing strategy decision."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Execute
        result = determine_routing_strategy_path(
            messages=mock_messages,
            strategy=RoutingStrategy.BALANCED,
            max_cost_eur=0.020
        )

        # Verify routing decision
        assert result == "BalanceProvider"

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['decision'] == "routing_to_balanced"
        assert log_call['routing_strategy'] == "balanced"
        assert log_call['next_step'] == "BalanceProvider"

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_failover_routing_decision(
        self,
        mock_log,
        mock_messages
    ):
        """Test STEP 50: FAILOVER routing strategy decision."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Execute
        result = determine_routing_strategy_path(
            messages=mock_messages,
            strategy=RoutingStrategy.FAILOVER,
            max_cost_eur=0.025
        )

        # Verify routing decision
        assert result == "PrimaryProvider"

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['decision'] == "routing_to_failover"
        assert log_call['routing_strategy'] == "failover"
        assert log_call['next_step'] == "PrimaryProvider"

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_unsupported_strategy_fallback(
        self,
        mock_log,
        mock_messages
    ):
        """Test STEP 50: Fallback for unsupported routing strategy."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Create a mock unsupported strategy
        unsupported_strategy = Mock()
        unsupported_strategy.value = "unsupported_strategy"

        # Execute
        result = determine_routing_strategy_path(
            messages=mock_messages,
            strategy=unsupported_strategy,
            max_cost_eur=0.020
        )

        # Verify fallback to balanced
        assert result == "BalanceProvider"

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['decision'] == "routing_fallback_to_balanced"
        assert log_call['routing_strategy'] == "unsupported_strategy"
        assert log_call['next_step'] == "BalanceProvider"
        assert log_call['fallback_reason'] == "unsupported_strategy"

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_edge_cases_and_defaults(
        self,
        mock_log
    ):
        """Test STEP 50: Edge cases and default values."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Test with empty messages and no cost limit
        result = determine_routing_strategy_path(
            messages=[],
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=None
        )

        # Verify
        assert result == "CheapProvider"

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['messages_count'] == 0
        assert log_call['messages_empty'] is True
        assert log_call['max_cost_eur'] is None

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_comprehensive_logging_format(
        self,
        mock_log,
        mock_messages
    ):
        """Test STEP 50: Comprehensive logging format and all attributes."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Execute
        determine_routing_strategy_path(
            messages=mock_messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=0.030,
            preferred_provider="anthropic"
        )

        # Verify comprehensive logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]

        # Required fields
        assert log_call['step'] == 50
        assert log_call['step_id'] == "RAG.platform.routing.strategy"
        assert log_call['node_label'] == "StrategyType"
        assert log_call['decision'] == "routing_to_quality_first"

        # Strategy details
        assert log_call['routing_strategy'] == "quality_first"
        assert log_call['next_step'] == "BestProvider"
        assert log_call['max_cost_eur'] == 0.030
        assert log_call['preferred_provider'] == "anthropic"

        # Message context
        assert log_call['messages_count'] == 4
        assert log_call['messages_empty'] is False

        # Processing status
        assert log_call['processing_stage'] == "completed"

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_run_adapter_function(
        self,
        mock_log
    ):
        """Test STEP 50: Adapter function execution."""
        if not run:
            pytest.skip("Implementation not yet available")

        # Execute adapter
        payload = {
            "messages": [],
            "strategy": "cost_optimized",
            "max_cost_eur": 0.015,
            "trace_id": "test-trace-123"
        }

        result = run(payload)

        # Verify adapter response
        assert result['step'] == 50
        assert result['step_id'] == "RAG.platform.routing.strategy"
        assert result['node'] == "StrategyType"
        assert result['ok'] is True

        # Verify logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['step'] == 50
        assert log_call['decision'] == "routing_strategy_decision_adapter"
        assert log_call['trace_id'] == "test-trace-123"

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_all_strategy_variations(
        self,
        mock_log,
        mock_messages
    ):
        """Test STEP 50: All routing strategy variations and their mappings."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Test mapping for all strategies
        test_cases = [
            (RoutingStrategy.COST_OPTIMIZED, "CheapProvider", "routing_to_cost_optimized"),
            (RoutingStrategy.QUALITY_FIRST, "BestProvider", "routing_to_quality_first"),
            (RoutingStrategy.BALANCED, "BalanceProvider", "routing_to_balanced"),
            (RoutingStrategy.FAILOVER, "PrimaryProvider", "routing_to_failover"),
        ]

        for strategy, expected_next_step, expected_decision in test_cases:
            mock_log.reset_mock()

            # Execute
            result = determine_routing_strategy_path(
                messages=mock_messages,
                strategy=strategy,
                max_cost_eur=0.025
            )

            # Verify
            assert result == expected_next_step

            # Verify strategy-specific logging
            mock_log.assert_called()
            log_call = mock_log.call_args[1]
            assert log_call['decision'] == expected_decision
            assert log_call['routing_strategy'] == strategy.value
            assert log_call['next_step'] == expected_next_step

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_performance_tracking(
        self,
        mock_log,
        mock_messages
    ):
        """Test STEP 50: Performance tracking capabilities."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Execute
        result = determine_routing_strategy_path(
            messages=mock_messages,
            strategy=RoutingStrategy.QUALITY_FIRST,
            max_cost_eur=0.030
        )

        # Verify result
        assert result == "BestProvider"

        # Verify performance-related logging
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert 'processing_stage' in log_call
        assert log_call['processing_stage'] == "completed"

        # Should include timing if rag_step_timer is used
        assert 'step' in log_call
        assert 'step_id' in log_call

    @pytest.mark.asyncio
    @patch('app.ragsteps.platform.step_50_rag_platform_routing_strategy.rag_step_log')
    async def test_step_50_decision_with_additional_context(
        self,
        mock_log,
        mock_messages
    ):
        """Test STEP 50: Decision making with additional context parameters."""
        if not determine_routing_strategy_path:
            pytest.skip("Implementation not yet available")

        # Execute with additional context
        result = determine_routing_strategy_path(
            messages=mock_messages,
            strategy=RoutingStrategy.BALANCED,
            max_cost_eur=0.020,
            preferred_provider="openai",
            complexity="high"
        )

        # Verify
        assert result == "BalanceProvider"

        # Verify context is logged
        mock_log.assert_called()
        log_call = mock_log.call_args[1]
        assert log_call['preferred_provider'] == "openai"
        assert log_call['complexity'] == "high"
        assert log_call['routing_strategy'] == "balanced"
        assert log_call['next_step'] == "BalanceProvider"