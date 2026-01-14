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
            {
                "id": "2",
                "label": "Verifica scadenza F24",
                "prompt": "Verifica la scadenza del modello F24",
                "icon": "calendar",
            },
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
        mock_llm_client.generate.return_value = MagicMock(content='[{"id": "bad", "label": "Bad", "prompt": "x"}]')
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


class TestDEV242FallbackGrammar:
    """DEV-242: Test fallback grammar fixes - no truncated words, no double verbs."""

    @pytest.fixture
    def regenerator(self):
        return ActionRegenerator(
            prompt_loader=MagicMock(),
            llm_client=AsyncMock(),
        )

    # Tests for _truncate_at_word_boundary()
    class TestTruncateAtWordBoundary:
        """Test word boundary truncation to avoid mid-word cuts."""

        @pytest.fixture
        def regenerator(self):
            return ActionRegenerator(
                prompt_loader=MagicMock(),
                llm_client=AsyncMock(),
            )

        def test_short_text_unchanged(self, regenerator):
            """Text shorter than max_length is returned unchanged."""
            result = regenerator._truncate_at_word_boundary("IVA", 25)
            assert result == "IVA"

        def test_exact_length_unchanged(self, regenerator):
            """Text exactly at max_length is returned unchanged."""
            text = "a" * 25
            result = regenerator._truncate_at_word_boundary(text, 25)
            assert result == text

        def test_truncates_at_word_boundary(self, regenerator):
            """Long text is truncated at word boundary."""
            text = "Rottamazione quinquies scadenze fiscali 2026"
            result = regenerator._truncate_at_word_boundary(text, 25)
            # Should truncate at word boundary, not mid-word
            assert not result.endswith("scaden")  # No partial word
            assert " " not in result[-1:]  # No trailing space
            assert len(result) <= 25

        def test_no_partial_words(self, regenerator):
            """Never produces partial words like 'scaden' from 'scadenze'."""
            test_cases = [
                "scadenze fiscali importanti",
                "rottamazione quinquies 2026",
                "contributi previdenziali INPS",
            ]
            for text in test_cases:
                result = regenerator._truncate_at_word_boundary(text, 15)
                # Result should be complete words only
                words_in_result = result.split()
                for word in words_in_result:
                    assert word in text.split(), f"Partial word detected: {word}"

        def test_empty_string(self, regenerator):
            """Empty string returns empty string."""
            result = regenerator._truncate_at_word_boundary("", 25)
            assert result == ""

        def test_whitespace_only(self, regenerator):
            """Whitespace-only string returns empty string."""
            result = regenerator._truncate_at_word_boundary("   ", 25)
            assert result == ""

        def test_strips_trailing_punctuation(self, regenerator):
            """Strips trailing punctuation from truncated text."""
            text = "Scadenze: fiscali, importanti."
            result = regenerator._truncate_at_word_boundary(text, 10)
            assert not result.endswith(":")
            assert not result.endswith(",")

    # Tests for _starts_with_verb()
    class TestStartsWithVerb:
        """Test imperative verb detection."""

        @pytest.fixture
        def regenerator(self):
            return ActionRegenerator(
                prompt_loader=MagicMock(),
                llm_client=AsyncMock(),
            )

        @pytest.mark.parametrize(
            "verb",
            [
                "Verifica",
                "Calcola",
                "Controlla",
                "Consulta",
                "Leggi",
                "Vedi",
                "Scopri",
                "Approfondisci",
                "Cerca",
                "Trova",
                "Monitora",
                "Segui",
                "Chiedi",
                "Contatta",
            ],
        )
        def test_detects_imperative_verbs(self, regenerator, verb):
            """Detects common Italian imperative verbs."""
            text = f"{verb} le scadenze"
            assert regenerator._starts_with_verb(text) is True

        def test_detects_lowercase_verbs(self, regenerator):
            """Detects verbs regardless of case."""
            assert regenerator._starts_with_verb("verifica le scadenze") is True
            assert regenerator._starts_with_verb("CALCOLA importo") is True

        def test_does_not_match_nouns(self, regenerator):
            """Does not match noun phrases."""
            assert regenerator._starts_with_verb("Scadenze fiscali") is False
            assert regenerator._starts_with_verb("Calcolo IVA 22%") is False
            assert regenerator._starts_with_verb("Dettagli su IVA") is False

        def test_empty_string(self, regenerator):
            """Empty string returns False."""
            assert regenerator._starts_with_verb("") is False

    # Tests for _create_value_action()
    class TestCreateValueAction:
        """Test context-appropriate value action creation."""

        @pytest.fixture
        def regenerator(self):
            return ActionRegenerator(
                prompt_loader=MagicMock(),
                llm_client=AsyncMock(),
            )

        def test_creates_percentage_action(self, regenerator):
            """Creates appropriate action for percentage values."""
            action = regenerator._create_value_action("22%")
            assert action is not None
            assert "22%" in action["label"]
            assert "aliquota" in action["label"].lower()
            assert action["icon"] == "calculator"

        def test_creates_euro_action(self, regenerator):
            """Creates appropriate action for euro amounts."""
            action = regenerator._create_value_action("€15.000")
            assert action is not None
            assert "€15.000" in action["label"]
            assert "importo" in action["label"].lower()
            assert action["icon"] == "calculator"

        def test_creates_euro_text_action(self, regenerator):
            """Creates action for 'euro' text amounts."""
            action = regenerator._create_value_action("5.000 euro")
            assert action is not None
            assert "5.000 euro" in action["label"]

        def test_creates_date_action(self, regenerator):
            """Creates appropriate action for date values."""
            action = regenerator._create_value_action("16/03/2026")
            assert action is not None
            assert "16/03/2026" in action["label"]
            assert "scadenza" in action["label"].lower()
            assert action["icon"] == "calendar"

        def test_creates_date_dash_format_action(self, regenerator):
            """Creates action for dash-formatted dates."""
            action = regenerator._create_value_action("2026-03-16")
            assert action is not None
            assert "2026-03-16" in action["label"]
            assert action["icon"] == "calendar"

        def test_creates_generic_value_action(self, regenerator):
            """Creates generic action for numeric values."""
            action = regenerator._create_value_action("1000")
            assert action is not None
            assert "1000" in action["label"]
            assert "esempio" in action["label"].lower()

        def test_returns_none_for_empty(self, regenerator):
            """Returns None for empty value."""
            assert regenerator._create_value_action("") is None
            assert regenerator._create_value_action(None) is None

    # Tests for _validate_fallback_grammar()
    class TestValidateFallbackGrammar:
        """Test grammar validation and double-verb prevention."""

        @pytest.fixture
        def regenerator(self):
            return ActionRegenerator(
                prompt_loader=MagicMock(),
                llm_client=AsyncMock(),
            )

        def test_rejects_short_labels(self, regenerator):
            """Rejects labels shorter than 8 characters."""
            actions = [
                {"id": "1", "label": "Short", "icon": "search"},
                {"id": "2", "label": "Valid label here", "icon": "search"},
            ]
            result = regenerator._validate_fallback_grammar(actions)
            assert len(result) == 1
            assert result[0]["label"] == "Valid label here"

        def test_fixes_double_verb_pattern(self, regenerator):
            """Fixes 'Approfondisci Verifica le scadenze' → 'Verifica le scadenze'."""
            actions = [
                {"id": "1", "label": "Approfondisci Verifica le scadenze", "icon": "search"},
            ]
            result = regenerator._validate_fallback_grammar(actions)
            # Should fix the double verb
            assert len(result) == 1
            assert not result[0]["label"].startswith("Approfondisci")

        def test_preserves_valid_labels(self, regenerator):
            """Preserves grammatically correct labels."""
            actions = [
                {"id": "1", "label": "Dettagli su IVA 22%", "icon": "search"},
                {"id": "2", "label": "Calcolo contributi INPS", "icon": "calculator"},
            ]
            result = regenerator._validate_fallback_grammar(actions)
            assert len(result) == 2
            assert result[0]["label"] == "Dettagli su IVA 22%"

        def test_empty_list_returns_empty(self, regenerator):
            """Empty list returns empty list."""
            result = regenerator._validate_fallback_grammar([])
            assert result == []

    # Integration tests for _generate_safe_fallback()
    class TestGenerateSafeFallbackIntegration:
        """Integration tests for complete fallback generation."""

        @pytest.fixture
        def regenerator(self):
            return ActionRegenerator(
                prompt_loader=MagicMock(),
                llm_client=AsyncMock(),
            )

        def test_no_approfondisci_in_labels(self, regenerator):
            """DEV-242: Labels should not start with 'Approfondisci'."""
            context = ResponseContext(
                answer="Risposta test",
                primary_source={},
                extracted_values=["22%"],
                main_topic="Rottamazione quinquies",
                kb_sources=[],
            )
            fallback = regenerator._generate_safe_fallback(context)

            for action in fallback:
                assert (
                    not action["label"].lower().startswith("approfondisci")
                ), f"Label should not start with 'Approfondisci': {action['label']}"

        def test_no_truncated_words_in_labels(self, regenerator):
            """DEV-242: Labels should have complete words only."""
            context = ResponseContext(
                answer="Risposta test",
                primary_source={},
                extracted_values=[],
                main_topic="Rottamazione quinquies scadenze fiscali importanti",
                kb_sources=[],
            )
            fallback = regenerator._generate_safe_fallback(context)

            for action in fallback:
                label = action["label"]
                # No partial words - all words should be complete
                assert "..." not in label
                # Check for common truncation patterns
                assert not any(label.endswith(x) for x in ["scaden", "rottama", "quinqu"])

        def test_uses_noun_phrases_not_imperatives(self, regenerator):
            """DEV-242: Uses noun phrases like 'Dettagli su' not 'Approfondisci'."""
            context = ResponseContext(
                answer="Risposta test",
                primary_source={},
                extracted_values=[],
                main_topic="contributi INPS",
                kb_sources=[],
            )
            fallback = regenerator._generate_safe_fallback(context)

            topic_actions = [a for a in fallback if "topic" in a.get("source_basis", "")]
            if topic_actions:
                label = topic_actions[0]["label"]
                # Should use "Dettagli su" pattern
                assert "Dettagli su" in label or "dettagli" in label.lower()

        def test_all_labels_grammatically_correct(self, regenerator):
            """DEV-242: All fallback labels are grammatically correct Italian."""
            context = ResponseContext(
                answer="L'aliquota IVA è del 22% con scadenza 16/03/2026",
                primary_source={},
                extracted_values=["22%", "16/03/2026"],
                main_topic="IVA ordinaria",
                kb_sources=[],
            )
            fallback = regenerator._generate_safe_fallback(context)

            for action in fallback:
                label = action["label"]
                # Label should be at least 8 chars
                assert len(label) >= 8, f"Label too short: {label}"
                # No double verbs
                words = label.split()
                if len(words) >= 2:
                    # If first word ends with 'i' (imperative) and second is capitalized
                    # it shouldn't also be an imperative verb
                    first = words[0].lower()
                    second = words[1] if len(words) > 1 else ""
                    imperative_endings = ["verifica", "calcola", "controlla", "approfondisci"]
                    if first in imperative_endings and second and second[0].isupper():
                        assert second.lower() not in imperative_endings, f"Double verb pattern: {label}"

        def test_percentage_value_creates_calculator_action(self, regenerator):
            """DEV-242: Percentage values create appropriate calculator actions."""
            context = ResponseContext(
                answer="Test",
                primary_source={},
                extracted_values=["22%"],
                main_topic="",
                kb_sources=[],
            )
            fallback = regenerator._generate_safe_fallback(context)

            value_actions = [a for a in fallback if "value" in a.get("source_basis", "")]
            if value_actions:
                assert "22%" in value_actions[0]["label"]
                assert value_actions[0]["icon"] == "calculator"

        def test_date_value_creates_calendar_action(self, regenerator):
            """DEV-242: Date values create appropriate calendar actions."""
            context = ResponseContext(
                answer="Test",
                primary_source={},
                extracted_values=["16/03/2026"],
                main_topic="",
                kb_sources=[],
            )
            fallback = regenerator._generate_safe_fallback(context)

            date_actions = [a for a in fallback if "date" in a.get("source_basis", "")]
            if date_actions:
                assert "16/03/2026" in date_actions[0]["label"]
                assert date_actions[0]["icon"] == "calendar"

        def test_skips_topic_starting_with_verb(self, regenerator):
            """DEV-242: Skips topics that start with imperative verbs."""
            context = ResponseContext(
                answer="Test",
                primary_source={},
                extracted_values=[],
                main_topic="Verifica le scadenze fiscali",  # Starts with verb
                kb_sources=[],
            )
            fallback = regenerator._generate_safe_fallback(context)

            # Should not create topic action for verb-starting topic
            topic_actions = [a for a in fallback if "topic" in a.get("source_basis", "")]
            # Either no topic action, or it doesn't use the verb-starting topic directly
            for action in topic_actions:
                assert not action["label"].startswith("Dettagli su Verifica")
