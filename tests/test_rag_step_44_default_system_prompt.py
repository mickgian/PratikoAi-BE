"""
Tests for RAG STEP 44 — Use default SYSTEM_PROMPT

This step uses the default system prompt when classification confidence is below
threshold or when no classification is available. It follows from the ClassConfidence
decision node in the RAG workflow.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.langgraph.graph import LangGraphAgent
from app.core.prompts import SYSTEM_PROMPT
from app.schemas.chat import Message
from app.services.domain_action_classifier import DomainActionClassification, Domain, Action


class TestRAGStep44DefaultSystemPrompt:
    """Test suite for RAG STEP 44 - Use default SYSTEM_PROMPT."""

    @pytest.fixture
    def mock_prompt_template_manager(self):
        """Mock prompt template manager."""
        manager = MagicMock()
        manager.get_prompt.return_value = "Domain-specific system prompt."
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
            Message(role="user", content="Can you help me with general questions?")
        ]

    @pytest.fixture
    def low_confidence_classification(self):
        """Low confidence classification that should trigger default prompt."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.3,  # Below default 0.6 threshold
            document_type=None,
            reasoning="Low confidence classification"
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_step_44_no_classification_uses_default_prompt(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 44: No classification available -> use default SYSTEM_PROMPT."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, None)
        
        # Should use default system prompt
        assert result == SYSTEM_PROMPT
        assert "world class assistant" in result  # Content from system.md
        
        # Verify STEP 44 structured logging was called
        mock_log.assert_called()
        
        # Find STEP 44 log calls
        step_44_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 44
        ]
        
        assert len(step_44_logs) > 0
        log_call = step_44_logs[0]
        assert log_call[1]['step'] == 44
        assert log_call[1]['step_id'] == "RAG.prompting.use.default.system.prompt"
        assert log_call[1]['node_label'] == "DefaultSysPrompt"
        assert log_call[1]['prompt_type'] == "default"
        assert log_call[1]['trigger_reason'] == "no_classification"
        assert log_call[1]['classification_available'] is False

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_step_44_low_confidence_uses_default_prompt(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        low_confidence_classification
    ):
        """Test STEP 44: Low confidence classification -> use default SYSTEM_PROMPT."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, low_confidence_classification)
        
        # Should use default system prompt
        assert result == SYSTEM_PROMPT
        
        # Verify STEP 44 structured logging was called
        step_44_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 44
        ]
        
        assert len(step_44_logs) > 0
        log_call = step_44_logs[0]
        assert log_call[1]['step'] == 44
        assert log_call[1]['step_id'] == "RAG.prompting.use.default.system.prompt"
        assert log_call[1]['node_label'] == "DefaultSysPrompt"
        assert log_call[1]['prompt_type'] == "default"
        assert log_call[1]['trigger_reason'] == "low_confidence"
        assert log_call[1]['classification_available'] is True
        assert log_call[1]['classification_confidence'] == 0.3
        assert log_call[1]['confidence_threshold'] == 0.6
        assert log_call[1]['domain'] == Domain.TAX.value

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.8)  # Higher threshold
    async def test_step_44_different_threshold_configuration(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 44: Different threshold causes higher confidence to use default."""
        
        # Classification with 0.7 confidence, but threshold is 0.8
        medium_confidence = DomainActionClassification(
            domain=Domain.LEGAL,
            action=Action.DOCUMENT_GENERATION,
            confidence=0.7,  # Below 0.8 threshold
            document_type=None,
            reasoning="Medium confidence classification"
        )
        
        result = lang_graph_agent._get_system_prompt(sample_messages, medium_confidence)
        
        # Should use default prompt due to higher threshold
        assert result == SYSTEM_PROMPT
        
        # Verify STEP 44 logging shows correct threshold comparison
        step_44_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 44
        ]
        
        assert len(step_44_logs) > 0
        log_call = step_44_logs[0]
        assert log_call[1]['classification_confidence'] == 0.7
        assert log_call[1]['confidence_threshold'] == 0.8
        assert log_call[1]['trigger_reason'] == "low_confidence"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_44_prompt_content_validation(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 44: Validate the content of the default system prompt."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, None)
        
        # Should contain expected content from system.md
        assert "world class assistant" in result
        assert "friendly and professional" in result
        assert "don't know" in result
        assert "Current date and time" in result
        
        # Verify STEP 44 logging includes prompt characteristics
        step_44_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 44
        ]
        
        assert len(step_44_logs) > 0
        log_call = step_44_logs[0]
        assert 'prompt_length' in log_call[1]
        assert log_call[1]['prompt_length'] > 0
        assert isinstance(log_call[1]['prompt_length'], int)

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_44_edge_case_exactly_at_threshold(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 44: Edge case where confidence exactly equals threshold."""
        
        # This should NOT trigger STEP 44 (should use domain prompt)
        exact_threshold = DomainActionClassification(
            domain=Domain.BUSINESS,
            action=Action.STRATEGIC_ADVICE,
            confidence=0.6,  # Exactly at threshold
            document_type=None,
            reasoning="Exact threshold classification"
        )
        
        result = lang_graph_agent._get_system_prompt(sample_messages, exact_threshold)
        
        # Should use domain-specific prompt (NOT default)
        assert result != SYSTEM_PROMPT
        assert result == "Domain-specific system prompt."
        
        # Should NOT have STEP 44 logging (should have STEP 43 instead)
        step_44_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 44
        ]
        
        # No STEP 44 logs because we used domain prompt
        assert len(step_44_logs) == 0

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.langgraph.graph.rag_step_timer')
    async def test_step_44_performance_tracking_with_timer(
        self,
        mock_timer,
        mock_log,
        lang_graph_agent,
        sample_messages,
        low_confidence_classification
    ):
        """Test STEP 44: Performance tracking with timer."""
        
        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()
        
        result = lang_graph_agent._get_system_prompt(sample_messages, low_confidence_classification)
        
        # Should use default prompt
        assert result == SYSTEM_PROMPT
        
        # Verify STEP 44 timer was used
        step_44_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 44
        ]
        
        assert len(step_44_logs) > 0
        log_call = step_44_logs[0]
        # Should include performance metrics
        assert 'processing_stage' in log_call[1]
        assert log_call[1]['processing_stage'] == "completed"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_44_comprehensive_logging_format(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        low_confidence_classification
    ):
        """Test STEP 44: Comprehensive structured logging format."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, low_confidence_classification)
        
        # Verify all required STEP 44 logging fields
        step_44_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 44
        ]
        
        assert len(step_44_logs) > 0
        log_call = step_44_logs[0]
        
        # Verify all required fields for STEP 44
        required_fields = [
            'step', 'step_id', 'node_label', 'prompt_type', 'trigger_reason',
            'classification_available', 'prompt_length', 'user_query'
        ]
        
        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"
        
        # Verify specific values
        assert log_call[1]['step'] == 44
        assert log_call[1]['step_id'] == "RAG.prompting.use.default.system.prompt"
        assert log_call[1]['node_label'] == "DefaultSysPrompt"
        assert log_call[1]['prompt_type'] == "default"
        assert log_call[1]['user_query'] == "Can you help me with general questions?"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_44_different_trigger_scenarios(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 44: Different scenarios that trigger default prompt usage."""
        
        test_scenarios = [
            # Scenario 1: No classification
            (None, "no_classification"),
            
            # Scenario 2: Very low confidence
            (DomainActionClassification(
                domain=Domain.TAX,
                action=Action.INFORMATION_REQUEST,
                confidence=0.1,
                reasoning="Very low confidence"
            ), "low_confidence"),
            
            # Scenario 3: Just below threshold
            (DomainActionClassification(
                domain=Domain.LEGAL,
                action=Action.DOCUMENT_GENERATION,
                confidence=0.59,  # Just below 0.6
                reasoning="Just below threshold"
            ), "low_confidence")
        ]
        
        for classification, expected_reason in test_scenarios:
            mock_log.reset_mock()
            
            result = lang_graph_agent._get_system_prompt(sample_messages, classification)
            
            # Should always use default prompt
            assert result == SYSTEM_PROMPT
            
            # Verify STEP 44 logging with correct reason
            step_44_logs = [
                call for call in mock_log.call_args_list
                if len(call[1]) > 3 and call[1].get('step') == 44
            ]
            
            assert len(step_44_logs) > 0, f"No STEP 44 logging for scenario {expected_reason}"
            log_call = step_44_logs[0]
            assert log_call[1]['trigger_reason'] == expected_reason

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_44_empty_messages_handled(
        self,
        mock_log,
        lang_graph_agent
    ):
        """Test STEP 44: Handle empty messages gracefully."""
        
        result = lang_graph_agent._get_system_prompt([], None)
        
        # Should still use default prompt
        assert result == SYSTEM_PROMPT
        
        # Verify STEP 44 logging handles empty messages
        step_44_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 44
        ]
        
        assert len(step_44_logs) > 0
        log_call = step_44_logs[0]
        assert log_call[1]['user_query'] == ""  # Should handle empty query gracefully

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_44_various_domains_with_low_confidence(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 44: All domains with low confidence use default prompt."""
        
        domains_to_test = [
            Domain.TAX,
            Domain.LEGAL, 
            Domain.LABOR,
            Domain.BUSINESS,
            Domain.ACCOUNTING
        ]
        
        for domain in domains_to_test:
            mock_log.reset_mock()
            
            low_confidence = DomainActionClassification(
                domain=domain,
                action=Action.INFORMATION_REQUEST,
                confidence=0.2,  # Low confidence
                reasoning=f"Low confidence {domain.value} query"
            )
            
            result = lang_graph_agent._get_system_prompt(sample_messages, low_confidence)
            
            # Should use default prompt for all domains when confidence is low
            assert result == SYSTEM_PROMPT
            
            # Verify STEP 44 logging includes domain info
            step_44_logs = [
                call for call in mock_log.call_args_list
                if len(call[1]) > 3 and call[1].get('step') == 44
            ]
            
            assert len(step_44_logs) > 0, f"No STEP 44 logging for domain {domain.value}"
            log_call = step_44_logs[0]
            assert log_call[1]['domain'] == domain.value
            assert log_call[1]['trigger_reason'] == "low_confidence"