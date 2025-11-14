"""
Tests for RAG STEP 46 — Replace system message

This step replaces the existing system message with a new domain-specific prompt
when a system message already exists and a classification is available.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message
from app.services.domain_action_classifier import DomainActionClassification, Domain, Action


class TestRAGStep46ReplaceSystemMessage:
    """Test suite for RAG STEP 46 - Replace system message"""

    @pytest.fixture
    def lang_graph_agent(self):
        """Create LangGraphAgent instance for testing."""
        agent = LangGraphAgent()
        # Mock dependencies
        agent._prompt_template_manager = MagicMock()
        agent._prompt_template_manager.get_prompt.return_value = "Tax-specific system prompt for deductions and calculations."
        return agent

    @pytest.fixture
    def messages_with_system(self):
        """Messages list that already contains a system message."""
        return [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What is tax deduction?"),
            Message(role="assistant", content="A tax deduction reduces taxable income.")
        ]

    @pytest.fixture
    def tax_classification(self):
        """High confidence tax domain classification."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.85,
            document_type=None,
            reasoning="High confidence tax query about deductions"
        )

    @pytest.fixture
    def labor_classification(self):
        """High confidence labor domain classification."""
        return DomainActionClassification(
            domain=Domain.LABOR,
            action=Action.CALCULATION_REQUEST,
            confidence=0.92,
            document_type=None,
            reasoning="High confidence labor query about overtime"
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_46_replace_system_message_with_tax_domain(
        self,
        mock_log,
        lang_graph_agent,
        messages_with_system,
        tax_classification
    ):
        """Test STEP 46: Replace existing system message with tax-specific prompt."""

        # Set up agent with tax classification
        lang_graph_agent._current_classification = tax_classification
        original_content = messages_with_system[0].content

        # Call the method that triggers STEP 46
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages_with_system,
            system_prompt="Tax-specific system prompt for deductions and calculations.",
            classification=tax_classification
        )

        # Verify system message was replaced
        assert result[0].role == "system"
        assert result[0].content != original_content
        assert result[0].content == "Tax-specific system prompt for deductions and calculations."
        assert len(result) == 3  # Same number of messages

        # Verify STEP 45 logging was called for the replace action
        step_45_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 45 and call[1].get('action_taken') == 'replace'
        ]

        assert len(step_45_logs) > 0, "STEP 45 replace action should be logged"
        log_call = step_45_logs[0]
        assert log_call[1]['step'] == 45
        assert log_call[1]['step_id'] == "RAG.prompting.system.message.exists"
        assert log_call[1]['node_label'] == "CheckSysMsg"
        assert log_call[1]['decision'] == "system_message_exists"
        assert log_call[1]['action_taken'] == "replace"
        assert log_call[1]['system_message_exists'] is True
        assert log_call[1]['has_classification'] is True
        assert log_call[1]['classification_confidence'] == 0.85
        assert log_call[1]['domain'] == Domain.TAX.value

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_46_replace_system_message_with_labor_domain(
        self,
        mock_log,
        lang_graph_agent,
        messages_with_system,
        labor_classification
    ):
        """Test STEP 46: Replace existing system message with labor-specific prompt."""

        # Set up agent with labor classification
        lang_graph_agent._current_classification = labor_classification
        lang_graph_agent._prompt_template_manager.get_prompt.return_value = "Labor law specialist prompt for calculations."
        original_content = messages_with_system[0].content

        # Call the method that triggers STEP 46
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages_with_system,
            system_prompt="Labor law specialist prompt for calculations.",
            classification=labor_classification
        )

        # Verify system message was replaced
        assert result[0].role == "system"
        assert result[0].content != original_content
        assert result[0].content == "Labor law specialist prompt for calculations."

        # Verify STEP 45 logging for replace action
        step_45_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 45 and call[1].get('action_taken') == 'replace'
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]['action_taken'] == "replace"
        assert log_call[1]['domain'] == Domain.LABOR.value
        assert log_call[1]['classification_confidence'] == 0.92

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_46_no_replace_without_classification(
        self,
        mock_log,
        lang_graph_agent,
        messages_with_system
    ):
        """Test STEP 46: No replacement when classification is missing."""

        # No classification provided
        lang_graph_agent._current_classification = None
        original_content = messages_with_system[0].content

        # Call the method
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages_with_system,
            system_prompt="Some prompt",
            classification=None
        )

        # System message should NOT be replaced
        assert result[0].role == "system"
        assert result[0].content == original_content  # Unchanged

        # Verify STEP 45 logging shows "keep" action
        step_45_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 45
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]['action_taken'] == "keep"
        assert log_call[1]['has_classification'] is False

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_46_replace_preserves_message_order(
        self,
        mock_log,
        lang_graph_agent,
        tax_classification
    ):
        """Test STEP 46: Replacing system message preserves order of other messages."""

        messages = [
            Message(role="system", content="Original system message"),
            Message(role="user", content="First user message"),
            Message(role="assistant", content="First assistant response"),
            Message(role="user", content="Second user message"),
            Message(role="assistant", content="Second assistant response")
        ]

        lang_graph_agent._current_classification = tax_classification

        # Call the method
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages,
            system_prompt="New tax-specific prompt",
            classification=tax_classification
        )

        # Verify structure is preserved
        assert len(result) == 5
        assert result[0].role == "system"
        assert result[0].content == "New tax-specific prompt"
        assert result[1].role == "user"
        assert result[1].content == "First user message"
        assert result[2].role == "assistant"
        assert result[2].content == "First assistant response"
        assert result[3].role == "user"
        assert result[3].content == "Second user message"
        assert result[4].role == "assistant"
        assert result[4].content == "Second assistant response"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_46_replace_with_different_message_types(
        self,
        mock_log,
        lang_graph_agent,
        tax_classification
    ):
        """Test STEP 46: Replacement works with different Message object types."""

        # Create messages with different attributes
        messages = [
            Message(role="system", content="Original", metadata={"type": "system"}),
            Message(role="user", content="Question", metadata={"timestamp": "123"})
        ]

        lang_graph_agent._current_classification = tax_classification

        # Call the method
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages,
            system_prompt="Replaced system prompt",
            classification=tax_classification
        )

        # Verify replacement preserved message structure
        assert result[0].role == "system"
        assert result[0].content == "Replaced system prompt"
        # The replaced message should be same type as original
        assert isinstance(result[0], type(messages[0]))

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_46_replace_with_low_confidence_classification(
        self,
        mock_log,
        lang_graph_agent,
        messages_with_system
    ):
        """Test STEP 46: Replacement occurs even with low confidence classification."""

        # Low confidence classification
        low_conf_classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.3,  # Low confidence
            document_type=None,
            reasoning="Uncertain tax classification"
        )

        lang_graph_agent._current_classification = low_conf_classification
        original_content = messages_with_system[0].content

        # Call the method
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages_with_system,
            system_prompt="Low confidence tax prompt",
            classification=low_conf_classification
        )

        # Should still replace (classification presence matters, not confidence)
        assert result[0].content != original_content
        assert result[0].content == "Low confidence tax prompt"

        # Verify logging shows replacement with low confidence
        step_45_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 45 and call[1].get('action_taken') == 'replace'
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]['classification_confidence'] == 0.3

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_46_replace_system_message_comprehensive_logging(
        self,
        mock_log,
        lang_graph_agent,
        messages_with_system,
        tax_classification
    ):
        """Test STEP 46: Comprehensive structured logging for replace action."""

        lang_graph_agent._current_classification = tax_classification

        # Call the method
        lang_graph_agent._prepare_messages_with_system_prompt(
            messages_with_system,
            system_prompt="Comprehensive test prompt",
            classification=tax_classification
        )

        # Find the replace action log
        step_45_replace_logs = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and
                call[1].get('step') == 45 and
                call[1].get('action_taken') == 'replace')
        ]

        assert len(step_45_replace_logs) > 0
        log_call = step_45_replace_logs[0]

        # Verify all required STEP 45 logging fields for replace action
        required_fields = [
            'step', 'step_id', 'node_label', 'decision', 'action_taken',
            'system_message_exists', 'has_classification', 'messages_count',
            'original_messages_count', 'classification_confidence', 'domain', 'action'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field in STEP 45 replace log: {field}"

        # Verify specific values for replace action
        assert log_call[1]['step'] == 45
        assert log_call[1]['step_id'] == "RAG.prompting.system.message.exists"
        assert log_call[1]['node_label'] == "CheckSysMsg"
        assert log_call[1]['decision'] == "system_message_exists"
        assert log_call[1]['action_taken'] == "replace"
        assert log_call[1]['system_message_exists'] is True
        assert log_call[1]['has_classification'] is True
        assert log_call[1]['messages_count'] == 3
        assert log_call[1]['original_messages_count'] == 3
        assert log_call[1]['classification_confidence'] == 0.85
        assert log_call[1]['domain'] == Domain.TAX.value
        assert log_call[1]['action'] == Action.INFORMATION_REQUEST.value
        assert log_call[1]['processing_stage'] == "completed"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.langgraph.graph.rag_step_timer')
    async def test_step_46_performance_tracking_during_replace(
        self,
        mock_timer,
        mock_log,
        lang_graph_agent,
        messages_with_system,
        tax_classification
    ):
        """Test STEP 46: Performance tracking during system message replacement."""

        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        lang_graph_agent._current_classification = tax_classification

        # Call the method
        lang_graph_agent._prepare_messages_with_system_prompt(
            messages_with_system,
            system_prompt="Performance test prompt",
            classification=tax_classification
        )

        # Verify timer was used for STEP 45 (which includes replace logic)
        mock_timer.assert_called_with(
            45,
            "RAG.prompting.system.message.exists",
            "CheckSysMsg"
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_46_replace_multiple_scenarios(
        self,
        mock_log,
        lang_graph_agent
    ):
        """Test STEP 46: Replace behavior across multiple domain scenarios."""

        scenarios = [
            # (domain, action, confidence, expected_domain_value, expected_action_value)
            (Domain.TAX, Action.INFORMATION_REQUEST, 0.9, "tax", "information_request"),
            (Domain.LABOR, Action.CALCULATION_REQUEST, 0.8, "labor", "calculation_request"),
            (Domain.LEGAL, Action.DOCUMENT_ANALYSIS, 0.7, "legal", "document_analysis"),
        ]

        for domain, action, confidence, expected_domain, expected_action in scenarios:
            mock_log.reset_mock()

            messages = [
                Message(role="system", content="Generic system message"),
                Message(role="user", content=f"Query about {domain.value}")
            ]

            classification = DomainActionClassification(
                domain=domain,
                action=action,
                confidence=confidence,
                reasoning=f"Test {domain.value} classification"
            )

            lang_graph_agent._current_classification = classification

            # Call the method
            lang_graph_agent._prepare_messages_with_system_prompt(
                messages,
                system_prompt=f"{domain.value.title()} domain-specific prompt",
                classification=classification
            )

            # Verify replacement occurred
            assert messages[0].content == f"{domain.value.title()} domain-specific prompt"

            # Verify logging
            step_45_logs = [
                call for call in mock_log.call_args_list
                if (len(call[1]) > 3 and
                    call[1].get('step') == 45 and
                    call[1].get('action_taken') == 'replace')
            ]

            assert len(step_45_logs) > 0, f"No STEP 45 replace log for {domain.value}"
            log_call = step_45_logs[0]
            assert log_call[1]['domain'] == expected_domain
            assert log_call[1]['action'] == expected_action
            assert log_call[1]['classification_confidence'] == confidence