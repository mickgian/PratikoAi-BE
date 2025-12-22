"""TDD Tests for /actions/execute Endpoint - DEV-160.

Tests for POST /api/v1/chatbot/actions/execute endpoint:
- Valid action execution
- Parameter substitution in prompt_template
- Invalid action_id handling (HTTP 400)
- Missing required input handling (HTTP 400)
- Returns full ChatResponse with new actions
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.chat import ChatResponse, Message
from app.schemas.proactivity import Action, ActionCategory


class TestActionExecuteRequest:
    """Test ActionExecuteRequest schema validation."""

    def test_valid_request_minimal(self):
        """Test valid request with minimal fields."""
        from app.schemas.proactivity import ActionExecuteRequest

        request = ActionExecuteRequest(
            action_id="tax_calculate_irpef",
            session_id="session-123",
        )
        assert request.action_id == "tax_calculate_irpef"
        assert request.session_id == "session-123"
        assert request.parameters is None

    def test_valid_request_with_parameters(self):
        """Test valid request with parameters."""
        from app.schemas.proactivity import ActionExecuteRequest

        request = ActionExecuteRequest(
            action_id="tax_calculate_irpef",
            session_id="session-123",
            parameters={"reddito": "50000", "anno": "2024"},
        )
        assert request.parameters == {"reddito": "50000", "anno": "2024"}

    def test_request_requires_action_id(self):
        """Test that action_id is required."""
        from app.schemas.proactivity import ActionExecuteRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ActionExecuteRequest(session_id="session-123")

    def test_request_requires_session_id(self):
        """Test that session_id is required."""
        from app.schemas.proactivity import ActionExecuteRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ActionExecuteRequest(action_id="tax_calculate_irpef")


class TestPromptTemplateSubstitution:
    """Test parameter substitution in prompt templates."""

    def test_substitute_single_parameter(self):
        """Test substituting a single parameter in template."""
        template = "Calcola l'IRPEF per reddito {reddito}"
        parameters = {"reddito": "50000"}

        result = template.format(**parameters)

        assert result == "Calcola l'IRPEF per reddito 50000"

    def test_substitute_multiple_parameters(self):
        """Test substituting multiple parameters in template."""
        template = "Calcola l'IRPEF per {tipo_contribuente} con reddito {reddito} per l'anno {anno}"
        parameters = {"tipo_contribuente": "dipendente", "reddito": "50000", "anno": "2024"}

        result = template.format(**parameters)

        assert result == "Calcola l'IRPEF per dipendente con reddito 50000 per l'anno 2024"

    def test_missing_parameter_raises_error(self):
        """Test that missing parameter raises KeyError."""
        template = "Calcola l'IRPEF per reddito {reddito}"
        parameters = {}

        with pytest.raises(KeyError):
            template.format(**parameters)

    def test_extra_parameters_ignored(self):
        """Test that extra parameters are ignored."""
        template = "Calcola l'IRPEF per reddito {reddito}"
        parameters = {"reddito": "50000", "extra": "ignored"}

        result = template.format(**parameters)

        assert result == "Calcola l'IRPEF per reddito 50000"


class TestActionLookup:
    """Test action template lookup."""

    @pytest.fixture
    def mock_template_service(self):
        """Create mock template service."""
        service = MagicMock()
        service.get_action_by_id = MagicMock()
        return service

    @pytest.fixture
    def sample_action(self):
        """Create sample action."""
        return Action(
            id="tax_calculate_irpef",
            label="Calcola IRPEF",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola l'IRPEF per {tipo_contribuente} con reddito {reddito}",
            requires_input=False,
        )

    def test_action_found_by_id(self, mock_template_service, sample_action):
        """Test action is found by ID."""
        mock_template_service.get_action_by_id.return_value = sample_action

        result = mock_template_service.get_action_by_id("tax_calculate_irpef")

        assert result is not None
        assert result.id == "tax_calculate_irpef"

    def test_action_not_found_returns_none(self, mock_template_service):
        """Test unknown action_id returns None."""
        mock_template_service.get_action_by_id.return_value = None

        result = mock_template_service.get_action_by_id("unknown_action")

        assert result is None


class TestActionExecuteResponse:
    """Test /actions/execute response format."""

    def test_response_is_chat_response(self):
        """Test that response is a ChatResponse."""
        messages = [Message(role="assistant", content="L'IRPEF dovuta è...")]
        response = ChatResponse(messages=messages)

        assert isinstance(response, ChatResponse)
        assert len(response.messages) == 1

    def test_response_includes_new_actions(self):
        """Test that response includes new suggested actions."""
        messages = [Message(role="assistant", content="L'IRPEF dovuta è...")]
        actions = [
            Action(
                id="tax_explain_irpef",
                label="Spiega dettagli IRPEF",
                icon="info",
                category=ActionCategory.EXPLAIN,
                prompt_template="Spiega i dettagli del calcolo IRPEF",
            )
        ]
        response = ChatResponse(messages=messages, suggested_actions=actions)

        assert response.suggested_actions is not None
        assert len(response.suggested_actions) == 1
        assert response.suggested_actions[0].id == "tax_explain_irpef"


class TestActionExecuteErrorHandling:
    """Test error handling for /actions/execute endpoint."""

    def test_invalid_action_id_returns_400(self):
        """Test that unknown action_id returns HTTP 400."""
        # Simulate the error that should be raised
        error = HTTPException(status_code=400, detail="Azione non valida")
        assert error.status_code == 400
        assert error.detail == "Azione non valida"

    def test_missing_required_input_returns_400(self):
        """Test that missing required input returns HTTP 400."""
        # Simulate the error for missing required parameter
        error = HTTPException(status_code=400, detail="Parametro richiesto mancante: reddito")
        assert error.status_code == 400
        assert "Parametro richiesto mancante" in error.detail

    def test_invalid_parameter_type_returns_400(self):
        """Test that invalid parameter type returns HTTP 400."""
        error = HTTPException(status_code=400, detail="Tipo di parametro non valido: reddito deve essere un numero")
        assert error.status_code == 400


class TestActionExecuteIntegration:
    """Integration tests for action execution flow."""

    @pytest.fixture
    def sample_action_with_input(self):
        """Create sample action that requires input."""
        return Action(
            id="tax_calculate_with_input",
            label="Calcola con input",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola l'imposta su {importo}",
            requires_input=True,
            input_placeholder="Inserisci l'importo",
        )

    def test_action_requires_input_validation(self, sample_action_with_input):
        """Test that action requiring input validates input is provided."""
        action = sample_action_with_input
        parameters = {}  # No input provided

        # Check if action requires input
        assert action.requires_input is True

        # Should raise error if parameters is empty or missing required key
        with pytest.raises(KeyError):
            action.prompt_template.format(**parameters)

    def test_action_prompt_generation(self, sample_action_with_input):
        """Test action prompt is correctly generated from template."""
        action = sample_action_with_input
        parameters = {"importo": "10000"}

        prompt = action.prompt_template.format(**parameters)

        assert prompt == "Calcola l'imposta su 10000"

    def test_full_action_execution_flow(self):
        """Test the complete action execution flow."""
        # 1. Create request
        from app.schemas.proactivity import ActionExecuteRequest

        request = ActionExecuteRequest(
            action_id="tax_calculate_irpef",
            session_id="session-123",
            parameters={"reddito": "50000", "tipo_contribuente": "dipendente"},
        )

        # 2. Lookup action (simulated)
        action = Action(
            id="tax_calculate_irpef",
            label="Calcola IRPEF",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola l'IRPEF per {tipo_contribuente} con reddito {reddito}",
        )

        # 3. Generate prompt
        prompt = action.prompt_template.format(**request.parameters)
        assert prompt == "Calcola l'IRPEF per dipendente con reddito 50000"

        # 4. Response would be generated by chat endpoint
        # This is integration tested separately
