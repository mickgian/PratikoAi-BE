"""
Tests for RAG STEP 48 — LangGraphAgent._get_optimal_provider Select LLM provider

This step selects the optimal LLM provider based on classification, routing strategy,
cost constraints, and provider preferences. It's a key decision point that follows
system message handling (Steps 46/47) and precedes provider routing (Step 49).
"""

import pytest
from unittest.mock import MagicMock, patch, call

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message
from app.services.domain_action_classifier import DomainActionClassification, Domain, Action
from app.core.llm.factory import RoutingStrategy
from app.core.llm.base import LLMProviderType
from app.core.llm.providers.openai_provider import OpenAIProvider
from app.core.llm.providers.anthropic_provider import AnthropicProvider


class TestRAGStep48SelectProvider:
    """Test suite for RAG STEP 48 - Select LLM provider"""

    @pytest.fixture
    def lang_graph_agent(self):
        """Create LangGraphAgent instance for testing."""
        agent = LangGraphAgent()
        return agent

    @pytest.fixture
    def messages_with_system(self):
        """Messages list with system message."""
        return [
            Message(role="system", content="You are a tax advisor assistant."),
            Message(role="user", content="What is tax deduction?"),
            Message(role="assistant", content="A tax deduction reduces taxable income.")
        ]

    @pytest.fixture
    def tax_classification_high_quality(self):
        """High confidence tax classification requiring quality-first routing."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.95,
            reasoning="High confidence tax calculation request"
        )

    @pytest.fixture
    def labor_classification_balanced(self):
        """Labor classification requiring balanced routing."""
        return DomainActionClassification(
            domain=Domain.LABOR,
            action=Action.CCNL_QUERY,
            confidence=0.85,
            reasoning="CCNL labor agreement query"
        )

    @pytest.fixture
    def general_classification_cost_optimized(self):
        """General classification suitable for cost-optimized routing."""
        return DomainActionClassification(
            domain=Domain.BUSINESS,
            action=Action.INFORMATION_REQUEST,
            confidence=0.70,
            reasoning="General business information request"
        )

    @pytest.fixture
    def mock_openai_provider(self):
        """Mock OpenAI provider."""
        provider = MagicMock(spec=OpenAIProvider)
        provider.provider_type = LLMProviderType.OPENAI
        provider.model = "gpt-4"
        return provider

    @pytest.fixture
    def mock_anthropic_provider(self):
        """Mock Anthropic provider."""
        provider = MagicMock(spec=AnthropicProvider)
        provider.provider_type = LLMProviderType.ANTHROPIC
        provider.model = "claude-3-sonnet"
        return provider

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_48_select_provider_with_tax_classification(
        self,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        messages_with_system,
        tax_classification_high_quality,
        mock_openai_provider
    ):
        """Test STEP 48: Provider selection with tax classification requiring quality-first."""

        # Set up classification
        lang_graph_agent._current_classification = tax_classification_high_quality
        mock_get_llm_provider.return_value = mock_openai_provider

        # Call the method
        result = lang_graph_agent._get_optimal_provider(messages_with_system)

        # Verify provider selection was called with correct parameters
        mock_get_llm_provider.assert_called_once()
        call_args = mock_get_llm_provider.call_args[1]
        assert call_args['messages'] == messages_with_system
        assert call_args['strategy'] == RoutingStrategy.QUALITY_FIRST
        assert call_args['max_cost_eur'] == 0.020  # Tax calculation cost limit

        # Verify result
        assert result == mock_openai_provider

        # Verify STEP 48 logging was called
        step_48_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 48
        ]

        assert len(step_48_logs) > 0, "STEP 48 should be logged"
        log_call = step_48_logs[0]
        assert log_call[1]['step'] == 48
        assert log_call[1]['step_id'] == "RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider"
        assert log_call[1]['node_label'] == "SelectProvider"
        assert log_call[1]['provider_type'] == LLMProviderType.OPENAI.value
        assert log_call[1]['model'] == "gpt-4"
        assert log_call[1]['routing_strategy'] == RoutingStrategy.QUALITY_FIRST.value
        assert log_call[1]['max_cost_eur'] == 0.020
        assert log_call[1]['classification_used'] is True
        assert log_call[1]['domain'] == Domain.TAX.value
        assert log_call[1]['action'] == Action.CALCULATION_REQUEST.value

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_48_select_provider_with_labor_classification(
        self,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        messages_with_system,
        labor_classification_balanced,
        mock_anthropic_provider
    ):
        """Test STEP 48: Provider selection with labor classification requiring balanced routing."""

        # Set up classification
        lang_graph_agent._current_classification = labor_classification_balanced
        mock_get_llm_provider.return_value = mock_anthropic_provider

        # Call the method
        result = lang_graph_agent._get_optimal_provider(messages_with_system)

        # Verify provider selection
        mock_get_llm_provider.assert_called_once()
        call_args = mock_get_llm_provider.call_args[1]
        assert call_args['strategy'] == RoutingStrategy.BALANCED
        assert call_args['max_cost_eur'] == 0.018  # CCNL query cost limit

        # Verify result
        assert result == mock_anthropic_provider

        # Verify STEP 48 logging
        step_48_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 48
        ]

        assert len(step_48_logs) > 0
        log_call = step_48_logs[0]
        assert log_call[1]['provider_type'] == LLMProviderType.ANTHROPIC.value
        assert log_call[1]['model'] == "claude-3-sonnet"
        assert log_call[1]['routing_strategy'] == RoutingStrategy.BALANCED.value
        assert log_call[1]['max_cost_eur'] == 0.018
        assert log_call[1]['domain'] == Domain.LABOR.value
        assert log_call[1]['action'] == Action.CCNL_QUERY.value

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_48_select_provider_without_classification(
        self,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        messages_with_system,
        mock_openai_provider
    ):
        """Test STEP 48: Provider selection without classification using default routing."""

        # No classification
        lang_graph_agent._current_classification = None
        mock_get_llm_provider.return_value = mock_openai_provider

        # Call the method
        result = lang_graph_agent._get_optimal_provider(messages_with_system)

        # Verify default routing strategy was used
        mock_get_llm_provider.assert_called_once()
        call_args = mock_get_llm_provider.call_args[1]
        assert call_args['strategy'] == RoutingStrategy.COST_OPTIMIZED  # Default
        assert call_args['max_cost_eur'] == 0.020  # Default from settings

        # Verify STEP 48 logging shows no classification
        step_48_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 48
        ]

        assert len(step_48_logs) > 0
        log_call = step_48_logs[0]
        assert log_call[1]['classification_used'] is False
        assert log_call[1]['domain'] is None
        assert log_call[1]['action'] is None
        assert log_call[1]['routing_strategy'] == RoutingStrategy.COST_OPTIMIZED.value

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_48_select_provider_with_preferred_provider(
        self,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        messages_with_system,
        mock_anthropic_provider
    ):
        """Test STEP 48: Provider selection respects preferred provider setting."""

        # Mock settings with preferred provider
        with patch('app.core.langgraph.graph.settings') as mock_settings:
            mock_settings.LLM_PREFERRED_PROVIDER = "anthropic"
            mock_settings.LLM_MAX_COST_EUR = 0.025
            mock_settings.LLM_ROUTING_STRATEGY = "quality_first"

            lang_graph_agent._current_classification = None
            mock_get_llm_provider.return_value = mock_anthropic_provider

            # Call the method
            result = lang_graph_agent._get_optimal_provider(messages_with_system)

            # Verify preferred provider was passed
            mock_get_llm_provider.assert_called_once()
            call_args = mock_get_llm_provider.call_args[1]
            assert call_args['preferred_provider'] == "anthropic"

        # Verify STEP 48 logging includes preferred provider info
        step_48_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 48
        ]

        assert len(step_48_logs) > 0
        log_call = step_48_logs[0]
        assert log_call[1]['preferred_provider'] == "anthropic"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.langgraph.graph.logger')
    async def test_step_48_select_provider_fallback_on_error(
        self,
        mock_logger,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        messages_with_system
    ):
        """Test STEP 48: Fallback to legacy OpenAI when provider selection fails."""

        # Mock provider selection failure
        mock_get_llm_provider.side_effect = Exception("Provider selection failed")
        lang_graph_agent._current_classification = None

        # Mock settings for fallback
        with patch('app.core.langgraph.graph.settings') as mock_settings:
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.OPENAI_API_KEY = "openai-key"
            mock_settings.LLM_MODEL = "gpt-4"
            mock_settings.OPENAI_MODEL = "gpt-3.5-turbo"

            # Call the method
            result = lang_graph_agent._get_optimal_provider(messages_with_system)

            # Verify fallback provider was created
            assert isinstance(result, OpenAIProvider)
            assert result.api_key == "test-key"
            assert result.model == "gpt-4"

        # Verify error logging
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[1]
        assert error_call['error'] == "Provider selection failed"
        assert error_call['fallback_to_legacy'] is True

        # Verify STEP 48 logging for fallback
        step_48_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 48
        ]

        assert len(step_48_logs) > 0
        log_call = step_48_logs[0]
        assert log_call[1]['decision'] == "fallback_to_legacy"
        assert log_call[1]['error'] == "Provider selection failed"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_48_classification_aware_routing_strategies(
        self,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        messages_with_system,
        mock_openai_provider
    ):
        """Test STEP 48: Different domain-action combinations use appropriate routing strategies."""

        test_scenarios = [
            # (domain, action, expected_strategy, expected_cost)
            (Domain.LEGAL, Action.DOCUMENT_GENERATION, RoutingStrategy.QUALITY_FIRST, 0.030),
            (Domain.TAX, Action.CALCULATION_REQUEST, RoutingStrategy.QUALITY_FIRST, 0.020),
            (Domain.LABOR, Action.CCNL_QUERY, RoutingStrategy.BALANCED, 0.018),
            (Domain.BUSINESS, Action.INFORMATION_REQUEST, RoutingStrategy.COST_OPTIMIZED, 0.015),
        ]

        for domain, action, expected_strategy, expected_cost in test_scenarios:
            mock_log.reset_mock()
            mock_get_llm_provider.reset_mock()
            mock_get_llm_provider.return_value = mock_openai_provider

            # Set up classification
            classification = DomainActionClassification(
                domain=domain,
                action=action,
                confidence=0.8,
                reasoning=f"Test {domain.value} {action.value}"
            )
            lang_graph_agent._current_classification = classification

            # Call the method
            result = lang_graph_agent._get_optimal_provider(messages_with_system)

            # Verify routing strategy and cost
            call_args = mock_get_llm_provider.call_args[1]
            assert call_args['strategy'] == expected_strategy, f"Wrong strategy for {domain.value}-{action.value}"
            assert call_args['max_cost_eur'] == expected_cost, f"Wrong cost for {domain.value}-{action.value}"

            # Verify STEP 48 logging
            step_48_logs = [
                call for call in mock_log.call_args_list
                if len(call[1]) > 3 and call[1].get('step') == 48
            ]

            assert len(step_48_logs) > 0
            log_call = step_48_logs[0]
            assert log_call[1]['routing_strategy'] == expected_strategy.value
            assert log_call[1]['max_cost_eur'] == expected_cost
            assert log_call[1]['domain'] == domain.value
            assert log_call[1]['action'] == action.value

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.langgraph.graph.rag_step_timer')
    async def test_step_48_performance_tracking(
        self,
        mock_timer,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        messages_with_system,
        mock_openai_provider
    ):
        """Test STEP 48: Performance tracking with timer."""

        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        lang_graph_agent._current_classification = None
        mock_get_llm_provider.return_value = mock_openai_provider

        # Call the method
        result = lang_graph_agent._get_optimal_provider(messages_with_system)

        # Verify timer was used
        mock_timer.assert_called_with(
            48,
            "RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider",
            "SelectProvider"
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_48_comprehensive_logging_format(
        self,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        messages_with_system,
        tax_classification_high_quality,
        mock_openai_provider
    ):
        """Test STEP 48: Comprehensive structured logging format."""

        lang_graph_agent._current_classification = tax_classification_high_quality
        mock_get_llm_provider.return_value = mock_openai_provider

        # Call the method
        result = lang_graph_agent._get_optimal_provider(messages_with_system)

        # Find the STEP 48 log
        step_48_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 48
        ]

        assert len(step_48_logs) > 0
        log_call = step_48_logs[0]

        # Verify all required STEP 48 logging fields
        required_fields = [
            'step', 'step_id', 'node_label', 'decision', 'provider_type',
            'model', 'routing_strategy', 'max_cost_eur', 'classification_used',
            'messages_count', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field in STEP 48 log: {field}"

        # Verify specific values
        assert log_call[1]['step'] == 48
        assert log_call[1]['step_id'] == "RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider"
        assert log_call[1]['node_label'] == "SelectProvider"
        assert log_call[1]['decision'] == "provider_selected"
        assert log_call[1]['provider_type'] == LLMProviderType.OPENAI.value
        assert log_call[1]['model'] == "gpt-4"
        assert log_call[1]['routing_strategy'] == RoutingStrategy.QUALITY_FIRST.value
        assert log_call[1]['classification_used'] is True
        assert log_call[1]['messages_count'] == 3
        assert log_call[1]['processing_stage'] == "completed"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_48_edge_cases_and_defaults(
        self,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        mock_openai_provider
    ):
        """Test STEP 48: Edge cases and default handling."""

        # Test with empty messages
        empty_messages = []
        lang_graph_agent._current_classification = None
        mock_get_llm_provider.return_value = mock_openai_provider

        # Call the method
        result = lang_graph_agent._get_optimal_provider(empty_messages)

        # Verify handling of empty messages
        mock_get_llm_provider.assert_called_once()
        call_args = mock_get_llm_provider.call_args[1]
        assert call_args['messages'] == empty_messages

        # Verify STEP 48 logging handles empty messages
        step_48_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 48
        ]

        assert len(step_48_logs) > 0
        log_call = step_48_logs[0]
        assert log_call[1]['messages_count'] == 0
        assert log_call[1]['messages_empty'] is True

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.get_llm_provider')
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_48_provider_selection_context_passing(
        self,
        mock_log,
        mock_get_llm_provider,
        lang_graph_agent,
        messages_with_system,
        tax_classification_high_quality,
        mock_openai_provider
    ):
        """Test STEP 48: Verify all context is properly passed to provider selection."""

        lang_graph_agent._current_classification = tax_classification_high_quality
        mock_get_llm_provider.return_value = mock_openai_provider

        # Mock settings
        with patch('app.core.langgraph.graph.settings') as mock_settings:
            mock_settings.LLM_PREFERRED_PROVIDER = "openai"
            mock_settings.LLM_MAX_COST_EUR = 0.030

            # Call the method
            result = lang_graph_agent._get_optimal_provider(messages_with_system)

            # Verify all parameters were passed correctly
            mock_get_llm_provider.assert_called_once()
            call_args = mock_get_llm_provider.call_args[1]

            assert call_args['messages'] == messages_with_system
            assert call_args['strategy'] == RoutingStrategy.QUALITY_FIRST
            assert call_args['max_cost_eur'] == 0.020  # From classification, not settings
            assert call_args['preferred_provider'] == "openai"

        # Verify comprehensive context logging
        step_48_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 48
        ]

        assert len(step_48_logs) > 0
        log_call = step_48_logs[0]
        assert log_call[1]['classification_confidence'] == 0.95
        assert log_call[1]['preferred_provider'] == "openai"
        assert log_call[1]['settings_max_cost'] == 0.030
        assert log_call[1]['effective_max_cost'] == 0.020