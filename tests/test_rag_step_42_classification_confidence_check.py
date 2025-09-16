"""
Tests for RAG STEP 42 — Classification exists and confidence at least 0.6?

This step is the decision node that determines whether to use domain-specific
prompts or fall back to the default system prompt based on classification
existence and confidence threshold (default 0.6).
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message
from app.services.domain_action_classifier import DomainActionClassification, Domain, Action


class TestRAGStep42ClassificationConfidenceCheck:
    """Test suite for RAG STEP 42 - Classification exists and confidence at least 0.6?"""

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
            Message(role="user", content="I need help with tax calculations")
        ]

    @pytest.fixture
    def high_confidence_classification(self):
        """High confidence classification (≥ 0.6)."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.75,  # Above 0.6 threshold
            document_type=None,
            reasoning="High confidence tax calculation query"
        )

    @pytest.fixture
    def exact_threshold_classification(self):
        """Exact threshold classification (= 0.6)."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.6,  # Exactly at threshold
            document_type=None,
            reasoning="Exact threshold classification"
        )

    @pytest.fixture
    def low_confidence_classification(self):
        """Low confidence classification (< 0.6)."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.45,  # Below 0.6 threshold
            document_type=None,
            reasoning="Low confidence classification"
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_step_42_high_confidence_uses_domain_prompt(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        high_confidence_classification,
        mock_prompt_template_manager
    ):
        """Test STEP 42 decision: high confidence (≥ 0.6) -> use domain prompt."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)
        
        # Should use domain-specific prompt
        assert result == "Domain-specific system prompt."
        
        # Verify PromptTemplateManager was called
        mock_prompt_template_manager.get_prompt.assert_called_once_with(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            query="I need help with tax calculations",
            context=None,
            document_type=None
        )
        
        # Verify STEP 41 logging was called (which contains the decision logic)
        mock_log.assert_called()
        
        # Find the log call that shows domain prompt was used (STEP 42 decision outcome)
        domain_prompt_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('prompt_type') == 'domain_specific'
        ]
        
        assert len(domain_prompt_logs) > 0
        log_call = domain_prompt_logs[0]
        assert log_call[1]['classification_confidence'] == 0.75
        assert log_call[1]['confidence_below_threshold'] is False  # STEP 42 decision outcome

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_step_42_exact_threshold_uses_domain_prompt(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        exact_threshold_classification
    ):
        """Test STEP 42 decision: exact threshold (= 0.6) -> use domain prompt."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, exact_threshold_classification)
        
        # Should use domain-specific prompt (>= threshold)
        assert result == "Domain-specific system prompt."
        
        # Find the domain prompt log call
        domain_prompt_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('prompt_type') == 'domain_specific'
        ]
        
        assert len(domain_prompt_logs) > 0
        log_call = domain_prompt_logs[0]
        assert log_call[1]['classification_confidence'] == 0.6
        assert log_call[1]['confidence_below_threshold'] is False  # STEP 42 decision: meets threshold

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_step_42_low_confidence_uses_default_prompt(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        low_confidence_classification
    ):
        """Test STEP 42 decision: low confidence (< 0.6) -> use default prompt."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, low_confidence_classification)
        
        # Should use default prompt
        from app.core.prompts import SYSTEM_PROMPT
        assert result == SYSTEM_PROMPT
        
        # Find the log call that shows default prompt was used due to low confidence
        default_prompt_logs = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and 
                call[1].get('prompt_type') == 'default' and
                call[1].get('confidence_below_threshold') is True)
        ]
        
        assert len(default_prompt_logs) > 0
        log_call = default_prompt_logs[0]
        assert log_call[1]['classification_confidence'] == 0.45
        assert log_call[1]['confidence_below_threshold'] is True  # STEP 42 decision outcome
        assert log_call[1]['reason'] == 'low_confidence'

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_42_no_classification_uses_default_prompt(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 42 decision: no classification -> use default prompt."""
        
        result = lang_graph_agent._get_system_prompt(sample_messages, None)
        
        # Should use default prompt
        from app.core.prompts import SYSTEM_PROMPT
        assert result == SYSTEM_PROMPT
        
        # Find the log call that shows no classification available
        no_classification_logs = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and 
                call[1].get('classification_available') is False)
        ]
        
        assert len(no_classification_logs) > 0
        log_call = no_classification_logs[0]
        assert log_call[1]['prompt_type'] == 'default'
        assert log_call[1]['reason'] == 'no_classification'

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.8)  # Higher threshold
    async def test_step_42_different_threshold_configuration(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages,
        high_confidence_classification  # 0.75 confidence
    ):
        """Test STEP 42 with different threshold configuration."""
        
        # With threshold = 0.8, confidence 0.75 should use default prompt
        result = lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)
        
        from app.core.prompts import SYSTEM_PROMPT
        assert result == SYSTEM_PROMPT
        
        # Find the default prompt log call
        default_prompt_logs = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and 
                call[1].get('confidence_below_threshold') is True)
        ]
        
        assert len(default_prompt_logs) > 0
        log_call = default_prompt_logs[0]
        assert log_call[1]['classification_confidence'] == 0.75
        assert log_call[1]['confidence_threshold'] == 0.8
        assert log_call[1]['confidence_below_threshold'] is True

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_step_42_edge_case_very_high_confidence(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 42 decision with very high confidence classification."""
        
        very_high_confidence = DomainActionClassification(
            domain=Domain.LEGAL,
            action=Action.DOCUMENT_GENERATION,
            confidence=0.95,  # Very high confidence
            document_type=None,
            reasoning="Very high confidence legal document generation"
        )
        
        result = lang_graph_agent._get_system_prompt(sample_messages, very_high_confidence)
        
        # Should definitely use domain prompt
        assert result == "Domain-specific system prompt."
        
        # Check logging shows high confidence decision
        domain_logs = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and call[1].get('prompt_type') == 'domain_specific')
        ]
        
        assert len(domain_logs) > 0
        log_call = domain_logs[0]
        assert log_call[1]['classification_confidence'] == 0.95
        assert log_call[1]['confidence_below_threshold'] is False

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_step_42_edge_case_very_low_confidence(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 42 decision with very low confidence classification."""
        
        very_low_confidence = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.1,  # Very low confidence
            document_type=None,
            reasoning="Very low confidence classification"
        )
        
        result = lang_graph_agent._get_system_prompt(sample_messages, very_low_confidence)
        
        # Should definitely use default prompt
        from app.core.prompts import SYSTEM_PROMPT
        assert result == SYSTEM_PROMPT
        
        # Check logging shows low confidence decision
        default_logs = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and call[1].get('confidence_below_threshold') is True)
        ]
        
        assert len(default_logs) > 0
        log_call = default_logs[0]
        assert log_call[1]['classification_confidence'] == 0.1
        assert log_call[1]['confidence_below_threshold'] is True

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.6)
    async def test_step_42_different_domains_high_confidence(
        self,
        mock_log,
        lang_graph_agent,
        sample_messages
    ):
        """Test STEP 42 decision works consistently across different domains."""
        
        domains_to_test = [
            (Domain.TAX, Action.CALCULATION_REQUEST),
            (Domain.LEGAL, Action.DOCUMENT_GENERATION),
            (Domain.LABOR, Action.INFORMATION_REQUEST),
            (Domain.BUSINESS, Action.STRATEGIC_ADVICE),
            (Domain.ACCOUNTING, Action.COMPLIANCE_CHECK)
        ]
        
        for domain, action in domains_to_test:
            mock_log.reset_mock()
            
            classification = DomainActionClassification(
                domain=domain,
                action=action,
                confidence=0.8,  # High confidence
                document_type=None,
                reasoning=f"High confidence {domain.value} {action.value}"
            )
            
            result = lang_graph_agent._get_system_prompt(sample_messages, classification)
            
            # Should use domain prompt for all high confidence classifications
            assert result == "Domain-specific system prompt."
            
            # Check logging
            domain_logs = [
                call for call in mock_log.call_args_list
                if (len(call[1]) > 3 and call[1].get('confidence_below_threshold') is False)
            ]
            
            assert len(domain_logs) > 0
            log_call = domain_logs[0]
            assert log_call[1]['domain'] == domain.value
            assert log_call[1]['action'] == action.value
            assert log_call[1]['classification_confidence'] == 0.8