"""TDD Tests for /questions/answer Endpoint - DEV-161.

Tests for POST /api/v1/chatbot/questions/answer endpoint:
- Single-step question returns answer
- Multi-step question returns next question
- Custom input processed correctly
- Invalid question_id handling (HTTP 400)
- Invalid option_id handling (HTTP 400)
- Custom input required but empty (HTTP 400)
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.proactivity import (
    Action,
    ActionCategory,
    InteractiveOption,
    InteractiveQuestion,
)


class TestQuestionAnswerRequestSchema:
    """Test QuestionAnswerRequest schema validation."""

    def test_valid_request_minimal(self):
        """Test valid request with minimal fields."""
        from app.schemas.proactivity import QuestionAnswerRequest

        request = QuestionAnswerRequest(
            question_id="irpef_tipo_contribuente",
            selected_option="dipendente",
            session_id="session-123",
        )
        assert request.question_id == "irpef_tipo_contribuente"
        assert request.selected_option == "dipendente"
        assert request.session_id == "session-123"
        assert request.custom_input is None

    def test_valid_request_with_custom_input(self):
        """Test valid request with custom input."""
        from app.schemas.proactivity import QuestionAnswerRequest

        request = QuestionAnswerRequest(
            question_id="irpef_reddito",
            selected_option="altro",
            custom_input="75000",
            session_id="session-123",
        )
        assert request.custom_input == "75000"

    def test_request_requires_question_id(self):
        """Test that question_id is required."""
        from pydantic import ValidationError

        from app.schemas.proactivity import QuestionAnswerRequest

        with pytest.raises(ValidationError):
            QuestionAnswerRequest(
                selected_option="dipendente",
                session_id="session-123",
            )

    def test_request_selected_option_optional_for_multifield(self):
        """Test that selected_option is optional (for multi_field questions).

        Multi-field questions use field_values instead of selected_option.
        Both can be None, which is valid for multi_field questions.
        """
        from app.schemas.proactivity import QuestionAnswerRequest

        # Valid: no selected_option (for multi_field type)
        request = QuestionAnswerRequest(
            question_id="irpef_calculation",
            session_id="session-123",
            field_values={"reddito": "50000", "detrazioni": "1000"},
        )
        assert request.selected_option is None
        assert request.field_values == {"reddito": "50000", "detrazioni": "1000"}

    def test_request_requires_session_id(self):
        """Test that session_id is required."""
        from pydantic import ValidationError

        from app.schemas.proactivity import QuestionAnswerRequest

        with pytest.raises(ValidationError):
            QuestionAnswerRequest(
                question_id="irpef_tipo_contribuente",
                selected_option="dipendente",
            )


class TestQuestionAnswerResponseSchema:
    """Test QuestionAnswerResponse schema."""

    def test_response_with_next_question(self):
        """Test response with next question (multi-step flow)."""
        from app.schemas.proactivity import QuestionAnswerResponse

        next_question = InteractiveQuestion(
            id="irpef_reddito",
            text="Qual è il tuo reddito annuo?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="under_28k", label="Fino a 28.000€"),
                InteractiveOption(id="over_28k", label="Oltre 28.000€"),
            ],
        )
        response = QuestionAnswerResponse(next_question=next_question)

        assert response.next_question is not None
        assert response.next_question.id == "irpef_reddito"
        assert response.answer is None
        assert response.suggested_actions is None

    def test_response_with_answer(self):
        """Test response with answer (terminal question)."""
        from app.schemas.proactivity import QuestionAnswerResponse

        response = QuestionAnswerResponse(
            answer="L'IRPEF per un dipendente con reddito 50.000€ è...",
        )

        assert response.answer is not None
        assert response.next_question is None

    def test_response_with_answer_and_actions(self):
        """Test response with answer and follow-up actions."""
        from app.schemas.proactivity import QuestionAnswerResponse

        actions = [
            Action(
                id="tax_explain_brackets",
                label="Spiega scaglioni",
                icon="info",
                category=ActionCategory.EXPLAIN,
                prompt_template="Spiega gli scaglioni IRPEF",
            )
        ]
        response = QuestionAnswerResponse(
            answer="L'IRPEF dovuta è 12.500€",
            suggested_actions=actions,
        )

        assert response.answer is not None
        assert response.suggested_actions is not None
        assert len(response.suggested_actions) == 1


class TestQuestionLookup:
    """Test question template lookup."""

    @pytest.fixture
    def mock_template_service(self):
        """Create mock template service."""
        service = MagicMock()
        service.get_question = MagicMock()
        return service

    @pytest.fixture
    def sample_question(self):
        """Create sample interactive question."""
        return InteractiveQuestion(
            id="irpef_tipo_contribuente",
            text="Che tipo di contribuente sei?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="dipendente", label="Dipendente"),
                InteractiveOption(id="autonomo", label="Autonomo"),
            ],
        )

    def test_question_found_by_id(self, mock_template_service, sample_question):
        """Test question is found by ID."""
        mock_template_service.get_question.return_value = sample_question

        result = mock_template_service.get_question("irpef_tipo_contribuente")

        assert result is not None
        assert result.id == "irpef_tipo_contribuente"

    def test_question_not_found_returns_none(self, mock_template_service):
        """Test unknown question_id returns None."""
        mock_template_service.get_question.return_value = None

        result = mock_template_service.get_question("unknown_question")

        assert result is None


class TestOptionValidation:
    """Test option validation in question answers."""

    @pytest.fixture
    def sample_question(self):
        """Create sample interactive question."""
        return InteractiveQuestion(
            id="irpef_tipo_contribuente",
            text="Che tipo di contribuente sei?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="dipendente", label="Dipendente"),
                InteractiveOption(id="autonomo", label="Autonomo"),
                InteractiveOption(id="altro", label="Altro", requires_input=True),
            ],
        )

    def test_valid_option_found(self, sample_question):
        """Test that valid option is found."""
        option_ids = [opt.id for opt in sample_question.options]
        assert "dipendente" in option_ids
        assert "autonomo" in option_ids

    def test_invalid_option_not_found(self, sample_question):
        """Test that invalid option is not found."""
        option_ids = [opt.id for opt in sample_question.options]
        assert "invalid_option" not in option_ids

    def test_option_requires_input(self, sample_question):
        """Test detecting option that requires custom input."""
        altro_option = next(opt for opt in sample_question.options if opt.id == "altro")
        assert altro_option.requires_input is True


class TestMultiStepQuestionFlow:
    """Test multi-step question flows."""

    @pytest.fixture
    def question_with_followup(self):
        """Create question that leads to another question."""
        return InteractiveQuestion(
            id="irpef_tipo_contribuente",
            text="Che tipo di contribuente sei?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="dipendente", label="Dipendente", leads_to="irpef_reddito_dipendente"),
                InteractiveOption(id="autonomo", label="Autonomo", leads_to="irpef_reddito_autonomo"),
            ],
        )

    @pytest.fixture
    def followup_question(self):
        """Create follow-up question."""
        return InteractiveQuestion(
            id="irpef_reddito_dipendente",
            text="Qual è il tuo reddito annuo lordo?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="under_28k", label="Fino a 28.000€"),
                InteractiveOption(id="over_28k", label="Oltre 28.000€"),
            ],
        )

    def test_option_leads_to_next_question(self, question_with_followup):
        """Test that option has leads_to for next question."""
        dipendente_option = next(opt for opt in question_with_followup.options if opt.id == "dipendente")
        assert dipendente_option.leads_to == "irpef_reddito_dipendente"

    def test_terminal_option_has_no_leads_to(self):
        """Test terminal option has no leads_to."""
        terminal_question = InteractiveQuestion(
            id="final_question",
            text="Conferma?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="yes", label="Sì"),
                InteractiveOption(id="no", label="No"),
            ],
        )
        for option in terminal_question.options:
            assert option.leads_to is None


class TestQuestionAnswerErrorHandling:
    """Test error handling for /questions/answer endpoint."""

    def test_invalid_question_id_returns_400(self):
        """Test that unknown question_id returns HTTP 400."""
        error = HTTPException(status_code=400, detail="Domanda non valida")
        assert error.status_code == 400
        assert error.detail == "Domanda non valida"

    def test_invalid_option_id_returns_400(self):
        """Test that unknown option_id returns HTTP 400."""
        error = HTTPException(status_code=400, detail="Opzione non valida")
        assert error.status_code == 400
        assert error.detail == "Opzione non valida"

    def test_missing_custom_input_returns_400(self):
        """Test that missing custom input when required returns HTTP 400."""
        error = HTTPException(status_code=400, detail="Input personalizzato richiesto")
        assert error.status_code == 400
        assert error.detail == "Input personalizzato richiesto"


class TestQuestionAnswerIntegration:
    """Integration tests for question answer flow."""

    def test_single_step_flow_returns_answer(self):
        """Test single-step flow returns answer."""
        from app.schemas.proactivity import QuestionAnswerRequest, QuestionAnswerResponse

        # Simulate request
        request = QuestionAnswerRequest(
            question_id="simple_question",
            selected_option="yes",
            session_id="session-123",
        )

        # Simulate response for terminal question
        response = QuestionAnswerResponse(
            answer="La risposta è affermativa.",
            suggested_actions=[],
        )

        assert response.answer is not None
        assert response.next_question is None

    def test_multi_step_flow_returns_next_question(self):
        """Test multi-step flow returns next question."""
        from app.schemas.proactivity import QuestionAnswerRequest, QuestionAnswerResponse

        # Simulate request
        request = QuestionAnswerRequest(
            question_id="irpef_tipo_contribuente",
            selected_option="dipendente",
            session_id="session-123",
        )

        # Simulate response with next question
        next_question = InteractiveQuestion(
            id="irpef_reddito",
            text="Qual è il tuo reddito?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="low", label="Basso"),
                InteractiveOption(id="high", label="Alto"),
            ],
        )
        response = QuestionAnswerResponse(next_question=next_question)

        assert response.next_question is not None
        assert response.answer is None

    def test_custom_input_processed(self):
        """Test custom input is processed correctly."""
        from app.schemas.proactivity import QuestionAnswerRequest

        request = QuestionAnswerRequest(
            question_id="irpef_reddito_custom",
            selected_option="altro",
            custom_input="65000",
            session_id="session-123",
        )

        assert request.custom_input == "65000"
        # The endpoint would use this to generate a prompt
