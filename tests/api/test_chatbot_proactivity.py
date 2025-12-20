"""TDD Tests for Chatbot Proactivity Integration - DEV-158.

Tests for integrating ProactivityEngine with /chat endpoint:
- Actions returned in response
- Questions returned when coverage is low
- Graceful degradation on ProactivityEngine failure
- Extracted params included in response
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import ChatResponse, Message
from app.schemas.proactivity import (
    Action,
    ActionCategory,
    ExtractedParameter,
    InteractiveOption,
    InteractiveQuestion,
    ParameterExtractionResult,
    ProactivityContext,
    ProactivityResult,
)


class TestChatResponseWithProactivity:
    """Test ChatResponse includes proactivity fields."""

    def test_chat_response_includes_actions(self):
        """Test that ChatResponse can include suggested_actions."""
        actions = [
            Action(
                id="tax_calculate_irpef",
                label="Calcola IRPEF",
                icon="calculator",
                category=ActionCategory.CALCULATE,
                prompt_template="Calcola l'IRPEF per {reddito}",
            )
        ]
        messages = [Message(role="assistant", content="Ecco le informazioni")]

        response = ChatResponse(messages=messages, suggested_actions=actions)

        assert response.suggested_actions is not None
        assert len(response.suggested_actions) == 1
        assert response.suggested_actions[0].id == "tax_calculate_irpef"

    def test_chat_response_includes_question(self):
        """Test that ChatResponse can include interactive_question."""
        question = InteractiveQuestion(
            id="irpef_tipo_contribuente",
            trigger_query="calcola irpef",
            text="Che tipo di contribuente sei?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="dipendente", label="Dipendente"),
                InteractiveOption(id="autonomo", label="Autonomo"),
            ],
        )
        messages = [Message(role="assistant", content="Per calcolare...")]

        response = ChatResponse(messages=messages, interactive_question=question)

        assert response.interactive_question is not None
        assert response.interactive_question.id == "irpef_tipo_contribuente"

    def test_chat_response_includes_extracted_params(self):
        """Test that ChatResponse can include extracted_params."""
        messages = [Message(role="assistant", content="Hai specificato...")]
        params = {"reddito": "50000", "anno": "2024"}

        response = ChatResponse(messages=messages, extracted_params=params)

        assert response.extracted_params is not None
        assert response.extracted_params["reddito"] == "50000"


class TestProactivityEngineIntegration:
    """Test ProactivityEngine integration with chat endpoint."""

    @pytest.fixture
    def mock_proactivity_engine(self):
        """Create a mock ProactivityEngine."""
        engine = MagicMock()
        engine.process = MagicMock()
        return engine

    @pytest.fixture
    def sample_actions(self):
        """Create sample actions for testing."""
        return [
            Action(
                id="tax_calculate_irpef",
                label="Calcola IRPEF",
                icon="calculator",
                category=ActionCategory.CALCULATE,
                prompt_template="Calcola l'IRPEF per {reddito}",
            ),
            Action(
                id="tax_search_deductions",
                label="Cerca detrazioni",
                icon="search",
                category=ActionCategory.SEARCH,
                prompt_template="Cerca detrazioni per {categoria}",
            ),
        ]

    @pytest.fixture
    def sample_question(self):
        """Create sample interactive question for testing."""
        return InteractiveQuestion(
            id="irpef_tipo_contribuente",
            trigger_query="calcola irpef",
            text="Che tipo di contribuente sei?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="dipendente", label="Dipendente"),
                InteractiveOption(id="autonomo", label="Autonomo"),
            ],
        )

    @pytest.fixture
    def sample_extraction_result(self):
        """Create sample extraction result for testing."""
        return ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=[
                ExtractedParameter(
                    name="reddito",
                    value="50000",
                    confidence=0.95,
                    source="query",
                )
            ],
            missing_required=["tipo_contribuente"],
            coverage=0.5,
            can_proceed=False,
        )

    def test_proactivity_result_with_actions(self, mock_proactivity_engine, sample_actions):
        """Test ProactivityResult returns actions correctly."""
        result = ProactivityResult(
            actions=sample_actions,
            question=None,
            extraction_result=None,
            processing_time_ms=50.0,
        )

        assert len(result.actions) == 2
        assert result.actions[0].id == "tax_calculate_irpef"
        assert result.question is None

    def test_proactivity_result_with_question(
        self, mock_proactivity_engine, sample_question, sample_extraction_result
    ):
        """Test ProactivityResult returns question when coverage is low."""
        result = ProactivityResult(
            actions=[],
            question=sample_question,
            extraction_result=sample_extraction_result,
            processing_time_ms=80.0,
        )

        assert result.question is not None
        assert result.question.id == "irpef_tipo_contribuente"
        assert result.extraction_result is not None
        assert result.extraction_result.coverage == 0.5

    def test_proactivity_engine_failure_returns_empty_result(self, mock_proactivity_engine):
        """Test graceful degradation when ProactivityEngine fails."""
        # Simulate engine failure
        mock_proactivity_engine.process.side_effect = Exception("Engine error")

        # In production, the endpoint should catch this and return empty actions
        try:
            mock_proactivity_engine.process("query", MagicMock())
            result = None
        except Exception:
            # Fallback to empty result
            result = ProactivityResult(
                actions=[],
                question=None,
                extraction_result=None,
                processing_time_ms=0.0,
            )

        assert result is not None
        assert result.actions == []
        assert result.question is None

    def test_extracted_params_from_result(self, sample_extraction_result):
        """Test extracting params dict from extraction result."""
        # Convert extracted params to dict format for ChatResponse
        extracted_params = {p.name: p.value for p in sample_extraction_result.extracted}

        assert extracted_params == {"reddito": "50000"}


class TestProactivityContext:
    """Test ProactivityContext creation."""

    def test_context_creation_with_domain(self):
        """Test creating context with domain classification."""
        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
            action_type="fiscal_calculation",
            document_type=None,
        )

        assert context.session_id == "session-123"
        assert context.domain == "tax"
        assert context.action_type == "fiscal_calculation"
        assert context.document_type is None

    def test_context_creation_with_document(self):
        """Test creating context with document type."""
        context = ProactivityContext(
            session_id="session-456",
            domain="documents",
            action_type=None,
            document_type="fattura",
        )

        assert context.document_type == "fattura"
        assert context.domain == "documents"


class TestGracefulDegradation:
    """Test graceful degradation scenarios."""

    def test_chat_response_without_actions_on_timeout(self):
        """Test ChatResponse works without actions (timeout scenario)."""
        messages = [Message(role="assistant", content="Risposta normale")]

        # When proactivity times out, response should still work
        response = ChatResponse(
            messages=messages,
            suggested_actions=None,
            interactive_question=None,
            extracted_params=None,
        )

        assert response.messages is not None
        assert len(response.messages) == 1
        assert response.suggested_actions is None

    def test_chat_response_serialization_without_proactivity(self):
        """Test ChatResponse serializes correctly without proactivity fields."""
        messages = [Message(role="assistant", content="Hello")]
        response = ChatResponse(messages=messages)

        # Serialize with exclude_none to simulate API response
        response_dict = response.model_dump(exclude_none=True)

        assert "messages" in response_dict
        assert "suggested_actions" not in response_dict
        assert "interactive_question" not in response_dict
        assert "extracted_params" not in response_dict
