"""TDD tests for ActionRegenerator service.

DEV-217: Tests written FIRST per TDD methodology.
Tests cover regeneration logic, fallback generation, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.action_regenerator import (
    MAX_ATTEMPTS,
    ActionRegenerator,
    ResponseContext,
)
from app.services.action_validator import BatchValidationResult


class TestResponseContext:
    """Test ResponseContext dataclass."""

    def test_response_context_creation(self):
        """ResponseContext can be created with all fields."""
        context = ResponseContext(
            answer="La risposta è 22%",
            primary_source={"ref": "Art. 16 DPR 633/72", "relevant_paragraph": "L'aliquota IVA..."},
            extracted_values=["22%", "€15.000"],
            main_topic="IVA",
            kb_sources=[{"id": "doc1", "title": "DPR 633/72"}],
        )
        assert context.answer == "La risposta è 22%"
        assert context.main_topic == "IVA"
        assert len(context.extracted_values) == 2

    def test_response_context_with_empty_values(self):
        """ResponseContext works with empty optional values."""
        context = ResponseContext(
            answer="Risposta generica",
            primary_source={},
            extracted_values=[],
            main_topic="",
            kb_sources=[],
        )
        assert context.extracted_values == []
        assert context.main_topic == ""


class TestMaxAttemptsConstant:
    """Test MAX_ATTEMPTS constant."""

    def test_max_attempts_is_two(self):
        """MAX_ATTEMPTS should be 2 as per spec."""
        assert MAX_ATTEMPTS == 2


class TestRegenerateIfNeeded:
    """Test regenerate_if_needed method."""

    @pytest.fixture
    def mock_prompt_loader(self):
        loader = MagicMock()
        loader.load.return_value = "Mocked prompt template"
        return loader

    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_validator(self):
        validator = MagicMock()
        return validator

    @pytest.fixture
    def regenerator(self, mock_prompt_loader, mock_llm_client, mock_validator):
        regen = ActionRegenerator(
            prompt_loader=mock_prompt_loader,
            llm_client=mock_llm_client,
        )
        regen.validator = mock_validator
        return regen

    @pytest.fixture
    def valid_actions(self):
        return [
            {"id": "1", "label": "Calcola IVA 22%", "prompt": "Calcola l'IVA al 22%", "icon": "calculator"},
            {"id": "2", "label": "Verifica scadenza F24", "prompt": "Verifica la scadenza del modello F24", "icon": "calendar"},
            {"id": "3", "label": "Confronta aliquote", "prompt": "Confronta le aliquote IRPEF 2024", "icon": "chart"},
        ]

    @pytest.fixture
    def response_context(self):
        return ResponseContext(
            answer="L'aliquota IVA ordinaria è del 22%",
            primary_source={"ref": "DPR 633/72", "relevant_paragraph": "L'aliquota IVA..."},
            extracted_values=["22%", "€15.000"],
            main_topic="IVA",
            kb_sources=[{"id": "doc1", "title": "DPR 633/72", "key_topics": ["IVA"]}],
        )

    @pytest.mark.asyncio
    async def test_returns_valid_when_enough(self, regenerator, valid_actions, response_context):
        """No regeneration when >=2 valid actions exist."""
        validation_result = BatchValidationResult(
            validated_actions=valid_actions[:2],  # 2 valid actions
            rejected_count=1,
            rejection_log=[],
            quality_score=0.67,
        )

        result = await regenerator.regenerate_if_needed(
            original_actions=valid_actions,
            validation_result=validation_result,
            response_context=response_context,
        )

        assert result == valid_actions[:2]
        # LLM should not be called
        regenerator._attempt_regeneration = AsyncMock()
        assert not regenerator._attempt_regeneration.called

    @pytest.mark.asyncio
    async def test_regeneration_triggered(self, regenerator, response_context, mock_llm_client):
        """Regeneration triggered when <2 valid actions."""
        validation_result = BatchValidationResult(
            validated_actions=[{"id": "1", "label": "Valid action", "prompt": "Valid prompt here"}],
            rejected_count=2,
            rejection_log=[
                ({"label": "Bad", "prompt": "x"}, "Label too short"),
                ({"label": "Consulta", "prompt": "Consulta commercialista"}, "Forbidden pattern"),
            ],
            quality_score=0.33,
        )

        # Mock successful regeneration
        regenerated_actions = [
            {"id": "regen_1", "label": "Calcola contributi", "prompt": "Calcola i contributi dovuti"},
            {"id": "regen_2", "label": "Verifica scadenze", "prompt": "Verifica le scadenze fiscali"},
        ]
        mock_llm_client.generate.return_value = MagicMock(
            content='[{"id": "regen_1", "label": "Calcola contributi", "prompt": "Calcola i contributi dovuti"}, {"id": "regen_2", "label": "Verifica scadenze", "prompt": "Verifica le scadenze fiscali"}]'
        )
        regenerator.validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=regenerated_actions,
            rejected_count=0,
            rejection_log=[],
            quality_score=1.0,
        )

        result = await regenerator.regenerate_if_needed(
            original_actions=[],
            validation_result=validation_result,
            response_context=response_context,
        )

        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_regeneration_success_attempt_1(self, regenerator, response_context, mock_llm_client):
        """First regeneration attempt succeeds."""
        validation_result = BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )

        regenerated_actions = [
            {"id": "regen_1", "label": "Calcola contributi INPS", "prompt": "Calcola i contributi previdenziali"},
            {"id": "regen_2", "label": "Verifica scadenze fiscali", "prompt": "Verifica le prossime scadenze"},
        ]

        mock_llm_client.generate.return_value = MagicMock(
            content='[{"id": "regen_1", "label": "Calcola contributi INPS", "prompt": "Calcola i contributi previdenziali"}, {"id": "regen_2", "label": "Verifica scadenze fiscali", "prompt": "Verifica le prossime scadenze"}]'
        )
        regenerator.validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=regenerated_actions,
            rejected_count=0,
            rejection_log=[],
            quality_score=1.0,
        )

        result = await regenerator.regenerate_if_needed(
            original_actions=[],
            validation_result=validation_result,
            response_context=response_context,
        )

        assert len(result) == 2
        # Should only call LLM once
        assert mock_llm_client.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_regeneration_success_attempt_2(self, regenerator, response_context, mock_llm_client):
        """Second regeneration attempt succeeds after first fails."""
        validation_result = BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )

        # First attempt fails, second succeeds
        regenerated_actions = [
            {"id": "regen_1", "label": "Calcola contributi INPS", "prompt": "Calcola i contributi previdenziali"},
            {"id": "regen_2", "label": "Verifica scadenze fiscali", "prompt": "Verifica le prossime scadenze"},
        ]

        mock_llm_client.generate.return_value = MagicMock(
            content='[{"id": "regen_1", "label": "Calcola contributi INPS", "prompt": "Calcola i contributi previdenziali"}, {"id": "regen_2", "label": "Verifica scadenze fiscali", "prompt": "Verifica le prossime scadenze"}]'
        )

        # First validation fails, second succeeds
        regenerator.validator.validate_batch.side_effect = [
            BatchValidationResult(
                validated_actions=[],
                rejected_count=2,
                rejection_log=[],
                quality_score=0.0,
            ),
            BatchValidationResult(
                validated_actions=regenerated_actions,
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            ),
        ]

        result = await regenerator.regenerate_if_needed(
            original_actions=[],
            validation_result=validation_result,
            response_context=response_context,
        )

        assert len(result) == 2
        assert mock_llm_client.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_max_attempts_respected(self, regenerator, response_context, mock_llm_client):
        """Falls back after MAX_ATTEMPTS failed regenerations."""
        validation_result = BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )

        # All regeneration attempts fail validation
        mock_llm_client.generate.return_value = MagicMock(
            content='[{"id": "bad", "label": "Bad", "prompt": "x"}]'
        )
        regenerator.validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=[],
            rejected_count=1,
            rejection_log=[],
            quality_score=0.0,
        )

        result = await regenerator.regenerate_if_needed(
            original_actions=[],
            validation_result=validation_result,
            response_context=response_context,
        )

        # Should have called LLM MAX_ATTEMPTS times
        assert mock_llm_client.generate.call_count == MAX_ATTEMPTS
        # Should return fallback actions
        assert len(result) > 0
        assert any("fallback" in action.get("source_basis", "") for action in result)


class TestSafeFallback:
    """Test safe fallback action generation."""

    @pytest.fixture
    def regenerator(self):
        return ActionRegenerator(
            prompt_loader=MagicMock(),
            llm_client=AsyncMock(),
        )

    def test_safe_fallback_generated(self, regenerator):
        """Safe fallback actions are generated."""
        context = ResponseContext(
            answer="Risposta test",
            primary_source={},
            extracted_values=["22%"],
            main_topic="IVA",
            kb_sources=[],
        )

        fallback = regenerator._generate_safe_fallback(context)

        assert len(fallback) > 0
        assert len(fallback) <= 3

    def test_fallback_includes_topic(self, regenerator):
        """Fallback includes topic-based action when topic available."""
        context = ResponseContext(
            answer="Risposta test",
            primary_source={},
            extracted_values=[],
            main_topic="Contributi INPS",
            kb_sources=[],
        )

        fallback = regenerator._generate_safe_fallback(context)

        # Should have topic-based action
        topic_actions = [a for a in fallback if "topic" in a.get("source_basis", "")]
        assert len(topic_actions) >= 1

    def test_fallback_includes_value(self, regenerator):
        """Fallback includes value-based action when values present."""
        context = ResponseContext(
            answer="Risposta test",
            primary_source={},
            extracted_values=["€5.000", "22%"],
            main_topic="",
            kb_sources=[],
        )

        fallback = regenerator._generate_safe_fallback(context)

        # Should have value-based action
        value_actions = [a for a in fallback if "value" in a.get("source_basis", "")]
        assert len(value_actions) >= 1

    def test_fallback_always_has_deadline(self, regenerator):
        """Fallback always includes deadline action."""
        context = ResponseContext(
            answer="Risposta test",
            primary_source={},
            extracted_values=[],
            main_topic="",
            kb_sources=[],
        )

        fallback = regenerator._generate_safe_fallback(context)

        # Should have deadline action
        deadline_actions = [a for a in fallback if "deadline" in a.get("source_basis", "")]
        assert len(deadline_actions) >= 1

    def test_fallback_actions_have_valid_structure(self, regenerator):
        """Fallback actions have required fields."""
        context = ResponseContext(
            answer="Risposta test",
            primary_source={},
            extracted_values=["22%"],
            main_topic="IVA",
            kb_sources=[],
        )

        fallback = regenerator._generate_safe_fallback(context)

        for action in fallback:
            assert "id" in action
            assert "label" in action
            assert "icon" in action
            assert "prompt" in action
            assert "source_basis" in action


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_prompt_loader(self):
        loader = MagicMock()
        loader.load.return_value = "Mocked prompt template"
        return loader

    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def regenerator(self, mock_prompt_loader, mock_llm_client):
        regen = ActionRegenerator(
            prompt_loader=mock_prompt_loader,
            llm_client=mock_llm_client,
        )
        regen.validator = MagicMock()
        return regen

    @pytest.fixture
    def response_context(self):
        return ResponseContext(
            answer="Test answer",
            primary_source={},
            extracted_values=[],
            main_topic="Test",
            kb_sources=[],
        )

    @pytest.mark.asyncio
    async def test_llm_call_fails(self, regenerator, response_context, mock_llm_client):
        """Handles LLM errors gracefully."""
        validation_result = BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )

        # LLM raises exception
        mock_llm_client.generate.side_effect = Exception("LLM API error")

        result = await regenerator.regenerate_if_needed(
            original_actions=[],
            validation_result=validation_result,
            response_context=response_context,
        )

        # Should return fallback actions
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_json_parse_fails(self, regenerator, response_context, mock_llm_client):
        """Handles invalid JSON from LLM."""
        validation_result = BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )

        # LLM returns invalid JSON
        mock_llm_client.generate.return_value = MagicMock(content="Not valid JSON at all")
        regenerator.validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=[],
            rejected_count=0,
            rejection_log=[],
            quality_score=0.0,
        )

        result = await regenerator.regenerate_if_needed(
            original_actions=[],
            validation_result=validation_result,
            response_context=response_context,
        )

        # Should return fallback after max attempts
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_empty_regeneration_response(self, regenerator, response_context, mock_llm_client):
        """Empty LLM response treated as failure."""
        validation_result = BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )

        # LLM returns empty
        mock_llm_client.generate.return_value = MagicMock(content="")
        regenerator.validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=[],
            rejected_count=0,
            rejection_log=[],
            quality_score=0.0,
        )

        result = await regenerator.regenerate_if_needed(
            original_actions=[],
            validation_result=validation_result,
            response_context=response_context,
        )

        # Should return fallback
        assert len(result) > 0
        assert mock_llm_client.generate.call_count == MAX_ATTEMPTS

    @pytest.mark.asyncio
    async def test_no_primary_source(self, regenerator, mock_llm_client):
        """Works with minimal context (no primary source)."""
        context = ResponseContext(
            answer="Risposta generica",
            primary_source={},  # Empty
            extracted_values=[],
            main_topic="",  # Empty
            kb_sources=[],
        )
        validation_result = BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )

        mock_llm_client.generate.return_value = MagicMock(content="[]")
        regenerator.validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=[],
            rejected_count=0,
            rejection_log=[],
            quality_score=0.0,
        )

        result = await regenerator.regenerate_if_needed(
            original_actions=[],
            validation_result=validation_result,
            response_context=context,
        )

        # Should still return at least deadline fallback
        assert len(result) >= 1


class TestAttemptRegeneration:
    """Test _attempt_regeneration method."""

    @pytest.fixture
    def mock_prompt_loader(self):
        loader = MagicMock()
        loader.load.return_value = "Correction prompt with {rejection_reasons} and {main_source_ref}"
        return loader

    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def regenerator(self, mock_prompt_loader, mock_llm_client):
        return ActionRegenerator(
            prompt_loader=mock_prompt_loader,
            llm_client=mock_llm_client,
        )

    @pytest.fixture
    def response_context(self):
        return ResponseContext(
            answer="L'aliquota è del 22%",
            primary_source={"ref": "DPR 633/72", "relevant_paragraph": "L'aliquota IVA ordinaria..."},
            extracted_values=["22%"],
            main_topic="IVA",
            kb_sources=[],
        )

    @pytest.mark.asyncio
    async def test_attempt_loads_prompt(self, regenerator, response_context, mock_prompt_loader):
        """Regeneration loads action_regeneration prompt."""
        regenerator.llm_client.generate.return_value = MagicMock(content="[]")

        await regenerator._attempt_regeneration(
            attempt=0,
            rejection_reasons=[],
            context=response_context,
        )

        mock_prompt_loader.load.assert_called()

    @pytest.mark.asyncio
    async def test_attempt_calls_llm(self, regenerator, response_context, mock_llm_client):
        """Regeneration calls LLM client."""
        mock_llm_client.generate.return_value = MagicMock(content="[]")

        await regenerator._attempt_regeneration(
            attempt=0,
            rejection_reasons=[],
            context=response_context,
        )

        mock_llm_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_attempt_returns_parsed_actions(self, regenerator, response_context, mock_llm_client):
        """Regeneration returns parsed action list."""
        mock_llm_client.generate.return_value = MagicMock(
            content='[{"id": "1", "label": "Test action", "prompt": "Test prompt here", "icon": "calculator"}]'
        )

        result = await regenerator._attempt_regeneration(
            attempt=0,
            rejection_reasons=[],
            context=response_context,
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "1"


class TestPromptBuilding:
    """Test prompt building for regeneration."""

    @pytest.fixture
    def mock_prompt_loader(self):
        loader = MagicMock()
        loader.load.return_value = "Prompt loaded"
        return loader

    @pytest.fixture
    def regenerator(self, mock_prompt_loader):
        return ActionRegenerator(
            prompt_loader=mock_prompt_loader,
            llm_client=AsyncMock(),
        )

    def test_builds_rejection_reasons_list(self, regenerator):
        """Builds rejection reasons for prompt."""
        rejection_log = [
            ({"label": "Bad", "prompt": "x"}, "Label too short"),
            ({"label": "Consulta", "prompt": "Consulta commercialista"}, "Forbidden pattern"),
        ]

        reasons = regenerator._build_rejection_reasons(rejection_log)

        assert "Label too short" in reasons
        assert "Forbidden pattern" in reasons

    def test_extracts_values_from_answer(self, regenerator):
        """Extracts numeric values from answer text."""
        answer = "L'aliquota è del 22% su un importo di €15.000 entro il 16/03/2024"

        values = regenerator._extract_values_from_text(answer)

        assert "22%" in values
        assert any("15" in v or "€" in v for v in values)
