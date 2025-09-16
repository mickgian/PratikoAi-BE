"""
Tests for RAG STEP 41 — LangGraphAgent._get_system_prompt Select appropriate prompt

This step selects the appropriate system prompt based on domain-action classification
confidence. It either uses domain-specific prompts or falls back to the default
system prompt based on classification confidence thresholds.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.core.prompts import SYSTEM_PROMPT
from app.schemas.chat import Message
from app.services.domain_action_classifier import DomainActionClassification, Domain, Action


class TestRAGStep41SystemPromptSelection:
    """Test suite for RAG STEP 41 - LangGraphAgent._get_system_prompt Select appropriate prompt."""

    @pytest.fixture
    def mock_prompt_template_manager(self):
        """Mock prompt template manager."""
        manager = MagicMock()
        manager.get_prompt.return_value = "Domain-specific system prompt for tax consultation."
        return manager

    @pytest.fixture
    def lang_graph_agent(self, mock_prompt_template_manager):
        """Create LangGraphAgent instance for testing."""
        agent = LangGraphAgent()
        agent._prompt_template_manager = mock_prompt_template_manager
        return agent

    @pytest.fixture
    def sample_messages(self):
        """Sample conversation messages."""
        return [
            Message(role="user", content="I need help with my tax deductions"),
            Message(role="assistant", content="I can help you with tax deductions. What specific questions do you have?"),
            Message(role="user", content="What business expenses can I deduct?")
        ]

    @pytest.fixture
    def high_confidence_classification(self):
        """High confidence domain-action classification."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.85,  # Above threshold
            document_type=None,
            reasoning="Clear tax consultation query with high confidence"
        )

    @pytest.fixture
    def low_confidence_classification(self):
        """Low confidence domain-action classification."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.45,  # Below threshold
            document_type=None,
            reasoning="Uncertain classification due to ambiguous query"
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_system_prompt_high_confidence_classification(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        high_confidence_classification,
        mock_prompt_template_manager
    ):
        """Test system prompt selection with high confidence classification."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)
        
        # Should use domain-specific prompt
        assert result == "Domain-specific system prompt for tax consultation."
        
        # Verify PromptTemplateManager was called correctly
        mock_prompt_template_manager.get_prompt.assert_called_once_with(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            query="What business expenses can I deduct?",  # Latest user message
            context=None,
            document_type=None
        )
        
        # Verify structured logging was called
        mock_log.assert_called()
        
        # Find the prompt selection log call
        selection_log_calls = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 41
        ]
        
        assert len(selection_log_calls) > 0
        log_call = selection_log_calls[0]
        assert log_call[1]['step'] == 41
        assert log_call[1]['step_id'] == "RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt"
        assert log_call[1]['node_label'] == "SelectPrompt"
        assert log_call[1]['classification_confidence'] == 0.85
        assert log_call[1]['prompt_type'] == "domain_specific"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_system_prompt_low_confidence_classification(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        low_confidence_classification
    ):
        """Test system prompt selection with low confidence classification."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, low_confidence_classification)
        
        # Should use default prompt due to low confidence
        assert result == SYSTEM_PROMPT or result.startswith("You are PraticoAI")
        
        # Verify structured logging was called
        mock_log.assert_called()
        
        # Find the prompt selection log call
        selection_log_calls = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 41
        ]
        
        assert len(selection_log_calls) > 0
        log_call = selection_log_calls[0]
        assert log_call[1]['step'] == 41
        assert log_call[1]['classification_confidence'] == 0.45
        assert log_call[1]['prompt_type'] == "default"
        assert log_call[1]['confidence_below_threshold'] is True

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_system_prompt_no_classification(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test system prompt selection with no classification available."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, None)
        
        # Should use default prompt when no classification
        assert result == SYSTEM_PROMPT or result.startswith("You are PraticoAI")
        
        # Verify structured logging was called
        mock_log.assert_called()
        
        selection_log_calls = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 41
        ]
        
        assert len(selection_log_calls) > 0
        log_call = selection_log_calls[0]
        assert log_call[1]['prompt_type'] == "default"
        assert log_call[1]['classification_available'] is False

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_system_prompt_empty_messages(
        self,
        mock_log,
        lang_graph_agent,
        high_confidence_classification
    ):
        """Test system prompt selection with empty messages."""
        
        result = lang_graph_agent._get_system_prompt([], high_confidence_classification)
        
        # Should still work with domain prompt but empty query
        assert result == "Domain-specific system prompt for tax consultation."

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log') 
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_system_prompt_domain_prompt_error(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        high_confidence_classification,
        mock_prompt_template_manager
    ):
        """Test system prompt selection when domain prompt generation fails."""
        
        # Mock domain prompt generation to raise exception
        mock_prompt_template_manager.get_prompt.side_effect = Exception("Prompt generation failed")
        
        result = lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)
        
        # Should fallback to default prompt on error
        assert result == SYSTEM_PROMPT or result.startswith("You are PraticoAI")
        
        # Verify error logging
        selection_log_calls = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 41
        ]
        
        assert len(selection_log_calls) > 0
        log_call = selection_log_calls[0]
        assert log_call[1]['prompt_type'] == "default"
        assert log_call[1]['error_fallback'] is True

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_system_prompt_different_domains(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test system prompt selection with different domain classifications."""
        
        # Test LABOR domain
        labor_classification = DomainActionClassification(
            domain=Domain.LABOR,
            action=Action.INFORMATION_REQUEST,
            confidence=0.75,
            document_type=None,
            keywords=["employment", "contract"],
            reasoning="Labor law consultation"
        )
        
        lang_graph_agent._prompt_template_manager.get_prompt.return_value = "Labor-specific system prompt."
        
        result = lang_graph_agent._get_system_prompt(sample_messages, labor_classification)
        
        assert result == "Labor-specific system prompt."
        
        # Verify correct domain was passed
        lang_graph_agent._prompt_template_manager.get_prompt.assert_called_with(
            domain=Domain.LABOR,
            action=Action.INFORMATION_REQUEST,
            query="What business expenses can I deduct?",
            context=None,
            document_type=None
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_system_prompt_messages_without_user_content(
        self,
        mock_log,
        lang_graph_agent,
        high_confidence_classification
    ):
        """Test system prompt selection when messages have no user content."""
        
        messages_no_user = [
            Message(role="assistant", content="Hello, how can I help?"),
            Message(role="system", content="System message")
        ]
        
        result = lang_graph_agent._get_system_prompt(messages_no_user, high_confidence_classification)
        
        # Should still use domain prompt with empty query
        assert result == "Domain-specific system prompt for tax consultation."
        
        # Verify empty query was passed
        lang_graph_agent._prompt_template_manager.get_prompt.assert_called_with(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            query="",  # Empty query when no user messages found
            context=None,
            document_type=None
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.langgraph.graph.rag_step_timer')
    async def test_system_prompt_performance_tracking(
        self,
        mock_timer,
        mock_log,
        lang_graph_agent,
        sample_messages,
        high_confidence_classification
    ):
        """Test that system prompt selection includes performance tracking."""
        
        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()
        
        result = lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)
        
        # Verify timer was used
        mock_timer.assert_called_with(
            41,
            "RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt",
            "SelectPrompt",
            classification_confidence=0.85,
            domain=Domain.TAX.value
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_structured_logging_format_comprehensive(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        high_confidence_classification
    ):
        """Test comprehensive structured logging format for STEP 41."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)
        
        # Verify all required logging fields are present
        mock_log.assert_called()
        
        # Find all STEP 41 log calls
        step_41_logs = [
            call for call in mock_log.call_args_list
            if call[1].get('step') == 41
        ]
        
        assert len(step_41_logs) > 0
        
        # Check the main log call has all required fields
        main_log = step_41_logs[0]
        required_fields = [
            'step', 'step_id', 'node_label', 'classification_confidence',
            'prompt_type', 'domain', 'action', 'user_query'
        ]
        
        for field in required_fields:
            assert field in main_log[1], f"Missing required field: {field}"
        
        assert main_log[1]['step'] == 41
        assert main_log[1]['step_id'] == "RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt"
        assert main_log[1]['node_label'] == "SelectPrompt"