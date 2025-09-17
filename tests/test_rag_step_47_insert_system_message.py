"""
Tests for RAG STEP 47 — Insert system message

This step inserts a new system message when no system message exists in the
conversation messages. It's triggered after STEP 45 (CheckSysMsg) determines
that no system message is present.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message
from app.services.domain_action_classifier import DomainActionClassification, Domain, Action


class TestRAGStep47InsertSystemMessage:
    """Test suite for RAG STEP 47 - Insert system message"""

    @pytest.fixture
    def lang_graph_agent(self):
        """Create LangGraphAgent instance for testing."""
        agent = LangGraphAgent()
        # Mock dependencies
        agent._prompt_template_manager = MagicMock()
        agent._prompt_template_manager.get_prompt.return_value = "Domain-specific system prompt for tax queries."
        return agent

    @pytest.fixture
    def messages_without_system(self):
        """Messages list without a system message."""
        return [
            Message(role="user", content="What is tax deduction?"),
            Message(role="assistant", content="A tax deduction reduces taxable income.")
        ]

    @pytest.fixture
    def empty_messages(self):
        """Empty messages list."""
        return []

    @pytest.fixture
    def single_user_message(self):
        """Single user message without system message."""
        return [Message(role="user", content="How do I calculate overtime pay?")]

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
    async def test_step_47_insert_system_message_with_classification(
        self,
        mock_log,
        lang_graph_agent,
        messages_without_system,
        tax_classification
    ):
        """Test STEP 47: Insert system message when none exists and classification available."""

        # Set up agent with classification
        lang_graph_agent._current_classification = tax_classification
        original_count = len(messages_without_system)

        # Call the method that triggers STEP 47
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages_without_system,
            system_prompt="Tax-specific system prompt for deductions.",
            classification=tax_classification
        )

        # Verify system message was inserted at position 0
        assert len(result) == original_count + 1
        assert result[0].role == "system"
        assert result[0].content == "Tax-specific system prompt for deductions."
        assert result[1].role == "user"  # Original first message moved to position 1
        assert result[1].content == "What is tax deduction?"

        # Verify STEP 47 logging was called for insert action
        step_47_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 47
        ]

        assert len(step_47_logs) > 0, "STEP 47 insert action should be logged"
        log_call = step_47_logs[0]
        assert log_call[1]['step'] == 47
        assert log_call[1]['step_id'] == "RAG.prompting.insert.system.message"
        assert log_call[1]['node_label'] == "InsertMsg"
        assert log_call[1]['decision'] == "system_message_inserted"
        assert log_call[1]['action_taken'] == "insert"
        assert log_call[1]['system_message_exists'] is False
        assert log_call[1]['has_classification'] is True
        assert log_call[1]['classification_confidence'] == 0.85
        assert log_call[1]['domain'] == Domain.TAX.value
        assert log_call[1]['insert_position'] == 0
        assert log_call[1]['messages_count'] == original_count + 1

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_47_insert_system_message_without_classification(
        self,
        mock_log,
        lang_graph_agent,
        messages_without_system
    ):
        """Test STEP 47: Insert default system message when no classification available."""

        # No classification provided
        lang_graph_agent._current_classification = None
        original_count = len(messages_without_system)

        # Call the method with default system prompt
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages_without_system,
            system_prompt="You are a helpful assistant.",
            classification=None
        )

        # Verify system message was inserted
        assert len(result) == original_count + 1
        assert result[0].role == "system"
        assert result[0].content == "You are a helpful assistant."

        # Verify STEP 47 logging for insert without classification
        step_47_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 47
        ]

        assert len(step_47_logs) > 0
        log_call = step_47_logs[0]
        assert log_call[1]['action_taken'] == "insert"
        assert log_call[1]['has_classification'] is False
        assert log_call[1]['classification_confidence'] is None
        assert log_call[1]['domain'] is None

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_47_insert_system_message_empty_messages(
        self,
        mock_log,
        lang_graph_agent,
        empty_messages,
        labor_classification
    ):
        """Test STEP 47: Insert system message when messages list is empty."""

        lang_graph_agent._current_classification = labor_classification

        # Call the method
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            empty_messages,
            system_prompt="Labor law specialist prompt for calculations.",
            classification=labor_classification
        )

        # Should have inserted a system message into empty list
        assert len(result) == 1
        assert result[0].role == "system"
        assert result[0].content == "Labor law specialist prompt for calculations."

        # Verify STEP 47 logging for empty messages
        step_47_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 47
        ]

        assert len(step_47_logs) > 0
        log_call = step_47_logs[0]
        assert log_call[1]['messages_empty'] is True
        assert log_call[1]['original_messages_count'] == 0
        assert log_call[1]['messages_count'] == 1
        assert log_call[1]['domain'] == Domain.LABOR.value

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_47_insert_preserves_message_order(
        self,
        mock_log,
        lang_graph_agent,
        tax_classification
    ):
        """Test STEP 47: Inserting system message preserves order of existing messages."""

        messages = [
            Message(role="user", content="First user message"),
            Message(role="assistant", content="First assistant response"),
            Message(role="user", content="Second user message"),
            Message(role="assistant", content="Second assistant response")
        ]

        lang_graph_agent._current_classification = tax_classification

        # Call the method
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages,
            system_prompt="Tax advisor system prompt",
            classification=tax_classification
        )

        # Verify system message inserted at beginning and order preserved
        assert len(result) == 5  # 1 system + 4 original
        assert result[0].role == "system"
        assert result[0].content == "Tax advisor system prompt"
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
    async def test_step_47_insert_with_different_message_types(
        self,
        mock_log,
        lang_graph_agent,
        tax_classification
    ):
        """Test STEP 47: Insertion works with different Message object types."""

        # Create messages
        messages = [
            Message(role="user", content="Question about tax deductions")
        ]

        lang_graph_agent._current_classification = tax_classification

        # Call the method
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages,
            system_prompt="Inserted system prompt",
            classification=tax_classification
        )

        # Verify insertion worked correctly
        assert len(result) == 2
        assert result[0].role == "system"
        assert result[0].content == "Inserted system prompt"
        assert result[1].role == "user"
        assert result[1].content == "Question about tax deductions"
        # The message should be the same type as the original
        assert isinstance(result[1], type(messages[0]))

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_47_insert_with_various_starting_roles(
        self,
        mock_log,
        lang_graph_agent
    ):
        """Test STEP 47: Insert system message regardless of first message role."""

        test_scenarios = [
            # (starting_messages, expected_system_insert)
            ([Message(role="user", content="User first")], True),
            ([Message(role="assistant", content="Assistant first")], True),
            ([], True),  # Empty list
        ]

        for messages, should_insert in test_scenarios:
            mock_log.reset_mock()
            lang_graph_agent._current_classification = None
            messages_copy = messages.copy()

            # Call the method
            result = lang_graph_agent._prepare_messages_with_system_prompt(
                messages_copy,
                system_prompt="Default system prompt",
                classification=None
            )

            if should_insert:
                # Should have inserted system message
                assert len(result) == len(messages) + 1
                assert result[0].role == "system"
                assert result[0].content == "Default system prompt"

                # Verify STEP 47 logging
                step_47_logs = [
                    call for call in mock_log.call_args_list
                    if len(call[1]) > 3 and call[1].get('step') == 47
                ]
                assert len(step_47_logs) > 0

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_47_no_insert_when_system_exists(
        self,
        mock_log,
        lang_graph_agent,
        tax_classification
    ):
        """Test STEP 47: No insertion when system message already exists."""

        messages = [
            Message(role="system", content="Existing system message"),
            Message(role="user", content="User question")
        ]

        lang_graph_agent._current_classification = tax_classification
        original_count = len(messages)

        # Call the method
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages,
            system_prompt="Would-be inserted system prompt",
            classification=tax_classification
        )

        # Should NOT have inserted - should have replaced instead (STEP 46)
        assert len(result) == original_count  # No new message
        assert result[0].role == "system"
        # Content should be replaced, not the original
        assert result[0].content == "Would-be inserted system prompt"

        # Verify NO STEP 47 logging (should be STEP 46 replace instead)
        step_47_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 47
        ]
        assert len(step_47_logs) == 0, "STEP 47 should not be logged when system message exists"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_47_comprehensive_logging_format(
        self,
        mock_log,
        lang_graph_agent,
        single_user_message,
        tax_classification
    ):
        """Test STEP 47: Comprehensive structured logging format."""

        lang_graph_agent._current_classification = tax_classification

        # Call the method
        lang_graph_agent._prepare_messages_with_system_prompt(
            single_user_message,
            system_prompt="Comprehensive test system prompt",
            classification=tax_classification
        )

        # Find the insert action log
        step_47_logs = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and
                call[1].get('step') == 47 and
                call[1].get('action_taken') == 'insert')
        ]

        assert len(step_47_logs) > 0
        log_call = step_47_logs[0]

        # Verify all required STEP 47 logging fields
        required_fields = [
            'step', 'step_id', 'node_label', 'decision', 'action_taken',
            'system_message_exists', 'has_classification', 'messages_count',
            'original_messages_count', 'insert_position'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field in STEP 47 log: {field}"

        # Verify specific values for insert action
        assert log_call[1]['step'] == 47
        assert log_call[1]['step_id'] == "RAG.prompting.insert.system.message"
        assert log_call[1]['node_label'] == "InsertMsg"
        assert log_call[1]['decision'] == "system_message_inserted"
        assert log_call[1]['action_taken'] == "insert"
        assert log_call[1]['system_message_exists'] is False
        assert log_call[1]['has_classification'] is True
        assert log_call[1]['messages_count'] == 2  # 1 original + 1 inserted
        assert log_call[1]['original_messages_count'] == 1
        assert log_call[1]['insert_position'] == 0
        assert log_call[1]['classification_confidence'] == 0.85
        assert log_call[1]['domain'] == Domain.TAX.value
        assert log_call[1]['action'] == Action.INFORMATION_REQUEST.value
        assert log_call[1]['processing_stage'] == "completed"

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    @patch('app.core.langgraph.graph.rag_step_timer')
    async def test_step_47_performance_tracking_during_insert(
        self,
        mock_timer,
        mock_log,
        lang_graph_agent,
        messages_without_system,
        tax_classification
    ):
        """Test STEP 47: Performance tracking during system message insertion."""

        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        lang_graph_agent._current_classification = tax_classification

        # Call the method
        lang_graph_agent._prepare_messages_with_system_prompt(
            messages_without_system,
            system_prompt="Performance test prompt",
            classification=tax_classification
        )

        # Verify timer was used for STEP 45 (which coordinates insert logic)
        mock_timer.assert_called_with(
            45,
            "RAG.prompting.system.message.exists",
            "CheckSysMsg"
        )

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_47_insert_multiple_domain_scenarios(
        self,
        mock_log,
        lang_graph_agent
    ):
        """Test STEP 47: Insert behavior across multiple domain scenarios."""

        scenarios = [
            # (domain, action, confidence, expected_domain_value, expected_action_value)
            (Domain.TAX, Action.INFORMATION_REQUEST, 0.9, "tax", "information_request"),
            (Domain.LABOR, Action.CALCULATION_REQUEST, 0.8, "labor", "calculation_request"),
            (Domain.LEGAL, Action.DOCUMENT_ANALYSIS, 0.7, "legal", "document_analysis"),
        ]

        for domain, action, confidence, expected_domain, expected_action in scenarios:
            mock_log.reset_mock()

            messages = [Message(role="user", content=f"Query about {domain.value}")]

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

            # Verify insertion occurred
            assert len(messages) == 2  # 1 original + 1 inserted
            assert messages[0].content == f"{domain.value.title()} domain-specific prompt"

            # Verify STEP 47 logging
            step_47_logs = [
                call for call in mock_log.call_args_list
                if (len(call[1]) > 3 and
                    call[1].get('step') == 47 and
                    call[1].get('action_taken') == 'insert')
            ]

            assert len(step_47_logs) > 0, f"No STEP 47 insert log for {domain.value}"
            log_call = step_47_logs[0]
            assert log_call[1]['domain'] == expected_domain
            assert log_call[1]['action'] == expected_action
            assert log_call[1]['classification_confidence'] == confidence

    @pytest.mark.asyncio
    @patch('app.core.langgraph.graph.rag_step_log')
    async def test_step_47_insert_with_low_confidence_classification(
        self,
        mock_log,
        lang_graph_agent,
        messages_without_system
    ):
        """Test STEP 47: Insertion occurs even with low confidence classification."""

        # Low confidence classification
        low_conf_classification = DomainActionClassification(
            domain=Domain.BUSINESS,
            action=Action.STRATEGIC_ADVICE,
            confidence=0.2,  # Very low confidence
            document_type=None,
            reasoning="Uncertain business classification"
        )

        lang_graph_agent._current_classification = low_conf_classification

        # Call the method
        result = lang_graph_agent._prepare_messages_with_system_prompt(
            messages_without_system,
            system_prompt="Low confidence business prompt",
            classification=low_conf_classification
        )

        # Should still insert (classification presence matters, not confidence)
        assert len(result) == 3  # 2 original + 1 inserted
        assert result[0].content == "Low confidence business prompt"

        # Verify STEP 47 logging shows insertion with low confidence
        step_47_logs = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and
                call[1].get('step') == 47 and
                call[1].get('action_taken') == 'insert')
        ]

        assert len(step_47_logs) > 0
        log_call = step_47_logs[0]
        assert log_call[1]['classification_confidence'] == 0.2
        assert log_call[1]['domain'] == Domain.BUSINESS.value