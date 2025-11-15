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
from app.services.domain_action_classifier import Action, Domain, DomainActionClassification


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
            Message(
                role="assistant", content="I can help you with tax deductions. What specific questions do you have?"
            ),
            Message(role="user", content="What business expenses can I deduct?"),
        ]

    @pytest.fixture
    def high_confidence_classification(self):
        """High confidence domain-action classification."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.85,  # Above threshold
            document_type=None,
            reasoning="Clear tax consultation query with high confidence",
        )

    @pytest.fixture
    def low_confidence_classification(self):
        """Low confidence domain-action classification."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.45,  # Below threshold
            document_type=None,
            reasoning="Uncertain classification due to ambiguous query",
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.6)
    async def test_system_prompt_high_confidence_classification(
        self, mock_log, lang_graph_agent, sample_messages, high_confidence_classification, mock_prompt_template_manager
    ):
        """Test system prompt selection with high confidence classification."""

        result = await lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)

        # Should use domain-specific prompt
        assert result == "Domain-specific system prompt for tax consultation."

        # Verify PromptTemplateManager was called correctly
        mock_prompt_template_manager.get_prompt.assert_called_once_with(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            query="What business expenses can I deduct?",  # Latest user message
            context=None,
            document_type=None,
        )

        # Verify structured logging was called
        mock_log.assert_called()

        # Find the completed prompt selection log call
        selection_log_calls = [
            call
            for call in mock_log.call_args_list
            if call[1].get("step") == 41 and call[1].get("processing_stage") == "completed"
        ]

        assert len(selection_log_calls) > 0
        log_call = selection_log_calls[0]
        assert log_call[1]["step"] == 41
        assert log_call[1]["step_id"] == "RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt"
        assert log_call[1]["node_label"] == "SelectPrompt"
        assert log_call[1]["classification_confidence"] == 0.85
        assert log_call[1]["prompt_type"] == "domain_specific"

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.6)
    async def test_system_prompt_low_confidence_classification(
        self, mock_log, lang_graph_agent, sample_messages, low_confidence_classification
    ):
        """Test system prompt selection with low confidence classification."""

        result = await lang_graph_agent._get_system_prompt(sample_messages, low_confidence_classification)

        # Should use default prompt due to low confidence
        assert result == SYSTEM_PROMPT or result.startswith("You are PraticoAI")

        # Verify structured logging was called
        mock_log.assert_called()

        # Find the prompt selection log call
        selection_log_calls = [
            call
            for call in mock_log.call_args_list
            if call[1].get("step") == 41 and call[1].get("processing_stage") == "completed"
        ]

        assert len(selection_log_calls) > 0
        log_call = selection_log_calls[0]
        assert log_call[1]["step"] == 41
        assert log_call[1]["classification_confidence"] == 0.45
        assert log_call[1]["prompt_type"] == "default"
        assert log_call[1]["confidence_below_threshold"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_system_prompt_no_classification(self, mock_log, lang_graph_agent, sample_messages):
        """Test system prompt selection with no classification available."""

        result = await lang_graph_agent._get_system_prompt(sample_messages, None)

        # Should use default prompt when no classification
        assert result == SYSTEM_PROMPT or result.startswith("You are PraticoAI")

        # Verify structured logging was called
        mock_log.assert_called()

        selection_log_calls = [
            call
            for call in mock_log.call_args_list
            if call[1].get("step") == 41 and call[1].get("processing_stage") == "completed"
        ]

        assert len(selection_log_calls) > 0
        log_call = selection_log_calls[0]
        assert log_call[1]["prompt_type"] == "default"
        assert log_call[1]["classification_available"] is False

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.6)
    async def test_system_prompt_empty_messages(self, mock_log, lang_graph_agent, high_confidence_classification):
        """Test system prompt selection with empty messages."""

        result = await lang_graph_agent._get_system_prompt([], high_confidence_classification)

        # Should still work with domain prompt but empty query
        assert result == "Domain-specific system prompt for tax consultation."

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.6)
    async def test_system_prompt_domain_prompt_error(
        self, mock_log, lang_graph_agent, sample_messages, high_confidence_classification, mock_prompt_template_manager
    ):
        """Test system prompt selection when domain prompt generation fails."""

        # Mock domain prompt generation to raise exception
        mock_prompt_template_manager.get_prompt.side_effect = Exception("Prompt generation failed")

        result = await lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)

        # Should fallback to default prompt on error
        assert result == SYSTEM_PROMPT or result.startswith("You are PraticoAI")

        # Verify error logging
        selection_log_calls = [
            call
            for call in mock_log.call_args_list
            if call[1].get("step") == 41 and call[1].get("processing_stage") == "completed"
        ]

        assert len(selection_log_calls) > 0
        log_call = selection_log_calls[0]
        assert log_call[1]["prompt_type"] == "default"
        assert log_call[1]["reason"] == "domain_prompt_error_fallback"

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.6)
    async def test_system_prompt_different_domains(self, mock_log, lang_graph_agent, sample_messages):
        """Test system prompt selection with different domain classifications."""

        # Test LABOR domain
        labor_classification = DomainActionClassification(
            domain=Domain.LABOR,
            action=Action.INFORMATION_REQUEST,
            confidence=0.75,
            document_type=None,
            keywords=["employment", "contract"],
            reasoning="Labor law consultation",
        )

        lang_graph_agent._prompt_template_manager.get_prompt.return_value = "Labor-specific system prompt."

        result = await lang_graph_agent._get_system_prompt(sample_messages, labor_classification)

        assert result == "Labor-specific system prompt."

        # Verify correct domain was passed
        lang_graph_agent._prompt_template_manager.get_prompt.assert_called_with(
            domain=Domain.LABOR,
            action=Action.INFORMATION_REQUEST,
            query="What business expenses can I deduct?",
            context=None,
            document_type=None,
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.core.config.settings.CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.6)
    async def test_system_prompt_messages_without_user_content(
        self, mock_log, lang_graph_agent, high_confidence_classification
    ):
        """Test system prompt selection when messages have no user content."""

        messages_no_user = [
            Message(role="assistant", content="Hello, how can I help?"),
            Message(role="system", content="System message"),
        ]

        result = await lang_graph_agent._get_system_prompt(messages_no_user, high_confidence_classification)

        # Should still use domain prompt with empty query
        assert result == "Domain-specific system prompt for tax consultation."

        # Verify empty query was passed
        lang_graph_agent._prompt_template_manager.get_prompt.assert_called_with(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            query="",  # Empty query when no user messages found
            context=None,
            document_type=None,
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    async def test_system_prompt_performance_tracking(
        self, mock_timer, mock_log, lang_graph_agent, sample_messages, high_confidence_classification
    ):
        """Test that system prompt selection includes performance tracking."""

        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        await lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)

        # Verify timer was used
        mock_timer.assert_called_with(
            41,
            "RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt",
            "SelectPrompt",
            classification_confidence=0.85,
            domain=Domain.TAX.value,
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_structured_logging_format_comprehensive(
        self, mock_log, lang_graph_agent, sample_messages, high_confidence_classification
    ):
        """Test comprehensive structured logging format for STEP 41."""

        await lang_graph_agent._get_system_prompt(sample_messages, high_confidence_classification)

        # Verify all required logging fields are present
        mock_log.assert_called()

        # Find completed STEP 41 log calls
        step_41_logs = [
            call
            for call in mock_log.call_args_list
            if call[1].get("step") == 41 and call[1].get("processing_stage") == "completed"
        ]

        assert len(step_41_logs) > 0

        # Check the completed log call has all required fields
        main_log = step_41_logs[0]
        required_fields = [
            "step",
            "step_id",
            "node_label",
            "classification_confidence",
            "prompt_type",
            "domain",
            "action",
            "user_query",
        ]

        for field in required_fields:
            assert field in main_log[1], f"Missing required field: {field}"

        assert main_log[1]["step"] == 41
        assert main_log[1]["step_id"] == "RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt"
        assert main_log[1]["node_label"] == "SelectPrompt"


class TestRAGStep41Orchestrator:
    """Test suite for RAG STEP 41 Orchestrator - SelectPrompt orchestration function."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_41_orchestrator_high_confidence_classification(self, mock_rag_log):
        """Test Step 41: Orchestrator with high confidence classification."""
        from unittest.mock import MagicMock

        from app.orchestrators.prompting import step_41__select_prompt
        from app.schemas.chat import Message
        from app.services.domain_action_classifier import Action, Domain, DomainActionClassification

        # Mock prompt template manager
        mock_prompt_manager = MagicMock()
        mock_prompt_manager.get_prompt.return_value = "Domain-specific tax consultation prompt."

        # High confidence classification
        classification = DomainActionClassification(
            domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.87, document_type=None
        )

        messages = [Message(role="user", content="What business expenses can I deduct?")]

        ctx = {
            "request_id": "test-orchestrator-41",
            "classification": classification,
            "prompt_template_manager": mock_prompt_manager,
        }

        result = await step_41__select_prompt(messages=messages, ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["prompt_selected"] is True
        assert result["selected_prompt"] == "Domain-specific tax consultation prompt."
        assert result["prompt_type"] == "domain_specific"
        assert result["selection_reason"] == "confidence_meets_threshold"
        assert result["classification_available"] is True
        assert result["classification_confidence"] == 0.87
        assert result["confidence_meets_threshold"] is True
        assert result["domain"] == "tax"
        assert result["action"] == "information_request"
        assert result["request_id"] == "test-orchestrator-41"
        assert "timestamp" in result

        # Verify prompt template manager was called correctly
        mock_prompt_manager.get_prompt.assert_called_once_with(
            domain=classification.domain,
            action=classification.action,
            query="What business expenses can I deduct?",
            context=None,
            document_type=classification.document_type,
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.step_44__default_sys_prompt")
    async def test_step_41_orchestrator_low_confidence_classification(self, mock_step_44, mock_rag_log):
        """Test Step 41: Orchestrator with low confidence classification."""
        from app.orchestrators.prompting import step_41__select_prompt
        from app.schemas.chat import Message
        from app.services.domain_action_classifier import Action, Domain, DomainActionClassification

        # Low confidence classification
        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.45,  # Below 0.6 threshold
            document_type=None,
        )

        mock_step_44.return_value = "Default system prompt used for low confidence."

        messages = [Message(role="user", content="General business question")]

        ctx = {"request_id": "test-low-confidence", "classification": classification, "prompt_template_manager": None}

        result = await step_41__select_prompt(messages=messages, ctx=ctx)

        # Verify the result structure
        assert result["prompt_selected"] is True
        assert result["selected_prompt"] == "Default system prompt used for low confidence."
        assert result["prompt_type"] == "default"
        assert result["selection_reason"] == "low_confidence"
        assert result["classification_available"] is True
        assert result["classification_confidence"] == 0.45
        assert result["confidence_meets_threshold"] is False

        # Verify Step 44 was called for default prompt
        mock_step_44.assert_called_once_with(
            messages=messages,
            ctx={
                "classification": classification,
                "user_query": "General business question",
                "trigger_reason": "low_confidence",
            },
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.step_44__default_sys_prompt")
    async def test_step_41_orchestrator_no_classification(self, mock_step_44, mock_rag_log):
        """Test Step 41: Orchestrator with no classification available."""
        from app.orchestrators.prompting import step_41__select_prompt
        from app.schemas.chat import Message

        mock_step_44.return_value = "Default system prompt for no classification."

        messages = [Message(role="user", content="Help me with something")]

        ctx = {
            "request_id": "test-no-classification",
            "classification": None,  # No classification
            "prompt_template_manager": None,
        }

        result = await step_41__select_prompt(messages=messages, ctx=ctx)

        # Verify the result structure
        assert result["prompt_selected"] is True
        assert result["selected_prompt"] == "Default system prompt for no classification."
        assert result["prompt_type"] == "default"
        assert result["selection_reason"] == "no_classification_available"
        assert result["classification_available"] is False
        assert result["classification_confidence"] is None
        assert result["confidence_meets_threshold"] is False

        # Verify Step 44 was called for default prompt
        mock_step_44.assert_called_once_with(
            messages=messages,
            ctx={
                "classification": None,
                "user_query": "Help me with something",
                "trigger_reason": "no_classification",
            },
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_41_orchestrator_domain_prompt_error(self, mock_logger, mock_rag_log):
        """Test Step 41: Domain prompt error fallback."""
        from unittest.mock import MagicMock

        from app.orchestrators.prompting import step_41__select_prompt
        from app.schemas.chat import Message
        from app.services.domain_action_classifier import Action, Domain, DomainActionClassification

        # Mock prompt template manager that raises an exception
        mock_prompt_manager = MagicMock()
        mock_prompt_manager.get_prompt.side_effect = Exception("Domain prompt service unavailable")

        # High confidence classification
        classification = DomainActionClassification(
            domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.87, document_type=None
        )

        messages = [Message(role="user", content="Tax question")]

        ctx = {
            "request_id": "test-error-fallback",
            "classification": classification,
            "prompt_template_manager": mock_prompt_manager,
        }

        result = await step_41__select_prompt(messages=messages, ctx=ctx)

        # Verify fallback to default prompt
        assert result["prompt_selected"] is True
        assert result["prompt_type"] == "default"
        assert result["selection_reason"] == "domain_prompt_error_fallback"
        assert result["error"] is not None
        assert "Domain prompt service unavailable" in result["error"]

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_41_orchestrator_integration_flow(self, mock_rag_log):
        """Test Step 41: Integration test ensuring proper workflow integration."""
        from unittest.mock import MagicMock

        from app.orchestrators.prompting import step_41__select_prompt
        from app.schemas.chat import Message
        from app.services.domain_action_classifier import Action, Domain, DomainActionClassification

        # Mock context from previous steps (Step 40: BuildContext)
        mock_prompt_manager = MagicMock()
        mock_prompt_manager.get_prompt.return_value = "Integrated domain prompt for workflow testing."

        classification = DomainActionClassification(
            domain=Domain.LEGAL, action=Action.STRATEGIC_ADVICE, confidence=0.82, document_type=None
        )

        messages = [Message(role="user", content="Legal consultation request from integration test")]

        ctx = {
            "request_id": "test-integration-41",
            "classification": classification,
            "prompt_template_manager": mock_prompt_manager,
            # Context from previous steps
            "merged_context": "Merged context from Step 40",
            "context_quality_score": 0.87,
            "token_count": 1200,
        }

        result = await step_41__select_prompt(messages=messages, ctx=ctx)

        # Verify proper integration
        assert result["prompt_selected"] is True
        assert result["selected_prompt"] == "Integrated domain prompt for workflow testing."
        assert result["prompt_type"] == "domain_specific"
        assert result["request_id"] == "test-integration-41"

        # Verify rag_step_log was called with proper parameters
        assert mock_rag_log.call_count >= 2  # start and completed calls
        start_call = None
        completed_call = None

        for call in mock_rag_log.call_args_list:
            if call[1].get("processing_stage") == "started":
                start_call = call[1]
            elif call[1].get("processing_stage") == "completed":
                completed_call = call[1]

        assert start_call is not None
        assert start_call["step"] == 41
        assert start_call["node_label"] == "SelectPrompt"
        assert completed_call is not None
        assert completed_call["prompt_type"] == "domain_specific"

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    async def test_step_41_parity_behavior_preservation(self, mock_rag_log):
        """Test Step 41: Parity test proving identical behavior before/after orchestrator."""
        from unittest.mock import MagicMock

        from app.core.langgraph.graph import LangGraphAgent
        from app.orchestrators.prompting import step_41__select_prompt
        from app.schemas.chat import Message
        from app.services.domain_action_classifier import Action, Domain, DomainActionClassification

        # Setup identical test data for both approaches
        mock_prompt_manager = MagicMock()
        mock_prompt_manager.get_prompt.return_value = "Parity test domain prompt."

        classification = DomainActionClassification(
            domain=Domain.BUSINESS, action=Action.INFORMATION_REQUEST, confidence=0.75, document_type=None
        )

        messages = [Message(role="user", content="Business consultation parity test")]

        # Test via orchestrator (new approach)
        ctx = {
            "request_id": "parity-test-41",
            "classification": classification,
            "prompt_template_manager": mock_prompt_manager,
        }

        orchestrator_result = await step_41__select_prompt(messages=messages, ctx=ctx)

        # Test via LangGraphAgent (original approach - should now call orchestrator)
        agent = LangGraphAgent()
        agent._prompt_template_manager = mock_prompt_manager
        direct_result = await agent._get_system_prompt(messages, classification)

        # Verify that both approaches return the same prompt
        assert orchestrator_result["prompt_selected"] is True
        assert orchestrator_result["selected_prompt"] == direct_result
        assert orchestrator_result["selected_prompt"] == "Parity test domain prompt."
        assert orchestrator_result["prompt_type"] == "domain_specific"
        assert orchestrator_result["selection_reason"] == "confidence_meets_threshold"

        # Verify orchestrator adds coordination metadata without changing core behavior
        assert orchestrator_result["request_id"] == "parity-test-41"
        assert "timestamp" in orchestrator_result
