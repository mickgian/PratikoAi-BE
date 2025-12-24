"""Tests for proactivity schemas - DEV-150.

TDD: Tests written BEFORE implementation.
Tests cover: ActionCategory, Action, InteractiveOption, InteractiveQuestion,
ExtractedParameter, and ParameterExtractionResult schemas.
"""

import pytest
from pydantic import ValidationError


class TestActionCategory:
    """Test ActionCategory enum."""

    def test_action_category_enum_values(self):
        """Test all enum values are valid."""
        from app.schemas.proactivity import ActionCategory

        assert ActionCategory.CALCULATE == "calculate"
        assert ActionCategory.SEARCH == "search"
        assert ActionCategory.VERIFY == "verify"
        assert ActionCategory.EXPORT == "export"
        assert ActionCategory.EXPLAIN == "explain"

    def test_action_category_all_values_exist(self):
        """Test all expected enum values exist."""
        from app.schemas.proactivity import ActionCategory

        expected = {"calculate", "search", "verify", "export", "explain"}
        actual = {member.value for member in ActionCategory}
        assert actual == expected

    def test_action_category_is_string_enum(self):
        """Test ActionCategory is a string enum."""
        from app.schemas.proactivity import ActionCategory

        assert isinstance(ActionCategory.CALCULATE, str)
        assert ActionCategory.CALCULATE == "calculate"


class TestAction:
    """Test Action schema."""

    def test_action_creation_minimal(self):
        """Test creating an Action with minimal fields."""
        from app.schemas.proactivity import Action, ActionCategory

        action = Action(
            id="calculate_irpef",
            label="Calcola IRPEF",
            icon="calculate",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola l'IRPEF per {tipo_contribuente}",
        )

        assert action.id == "calculate_irpef"
        assert action.label == "Calcola IRPEF"
        assert action.icon == "calculate"
        assert action.category == ActionCategory.CALCULATE
        assert action.requires_input is False  # Default
        assert action.input_placeholder is None
        assert action.input_type is None

    def test_action_creation_with_input(self):
        """Test creating an Action that requires input."""
        from app.schemas.proactivity import Action, ActionCategory

        action = Action(
            id="recalculate",
            label="Ricalcola",
            icon="refresh",
            category=ActionCategory.CALCULATE,
            prompt_template="Ricalcola con importo {amount}",
            requires_input=True,
            input_placeholder="Nuovo importo",
            input_type="number",
        )

        assert action.requires_input is True
        assert action.input_placeholder == "Nuovo importo"
        assert action.input_type == "number"

    def test_action_validation(self):
        """Test Action validation - all required fields present."""
        from app.schemas.proactivity import Action, ActionCategory

        # Valid action
        action = Action(
            id="test",
            label="Test",
            icon="test",
            category=ActionCategory.SEARCH,
            prompt_template="Test {query}",
        )
        assert action.id == "test"

    def test_action_empty_label_rejected(self):
        """Test empty label is rejected."""
        from app.schemas.proactivity import Action, ActionCategory

        with pytest.raises(ValidationError) as exc_info:
            Action(
                id="test",
                label="",  # Empty label not allowed
                icon="test",
                category=ActionCategory.CALCULATE,
                prompt_template="Test",
            )

        assert "label" in str(exc_info.value)

    def test_action_empty_id_rejected(self):
        """Test empty id is rejected."""
        from app.schemas.proactivity import Action, ActionCategory

        with pytest.raises(ValidationError):
            Action(
                id="",  # Empty id not allowed
                label="Test",
                icon="test",
                category=ActionCategory.CALCULATE,
                prompt_template="Test",
            )

    def test_action_empty_prompt_template_rejected(self):
        """Test empty prompt_template is rejected."""
        from app.schemas.proactivity import Action, ActionCategory

        with pytest.raises(ValidationError):
            Action(
                id="test",
                label="Test",
                icon="test",
                category=ActionCategory.CALCULATE,
                prompt_template="",  # Empty not allowed
            )

    def test_action_invalid_category_rejected(self):
        """Test invalid category is rejected."""
        from app.schemas.proactivity import Action

        with pytest.raises(ValidationError):
            Action(
                id="test",
                label="Test",
                icon="test",
                category="invalid_category",
                prompt_template="Test",
            )

    def test_action_serialization(self):
        """Test Action JSON serialization."""
        from app.schemas.proactivity import Action, ActionCategory

        action = Action(
            id="test",
            label="Test",
            icon="test",
            category=ActionCategory.CALCULATE,
            prompt_template="Test",
        )

        data = action.model_dump()
        assert data["id"] == "test"
        assert data["category"] == "calculate"

    def test_action_from_dict(self):
        """Test Action creation from dict."""
        from app.schemas.proactivity import Action

        data = {
            "id": "test",
            "label": "Test",
            "icon": "test",
            "category": "calculate",
            "prompt_template": "Test",
        }

        action = Action.model_validate(data)
        assert action.id == "test"


class TestInteractiveOption:
    """Test InteractiveOption schema."""

    def test_interactive_option_creation_minimal(self):
        """Test creating an InteractiveOption with minimal fields."""
        from app.schemas.proactivity import InteractiveOption

        option = InteractiveOption(
            id="dipendente",
            label="Persona fisica (dipendente)",
        )

        assert option.id == "dipendente"
        assert option.label == "Persona fisica (dipendente)"
        assert option.icon is None
        assert option.leads_to is None
        assert option.requires_input is False

    def test_interactive_option_creation_full(self):
        """Test creating an InteractiveOption with all fields."""
        from app.schemas.proactivity import InteractiveOption

        option = InteractiveOption(
            id="altro",
            label="Altro (specifica)",
            icon="edit",
            leads_to="custom_input_question",
            requires_input=True,
        )

        assert option.id == "altro"
        assert option.icon == "edit"
        assert option.leads_to == "custom_input_question"
        assert option.requires_input is True

    def test_interactive_option_empty_id_rejected(self):
        """Test empty id is rejected."""
        from app.schemas.proactivity import InteractiveOption

        with pytest.raises(ValidationError):
            InteractiveOption(
                id="",  # Empty not allowed
                label="Test",
            )

    def test_interactive_option_empty_label_rejected(self):
        """Test empty label is rejected."""
        from app.schemas.proactivity import InteractiveOption

        with pytest.raises(ValidationError):
            InteractiveOption(
                id="test",
                label="",  # Empty not allowed
            )


class TestInteractiveQuestion:
    """Test InteractiveQuestion schema."""

    def test_interactive_question_creation_minimal(self):
        """Test creating an InteractiveQuestion with minimal fields."""
        from app.schemas.proactivity import InteractiveOption, InteractiveQuestion

        options = [
            InteractiveOption(id="opt1", label="Option 1"),
            InteractiveOption(id="opt2", label="Option 2"),
        ]

        question = InteractiveQuestion(
            id="test_question",
            text="Which option do you prefer?",
            question_type="single_choice",
            options=options,
        )

        assert question.id == "test_question"
        assert question.text == "Which option do you prefer?"
        assert question.question_type == "single_choice"
        assert len(question.options) == 2
        assert question.trigger_query is None
        assert question.allow_custom_input is False
        assert question.custom_input_placeholder is None
        assert question.prefilled_params is None

    def test_interactive_question_creation_full(self):
        """Test creating an InteractiveQuestion with all fields."""
        from app.schemas.proactivity import InteractiveOption, InteractiveQuestion

        options = [
            InteractiveOption(id="dipendente", label="Dipendente", icon="briefcase"),
            InteractiveOption(id="autonomo", label="Autonomo", icon="building"),
            InteractiveOption(id="altro", label="Altro", requires_input=True),
        ]

        question = InteractiveQuestion(
            id="irpef_tipo",
            trigger_query="calcolo irpef",
            text="Per quale tipo di contribuente vuoi calcolare l'IRPEF?",
            question_type="single_choice",
            options=options,
            allow_custom_input=True,
            custom_input_placeholder="Descrivi la situazione...",
            prefilled_params={"anno_fiscale": 2025},
        )

        assert question.id == "irpef_tipo"
        assert question.trigger_query == "calcolo irpef"
        assert len(question.options) == 3
        assert question.allow_custom_input is True
        assert question.custom_input_placeholder == "Descrivi la situazione..."
        assert question.prefilled_params == {"anno_fiscale": 2025}

    def test_multifield_question_allows_empty_options(self):
        """Test multi_field questions can have empty options.

        Multi-field questions use 'fields' instead of 'options'.
        Empty options list is valid for multi_field type.
        """
        from app.schemas.proactivity import InputField, InteractiveQuestion

        # multi_field question with no options but with fields
        fields = [
            InputField(id="reddito", label="Reddito lordo"),
            InputField(id="detrazioni", label="Detrazioni"),
        ]

        question = InteractiveQuestion(
            id="irpef_calc",
            text="Inserisci i dati per il calcolo IRPEF",
            question_type="multi_field",
            options=[],  # Empty is valid for multi_field
            fields=fields,
        )

        assert question.question_type == "multi_field"
        assert len(question.options) == 0
        assert len(question.fields) == 2

    def test_choice_question_with_single_option_allowed(self):
        """Test single option is now allowed (schema relaxed for flexibility).

        While 2+ options are recommended for choice types, the schema
        allows single options for edge cases (e.g., confirmation questions).
        """
        from app.schemas.proactivity import InteractiveOption, InteractiveQuestion

        # Single option now allowed (schema relaxed)
        question = InteractiveQuestion(
            id="confirm",
            text="Confermi l'operazione?",
            question_type="single_choice",
            options=[InteractiveOption(id="confirm", label="Conferma")],
        )

        assert len(question.options) == 1

    def test_choice_question_empty_options_uses_default(self):
        """Test empty options list uses default (empty list).

        Schema defaults to empty list if options not provided.
        For choice types, this means no options available.
        """
        from app.schemas.proactivity import InteractiveQuestion

        question = InteractiveQuestion(
            id="test",
            text="Test question",
            question_type="single_choice",
            # options not provided, defaults to []
        )

        assert question.options == []

    def test_interactive_question_empty_id_rejected(self):
        """Test empty id is rejected."""
        from app.schemas.proactivity import InteractiveOption, InteractiveQuestion

        options = [
            InteractiveOption(id="opt1", label="Option 1"),
            InteractiveOption(id="opt2", label="Option 2"),
        ]

        with pytest.raises(ValidationError):
            InteractiveQuestion(
                id="",  # Empty not allowed
                text="Test question",
                question_type="single_choice",
                options=options,
            )

    def test_interactive_question_empty_text_rejected(self):
        """Test empty text is rejected."""
        from app.schemas.proactivity import InteractiveOption, InteractiveQuestion

        options = [
            InteractiveOption(id="opt1", label="Option 1"),
            InteractiveOption(id="opt2", label="Option 2"),
        ]

        with pytest.raises(ValidationError):
            InteractiveQuestion(
                id="test",
                text="",  # Empty not allowed
                question_type="single_choice",
                options=options,
            )

    def test_interactive_question_serialization(self):
        """Test InteractiveQuestion JSON serialization."""
        from app.schemas.proactivity import InteractiveOption, InteractiveQuestion

        options = [
            InteractiveOption(id="opt1", label="Option 1"),
            InteractiveOption(id="opt2", label="Option 2"),
        ]

        question = InteractiveQuestion(
            id="test",
            text="Test question",
            question_type="single_choice",
            options=options,
        )

        data = question.model_dump()
        assert data["id"] == "test"
        assert len(data["options"]) == 2


class TestExtractedParameter:
    """Test ExtractedParameter schema."""

    def test_extracted_parameter_creation(self):
        """Test creating an ExtractedParameter."""
        from app.schemas.proactivity import ExtractedParameter

        param = ExtractedParameter(
            name="reddito",
            value="50000",
            confidence=0.95,
            source="query",
        )

        assert param.name == "reddito"
        assert param.value == "50000"
        assert param.confidence == 0.95
        assert param.source == "query"

    def test_extracted_parameter_confidence_range(self):
        """Test confidence must be 0.0-1.0 range."""
        from app.schemas.proactivity import ExtractedParameter

        # Valid confidence values
        param_low = ExtractedParameter(name="test", value="x", confidence=0.0, source="query")
        assert param_low.confidence == 0.0

        param_high = ExtractedParameter(name="test", value="x", confidence=1.0, source="query")
        assert param_high.confidence == 1.0

        param_mid = ExtractedParameter(name="test", value="x", confidence=0.5, source="query")
        assert param_mid.confidence == 0.5

    def test_extracted_parameter_confidence_below_zero_rejected(self):
        """Test confidence below 0.0 is rejected."""
        from app.schemas.proactivity import ExtractedParameter

        with pytest.raises(ValidationError) as exc_info:
            ExtractedParameter(name="test", value="x", confidence=-0.1, source="query")

        assert "confidence" in str(exc_info.value).lower()

    def test_extracted_parameter_confidence_above_one_rejected(self):
        """Test confidence above 1.0 is rejected."""
        from app.schemas.proactivity import ExtractedParameter

        with pytest.raises(ValidationError) as exc_info:
            ExtractedParameter(name="test", value="x", confidence=1.1, source="query")

        assert "confidence" in str(exc_info.value).lower()

    def test_extracted_parameter_empty_name_rejected(self):
        """Test empty name is rejected."""
        from app.schemas.proactivity import ExtractedParameter

        with pytest.raises(ValidationError):
            ExtractedParameter(name="", value="x", confidence=0.5, source="query")

    def test_extracted_parameter_empty_source_rejected(self):
        """Test empty source is rejected."""
        from app.schemas.proactivity import ExtractedParameter

        with pytest.raises(ValidationError):
            ExtractedParameter(name="test", value="x", confidence=0.5, source="")

    def test_extracted_parameter_allows_any_value(self):
        """Test value can be any type (string representation)."""
        from app.schemas.proactivity import ExtractedParameter

        # String value
        param1 = ExtractedParameter(name="test", value="string", confidence=0.5, source="query")
        assert param1.value == "string"

        # Numeric string
        param2 = ExtractedParameter(name="test", value="12345.67", confidence=0.5, source="query")
        assert param2.value == "12345.67"

        # Italian format
        param3 = ExtractedParameter(name="test", value="1.234,56", confidence=0.5, source="query")
        assert param3.value == "1.234,56"


class TestParameterExtractionResult:
    """Test ParameterExtractionResult schema."""

    def test_parameter_extraction_result_creation_minimal(self):
        """Test creating a ParameterExtractionResult with minimal fields."""
        from app.schemas.proactivity import ParameterExtractionResult

        result = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=[],
            missing_required=[],
            coverage=0.0,
            can_proceed=False,
        )

        assert result.intent == "calcolo_irpef"
        assert result.extracted == []
        assert result.missing_required == []
        assert result.coverage == 0.0
        assert result.can_proceed is False

    def test_parameter_extraction_result_creation_full(self):
        """Test creating a ParameterExtractionResult with extracted params."""
        from app.schemas.proactivity import ExtractedParameter, ParameterExtractionResult

        extracted = [
            ExtractedParameter(name="reddito", value="50000", confidence=0.95, source="query"),
            ExtractedParameter(name="tipo", value="dipendente", confidence=0.85, source="query"),
        ]

        result = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=extracted,
            missing_required=["detrazioni"],
            coverage=0.66,
            can_proceed=False,
        )

        assert result.intent == "calcolo_irpef"
        assert len(result.extracted) == 2
        assert result.missing_required == ["detrazioni"]
        assert result.coverage == 0.66
        assert result.can_proceed is False

    def test_parameter_extraction_result_full_coverage(self):
        """Test ParameterExtractionResult with full coverage."""
        from app.schemas.proactivity import ExtractedParameter, ParameterExtractionResult

        extracted = [
            ExtractedParameter(name="reddito", value="50000", confidence=0.95, source="query"),
            ExtractedParameter(name="tipo", value="dipendente", confidence=0.9, source="query"),
        ]

        result = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=extracted,
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        assert result.coverage == 1.0
        assert result.can_proceed is True
        assert result.missing_required == []

    def test_parameter_extraction_result_coverage_validation(self):
        """Test coverage must be 0.0-1.0 range."""
        from app.schemas.proactivity import ParameterExtractionResult

        # Below 0.0
        with pytest.raises(ValidationError):
            ParameterExtractionResult(
                intent="test",
                extracted=[],
                missing_required=[],
                coverage=-0.1,
                can_proceed=False,
            )

        # Above 1.0
        with pytest.raises(ValidationError):
            ParameterExtractionResult(
                intent="test",
                extracted=[],
                missing_required=[],
                coverage=1.1,
                can_proceed=False,
            )

    def test_parameter_extraction_result_intent_required(self):
        """Test intent field is required and cannot be empty."""
        from app.schemas.proactivity import ParameterExtractionResult

        with pytest.raises(ValidationError):
            ParameterExtractionResult(
                intent="",  # Empty not allowed
                extracted=[],
                missing_required=[],
                coverage=0.0,
                can_proceed=False,
            )

    def test_parameter_extraction_result_serialization(self):
        """Test ParameterExtractionResult JSON serialization."""
        from app.schemas.proactivity import ExtractedParameter, ParameterExtractionResult

        extracted = [
            ExtractedParameter(name="reddito", value="50000", confidence=0.95, source="query"),
        ]

        result = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=extracted,
            missing_required=["tipo"],
            coverage=0.5,
            can_proceed=False,
        )

        data = result.model_dump()
        assert data["intent"] == "calcolo_irpef"
        assert len(data["extracted"]) == 1
        assert data["coverage"] == 0.5


class TestProactivitySchemaIntegration:
    """Integration tests for proactivity schemas."""

    def test_action_with_category_enum(self):
        """Test Action uses ActionCategory enum correctly."""
        from app.schemas.proactivity import Action, ActionCategory

        action = Action(
            id="calculate_iva",
            label="Calcola IVA",
            icon="percent",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola IVA al {aliquota}% su {importo}",
            requires_input=True,
            input_placeholder="Inserisci importo",
            input_type="number",
        )

        # Serialize and deserialize
        data = action.model_dump()
        restored = Action.model_validate(data)

        assert restored.category == ActionCategory.CALCULATE
        assert restored.category.value == "calculate"

    def test_question_with_multiple_options(self):
        """Test InteractiveQuestion with multiple option types."""
        from app.schemas.proactivity import InteractiveOption, InteractiveQuestion

        options = [
            InteractiveOption(id="opt1", label="Standard", icon="check"),
            InteractiveOption(id="opt2", label="With Follow-up", leads_to="next_q"),
            InteractiveOption(id="altro", label="Altro", requires_input=True),
        ]

        question = InteractiveQuestion(
            id="regime_fiscale",
            trigger_query="quale regime fiscale",
            text="Quale regime fiscale preferisci?",
            question_type="single_choice",
            options=options,
            allow_custom_input=True,
        )

        # Verify different option types
        assert question.options[0].leads_to is None
        assert question.options[1].leads_to == "next_q"
        assert question.options[2].requires_input is True

    def test_extraction_result_with_parameters(self):
        """Test ParameterExtractionResult with ExtractedParameter list."""
        from app.schemas.proactivity import ExtractedParameter, ParameterExtractionResult

        params = [
            ExtractedParameter(name="importo", value="1000", confidence=0.9, source="query"),
            ExtractedParameter(name="aliquota", value="22", confidence=0.8, source="default"),
        ]

        result = ParameterExtractionResult(
            intent="calcolo_iva",
            extracted=params,
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        # Verify nested structure
        assert result.extracted[0].name == "importo"
        assert result.extracted[1].source == "default"

        # Full serialization
        data = result.model_dump()
        assert len(data["extracted"]) == 2
        assert data["extracted"][0]["confidence"] == 0.9

    def test_all_schemas_json_compatible(self):
        """Test all schemas can be serialized to JSON."""
        import json

        from app.schemas.proactivity import (
            Action,
            ActionCategory,
            ExtractedParameter,
            InteractiveOption,
            InteractiveQuestion,
            ParameterExtractionResult,
        )

        # Action
        action = Action(id="test", label="Test", icon="icon", category=ActionCategory.SEARCH, prompt_template="Test")
        json.dumps(action.model_dump())

        # InteractiveOption
        option = InteractiveOption(id="opt", label="Option")
        json.dumps(option.model_dump())

        # InteractiveQuestion
        question = InteractiveQuestion(
            id="q",
            text="Question?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="a", label="A"),
                InteractiveOption(id="b", label="B"),
            ],
        )
        json.dumps(question.model_dump())

        # ExtractedParameter
        param = ExtractedParameter(name="p", value="v", confidence=0.5, source="s")
        json.dumps(param.model_dump())

        # ParameterExtractionResult
        result = ParameterExtractionResult(
            intent="test", extracted=[param], missing_required=[], coverage=1.0, can_proceed=True
        )
        json.dumps(result.model_dump())
