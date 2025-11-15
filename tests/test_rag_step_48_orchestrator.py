#!/usr/bin/env python3
"""
Tests for RAG STEP 48 Orchestrator — Select LLM provider

This test file specifically tests the orchestrator function step_48__select_provider
to ensure it properly handles the provider selection initiation.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.llm.factory import RoutingStrategy
from app.schemas.chat import Message


class TestRAGStep48Orchestrator:
    """Test suite for RAG STEP 48 orchestrator function"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.providers.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_48_orchestrator_success(self, mock_logger, mock_rag_log):
        """Test Step 48 orchestrator: Successful provider selection initiation"""
        from app.orchestrators.providers import step_48__select_provider

        messages = [Message(role="user", content="Calculate my tax deductions")]

        ctx = {
            "messages": messages,
            "routing_strategy": RoutingStrategy.COST_OPTIMIZED,
            "max_cost_eur": 0.5,
            "preferred_provider": "openai",
            "user_id": "user_123",
            "session_id": "session_456",
        }

        # Call the orchestrator function
        result = step_48__select_provider(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["provider_selection_initiated"] is True
        assert result["ready_for_routing"] is True
        assert result["messages"] == messages
        assert result["routing_strategy"] == RoutingStrategy.COST_OPTIMIZED
        assert result["max_cost_eur"] == 0.5
        assert result["preferred_provider"] == "openai"
        assert result["user_id"] == "user_123"
        assert result["session_id"] == "session_456"
        assert "timestamp" in result

        # Verify logging was called
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args
        assert "Initiating provider selection" in log_call[0][0]

        # Verify rag_step_log was called with correct parameters
        start_logs = [call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "started"]
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(start_logs) > 0
        assert len(completed_logs) > 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.providers.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_48_orchestrator_missing_messages(self, mock_logger, mock_rag_log):
        """Test Step 48 orchestrator: Handle missing messages"""
        from app.orchestrators.providers import step_48__select_provider

        ctx = {
            "routing_strategy": RoutingStrategy.QUALITY_FIRST
            # Missing messages
        }

        result = step_48__select_provider(ctx=ctx)

        assert result["provider_selection_initiated"] is False
        assert result["error"] == "Missing required parameter: messages"
        assert "timestamp" in result

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Missing required parameter: messages" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.providers.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_48_orchestrator_default_strategy(self, mock_logger, mock_rag_log):
        """Test Step 48 orchestrator: Use default strategy when not specified"""
        from app.orchestrators.providers import step_48__select_provider

        messages = [Message(role="user", content="What is VAT?")]

        ctx = {
            "messages": messages
            # No strategy specified - should use default
        }

        result = step_48__select_provider(ctx=ctx)

        assert result["provider_selection_initiated"] is True
        assert result["routing_strategy"] == RoutingStrategy.COST_OPTIMIZED  # Default
        assert result["max_cost_eur"] is None
        assert result["preferred_provider"] is None

    @pytest.mark.asyncio
    @patch("app.orchestrators.providers.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_48_orchestrator_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 48 orchestrator: Parameters passed via kwargs"""
        from app.orchestrators.providers import step_48__select_provider

        messages = [Message(role="user", content="Test query")]

        # Call with kwargs instead of ctx
        result = step_48__select_provider(
            messages=messages, routing_strategy=RoutingStrategy.BALANCED, max_cost_eur=0.3, user_id="user_789"
        )

        assert result["provider_selection_initiated"] is True
        assert result["messages"] == messages
        assert result["routing_strategy"] == RoutingStrategy.BALANCED
        assert result["max_cost_eur"] == 0.3
        assert result["user_id"] == "user_789"

    @pytest.mark.asyncio
    @patch("app.orchestrators.providers.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_48_orchestrator_ready_for_step_49(self, mock_logger, mock_rag_log):
        """Test Step 48 orchestrator: Output is ready for Step 49 (RouteStrategy)"""
        from app.orchestrators.providers import step_48__select_provider

        messages = [
            Message(role="system", content="You are a tax expert"),
            Message(role="user", content="Complex tax calculation"),
        ]

        ctx = {
            "messages": messages,
            "routing_strategy": RoutingStrategy.QUALITY_FIRST,
            "max_cost_eur": 2.0,
            "preferred_provider": "anthropic",
        }

        result = step_48__select_provider(ctx=ctx)

        # Verify output is properly formatted for Step 49
        assert result["ready_for_routing"] is True
        assert "messages" in result
        assert "routing_strategy" in result
        assert "max_cost_eur" in result
        assert "preferred_provider" in result

        # Verify messages are preserved correctly
        assert isinstance(result["messages"], list)
        assert len(result["messages"]) == 2
        assert all(isinstance(msg, Message) for msg in result["messages"])

    @pytest.mark.asyncio
    @patch("app.orchestrators.providers.rag_step_timer")
    @patch("app.orchestrators.providers.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_48_orchestrator_performance_tracking(self, mock_logger, mock_rag_log, mock_timer):
        """Test Step 48 orchestrator: Performance tracking with timer"""
        from app.orchestrators.providers import step_48__select_provider

        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        messages = [Message(role="user", content="Test")]

        step_48__select_provider(ctx={"messages": messages})

        # Verify timer was used
        mock_timer.assert_called_with(
            48,
            "RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider",
            "SelectProvider",
            stage="start",
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.providers.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_48_orchestrator_parity(self, mock_logger, mock_rag_log):
        """Test Step 48 orchestrator: Parity test - ensures behavior matches requirements"""
        from app.orchestrators.providers import step_48__select_provider

        # This test ensures the orchestrator maintains expected behavior
        messages = [Message(role="user", content="Calculate my pension")]

        ctx = {
            "messages": messages,
            "routing_strategy": RoutingStrategy.BALANCED,
            "max_cost_eur": 0.75,
            "preferred_provider": "openai",
            "fallback_provider": "anthropic",
        }

        result = step_48__select_provider(ctx=ctx)

        # The orchestrator should:
        # 1. Accept incoming data from Steps 46/47
        # 2. Prepare context for Step 49
        # 3. Not modify the core data

        assert result["provider_selection_initiated"] is True
        assert result["ready_for_routing"] is True

        # Verify all necessary data is preserved for Step 49
        assert result["messages"] == messages
        assert result["routing_strategy"] == RoutingStrategy.BALANCED
        assert result["max_cost_eur"] == 0.75
        assert result["preferred_provider"] == "openai"
        assert result["fallback_provider"] == "anthropic"

        # Verify the result structure is compatible with Step 49's expected input
        assert isinstance(result, dict)
        assert all(key in result for key in ["messages", "routing_strategy", "max_cost_eur", "preferred_provider"])
