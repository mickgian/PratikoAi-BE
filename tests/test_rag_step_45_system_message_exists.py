"""
Tests for RAG STEP 45 — System message exists?

This step checks whether a system message already exists in the conversation
and decides whether to insert a new one or replace the existing one.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message
from app.services.domain_action_classifier import Action, Domain, DomainActionClassification


class TestRAGStep45SystemMessageExists:
    """Test suite for RAG STEP 45 - System message exists?"""

    @pytest.fixture
    def lang_graph_agent(self):
        """Create LangGraphAgent instance for testing."""
        agent = LangGraphAgent()
        # Mock dependencies
        agent._prompt_template_manager = MagicMock()
        agent._prompt_template_manager.get_prompt.return_value = "Domain-specific system prompt."
        return agent

    @pytest.fixture
    def messages_with_system(self):
        """Messages list that already contains a system message."""
        return [
            Message(role="system", content="Existing system prompt."),
            Message(role="user", content="What is tax deduction?"),
            Message(role="assistant", content="A tax deduction reduces taxable income."),
        ]

    @pytest.fixture
    def messages_without_system(self):
        """Messages list without a system message."""
        return [
            Message(role="user", content="What is tax deduction?"),
            Message(role="assistant", content="A tax deduction reduces taxable income."),
        ]

    @pytest.fixture
    def empty_messages(self):
        """Empty messages list."""
        return []

    @pytest.fixture
    def high_confidence_classification(self):
        """High confidence classification for domain-specific prompt."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.8,
            document_type=None,
            reasoning="High confidence tax query",
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_45_system_message_exists_replace(self, mock_log, lang_graph_agent, messages_with_system):
        """Test STEP 45: System message exists -> replace it."""

        # Set up agent with classification for domain-specific prompt
        lang_graph_agent._current_classification = DomainActionClassification(
            domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.8, reasoning="Tax query"
        )

        # Call the method that performs the check
        lang_graph_agent._prepare_messages_with_system_prompt(messages_with_system)

        # Verify STEP 45 logging was called (look for completed stage logs)
        step_45_logs = [
            call
            for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get("step") == 45 and call[1].get("processing_stage") == "completed"
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]["step"] == 45
        assert log_call[1]["step_id"] == "RAG.prompting.system.message.exists"
        assert log_call[1]["node_label"] == "CheckSysMsg"
        assert log_call[1]["decision"] == "system_message_exists"
        assert log_call[1]["system_message_exists"] is True
        assert log_call[1]["action_taken"] == "replace"
        assert log_call[1]["has_classification"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_45_system_message_not_exists_insert(self, mock_log, lang_graph_agent, messages_without_system):
        """Test STEP 45: System message doesn't exist -> insert it."""

        # No classification, will use default prompt
        lang_graph_agent._current_classification = None

        # Call the method that performs the check
        lang_graph_agent._prepare_messages_with_system_prompt(messages_without_system)

        # Verify STEP 45 logging was called (look for completed stage logs)
        step_45_logs = [
            call
            for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get("step") == 45 and call[1].get("processing_stage") == "completed"
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]["step"] == 45
        assert log_call[1]["step_id"] == "RAG.prompting.system.message.exists"
        assert log_call[1]["node_label"] == "CheckSysMsg"
        assert log_call[1]["decision"] == "system_message_not_exists"
        assert log_call[1]["system_message_exists"] is False
        assert log_call[1]["action_taken"] == "insert"
        assert log_call[1]["has_classification"] is False

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_45_empty_messages_insert(self, mock_log, lang_graph_agent, empty_messages):
        """Test STEP 45: Empty messages list -> insert system message."""

        lang_graph_agent._current_classification = None

        # Call the method that performs the check
        lang_graph_agent._prepare_messages_with_system_prompt(empty_messages)

        # Should have inserted a system message
        assert len(empty_messages) == 1
        assert empty_messages[0].role == "system"

        # Verify STEP 45 logging
        step_45_logs = [
            call
            for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get("step") == 45 and call[1].get("processing_stage") == "completed"
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]["system_message_exists"] is False
        assert log_call[1]["action_taken"] == "insert"
        assert log_call[1]["messages_empty"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_45_system_message_exists_no_classification_keep(
        self, mock_log, lang_graph_agent, messages_with_system
    ):
        """Test STEP 45: System message exists, no classification -> keep existing."""

        # No classification
        lang_graph_agent._current_classification = None
        original_system_content = messages_with_system[0].content

        # Call the method that performs the check
        lang_graph_agent._prepare_messages_with_system_prompt(messages_with_system)

        # Should have kept the existing system message (no replacement)
        assert messages_with_system[0].role == "system"
        assert messages_with_system[0].content == original_system_content

        # Verify STEP 45 logging
        step_45_logs = [
            call
            for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get("step") == 45 and call[1].get("processing_stage") == "completed"
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]["system_message_exists"] is True
        assert log_call[1]["action_taken"] == "keep"  # Keep existing when no classification
        assert log_call[1]["has_classification"] is False

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_45_system_message_exists_with_classification_replace(
        self, mock_log, lang_graph_agent, messages_with_system, high_confidence_classification
    ):
        """Test STEP 45: System message exists, with classification -> replace with domain-specific."""

        # Set classification for domain-specific prompt
        lang_graph_agent._current_classification = high_confidence_classification

        # Call the method that performs the check
        lang_graph_agent._prepare_messages_with_system_prompt(messages_with_system)

        # Should have replaced with domain-specific prompt
        assert messages_with_system[0].role == "system"
        # The content would be updated with domain-specific prompt from _get_system_prompt

        # Verify STEP 45 logging
        step_45_logs = [
            call
            for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get("step") == 45 and call[1].get("processing_stage") == "completed"
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]["system_message_exists"] is True
        assert log_call[1]["action_taken"] == "replace"
        assert log_call[1]["has_classification"] is True
        assert log_call[1]["classification_confidence"] == 0.8
        assert log_call[1]["domain"] == Domain.TAX.value

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_45_first_message_not_system_insert(self, mock_log, lang_graph_agent):
        """Test STEP 45: First message is not system -> insert system message at beginning."""

        messages = [
            Message(role="user", content="I have a question"),
            Message(role="user", content="Actually two questions"),
        ]

        lang_graph_agent._current_classification = None

        # Call the method that performs the check
        lang_graph_agent._prepare_messages_with_system_prompt(messages)

        # Should have inserted system message at the beginning
        assert len(messages) == 3
        assert messages[0].role == "system"
        assert messages[1].role == "user"

        # Verify STEP 45 logging
        step_45_logs = [
            call
            for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get("step") == 45 and call[1].get("processing_stage") == "completed"
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]["system_message_exists"] is False
        assert log_call[1]["action_taken"] == "insert"
        assert log_call[1]["insert_position"] == 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    async def test_step_45_performance_tracking(self, mock_timer, mock_log, lang_graph_agent, messages_without_system):
        """Test STEP 45: Performance tracking with timer."""

        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        lang_graph_agent._current_classification = None

        # Call the method that performs the check
        lang_graph_agent._prepare_messages_with_system_prompt(messages_without_system)

        # Verify Step 45 timer was used (check if called with Step 45 parameters)
        step_45_timer_calls = [call for call in mock_timer.call_args_list if len(call[0]) >= 3 and call[0][0] == 45]
        assert len(step_45_timer_calls) > 0, "Step 45 timer should be called"

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_45_comprehensive_logging_format(
        self, mock_log, lang_graph_agent, messages_with_system, high_confidence_classification
    ):
        """Test STEP 45: Comprehensive structured logging format."""

        lang_graph_agent._current_classification = high_confidence_classification

        # Call the method that performs the check
        lang_graph_agent._prepare_messages_with_system_prompt(messages_with_system)

        # Verify all required STEP 45 logging fields
        step_45_logs = [
            call
            for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get("step") == 45 and call[1].get("processing_stage") == "completed"
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]

        # Verify all required fields for STEP 45
        required_fields = [
            "step",
            "step_id",
            "node_label",
            "decision",
            "system_message_exists",
            "action_taken",
            "has_classification",
            "messages_count",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 45
        assert log_call[1]["step_id"] == "RAG.prompting.system.message.exists"
        assert log_call[1]["node_label"] == "CheckSysMsg"
        assert log_call[1]["messages_count"] == 3  # System + user + assistant

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_45_different_scenarios(self, mock_log, lang_graph_agent):
        """Test STEP 45: Different scenarios for system message checking."""

        test_scenarios = [
            # Scenario 1: Empty messages
            ([], False, "insert"),
            # Scenario 2: Only user message
            ([Message(role="user", content="Question")], False, "insert"),
            # Scenario 3: System message exists
            ([Message(role="system", content="System"), Message(role="user", content="Question")], True, "keep"),
            # Scenario 4: Assistant message first (unusual but possible)
            ([Message(role="assistant", content="Answer"), Message(role="user", content="Question")], False, "insert"),
        ]

        for messages, should_exist, expected_action in test_scenarios:
            mock_log.reset_mock()
            lang_graph_agent._current_classification = None

            # Call the method
            lang_graph_agent._prepare_messages_with_system_prompt(messages.copy())

            # Verify STEP 45 logging
            step_45_logs = [
                call
                for call in mock_log.call_args_list
                if len(call[1]) > 3 and call[1].get("step") == 45 and call[1].get("processing_stage") == "completed"
            ]

            assert len(step_45_logs) > 0, f"No STEP 45 logging for scenario {expected_action}"
            log_call = step_45_logs[0]
            assert log_call[1]["system_message_exists"] == should_exist
            assert log_call[1]["action_taken"] == expected_action

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_45_various_message_types(self, mock_log, lang_graph_agent):
        """Test STEP 45: Handling various message role types."""

        # Messages with mixed roles
        messages = [
            Message(role="user", content="User question"),
            Message(role="assistant", content="Assistant response"),
            Message(role="user", content="Follow-up"),
            Message(role="assistant", content="Another response"),
        ]

        lang_graph_agent._current_classification = None

        # Call the method
        lang_graph_agent._prepare_messages_with_system_prompt(messages)

        # Should have inserted system message at the beginning
        assert messages[0].role == "system"
        assert messages[1].role == "user"  # Original first message
        assert len(messages) == 5  # 1 system + 4 original

        # Verify STEP 45 logging
        step_45_logs = [
            call
            for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get("step") == 45 and call[1].get("processing_stage") == "completed"
        ]

        assert len(step_45_logs) > 0
        log_call = step_45_logs[0]
        assert log_call[1]["system_message_exists"] is False
        assert log_call[1]["action_taken"] == "insert"
        assert log_call[1]["original_messages_count"] == 4
        assert log_call[1]["messages_count"] == 4  # Step 45 logs before Step 47 insertion
