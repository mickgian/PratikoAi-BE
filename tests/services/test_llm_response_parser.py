"""
TDD Tests for llm_response_parser module.

Tests written FIRST as per DEV-176 requirements.
"""

import pytest


class TestParseValidResponse:
    """Tests for parsing valid LLM responses."""

    def test_parse_valid_response_with_both_tags(self):
        """Parser extracts answer and actions from well-formed response."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>
Questa è la risposta completa con informazioni dettagliate.
</answer>

<suggested_actions>
[
  {"id": "1", "label": "Approfondisci", "icon": "🔍", "prompt": "Spiega in dettaglio"},
  {"id": "2", "label": "Calcola", "icon": "💰", "prompt": "Calcola l'importo"}
]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert "Questa è la risposta completa" in result.answer
        assert len(result.suggested_actions) == 2
        assert result.suggested_actions[0].id == "1"
        assert result.suggested_actions[0].label == "Approfondisci"
        assert result.suggested_actions[0].icon == "🔍"
        assert result.suggested_actions[0].prompt == "Spiega in dettaglio"

    def test_parse_response_preserves_citations(self):
        """Parser preserves citation markers [1], [2] in answer text."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>
Secondo la normativa [1], l'aliquota è del 22% [2].
</answer>

<suggested_actions>
[{"id": "1", "label": "Test", "icon": "📋", "prompt": "Test prompt"}]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert "[1]" in result.answer
        assert "[2]" in result.answer


class TestMissingTags:
    """Tests for responses with missing tags."""

    def test_parse_response_without_answer_tag(self):
        """When no <answer> tag, full response used as answer."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = "Questa è una risposta senza tag."
        result = parse_llm_response(raw_response)

        assert result.answer == "Questa è una risposta senza tag."
        assert len(result.suggested_actions) == 0

    def test_parse_response_without_actions_tag(self):
        """When no <suggested_actions> tag, return empty actions."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>
Risposta senza azioni suggerite.
</answer>
"""
        result = parse_llm_response(raw_response)

        assert "Risposta senza azioni suggerite" in result.answer
        assert len(result.suggested_actions) == 0

    def test_parse_response_with_only_closing_tag(self):
        """Handle malformed response with only closing tag."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = "Some text</answer> more text"
        result = parse_llm_response(raw_response)

        # Should not crash, use full response
        assert result.answer == "Some text</answer> more text"
        assert len(result.suggested_actions) == 0


class TestEmptyAndNullResponses:
    """Tests for empty and null-like responses."""

    def test_parse_empty_response(self):
        """Empty string returns empty answer and empty actions."""
        from app.services.llm_response_parser import parse_llm_response

        result = parse_llm_response("")

        assert result.answer == ""
        assert len(result.suggested_actions) == 0

    def test_parse_whitespace_only_response(self):
        """Whitespace-only response returns empty answer."""
        from app.services.llm_response_parser import parse_llm_response

        result = parse_llm_response("   \n\t  ")

        assert result.answer.strip() == ""
        assert len(result.suggested_actions) == 0


class TestMalformedJson:
    """Tests for malformed JSON in suggested_actions."""

    def test_parse_response_with_malformed_json(self):
        """Malformed JSON returns empty actions, not crash."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>Valid answer</answer>
<suggested_actions>
[{"id": "1", "label": "Test" missing_comma "icon": "📋"}]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert result.answer == "Valid answer"
        assert len(result.suggested_actions) == 0

    def test_parse_response_with_empty_actions(self):
        """Empty actions array returns empty list."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>Answer text</answer>
<suggested_actions>
[]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert result.answer == "Answer text"
        assert len(result.suggested_actions) == 0

    def test_parse_partial_valid_actions(self):
        """Some valid, some invalid actions - include valid only."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>Answer</answer>
<suggested_actions>
[
  {"id": "1", "label": "Valid", "icon": "✅", "prompt": "Valid prompt"},
  {"id": "2", "label": "Missing icon and prompt"},
  {"id": "3", "label": "Also Valid", "icon": "📋", "prompt": "Another valid"}
]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert result.answer == "Answer"
        assert len(result.suggested_actions) == 2
        assert result.suggested_actions[0].id == "1"
        assert result.suggested_actions[1].id == "3"


class TestActionLimits:
    """Tests for action count limits."""

    def test_parse_response_with_more_than_4_actions_truncates(self):
        """More than 4 actions are truncated to 4."""
        from app.services.llm_response_parser import parse_llm_response

        actions = [
            {"id": str(i), "label": f"Action {i}", "icon": "📋", "prompt": f"Prompt {i}"}
            for i in range(1, 7)  # 6 actions
        ]
        import json

        raw_response = f"""
<answer>Answer</answer>
<suggested_actions>
{json.dumps(actions)}
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert len(result.suggested_actions) == 4
        assert result.suggested_actions[0].id == "1"
        assert result.suggested_actions[3].id == "4"


class TestActionValidation:
    """Tests for action field validation."""

    def test_parse_response_with_missing_action_fields_skips(self):
        """Actions missing required fields are skipped."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>Answer</answer>
<suggested_actions>
[
  {"id": "1", "label": "Missing icon and prompt"},
  {"label": "Missing id", "icon": "📋", "prompt": "Prompt"},
  {"id": "3", "label": "Complete", "icon": "✅", "prompt": "Valid"}
]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert len(result.suggested_actions) == 1
        assert result.suggested_actions[0].id == "3"

    def test_parse_response_ignores_extra_fields(self):
        """Extra fields in action objects are ignored."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>Answer</answer>
<suggested_actions>
[
  {"id": "1", "label": "Test", "icon": "📋", "prompt": "Prompt", "extra_field": "ignored", "another": 123}
]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert len(result.suggested_actions) == 1
        assert result.suggested_actions[0].id == "1"
        # Should not have extra fields on the model
        assert not hasattr(result.suggested_actions[0], "extra_field")


class TestWhitespaceHandling:
    """Tests for whitespace handling."""

    def test_parse_response_with_extra_whitespace(self):
        """Whitespace is trimmed from extracted content."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>

   Risposta con spazi extra

</answer>

<suggested_actions>
[
  {"id": "1", "label": "  Spaced  ", "icon": "📋", "prompt": "Prompt"}
]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert result.answer == "Risposta con spazi extra"
        assert len(result.suggested_actions) == 1


class TestNestedTags:
    """Tests for nested/escaped tags."""

    def test_parse_response_with_nested_tags_in_code_block(self):
        """Handle <answer> inside code blocks gracefully."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>
Here is an example:
```xml
<answer>This is inside a code block</answer>
```
The actual answer continues here.
</answer>

<suggested_actions>
[{"id": "1", "label": "Test", "icon": "📋", "prompt": "Prompt"}]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        # Should extract the outer answer, including the code block
        assert "code block" in result.answer
        assert len(result.suggested_actions) == 1


class TestUnicodeAndSpecialChars:
    """Tests for unicode and special characters."""

    def test_parse_unicode_in_response(self):
        """Unicode characters (emoji, accents) are preserved."""
        from app.services.llm_response_parser import parse_llm_response

        raw_response = """
<answer>
Risposta con caratteri speciali: àèìòù, €, 中文, 🎉
</answer>

<suggested_actions>
[{"id": "1", "label": "Verifica", "icon": "✅", "prompt": "Controlla tutto"}]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert "àèìòù" in result.answer
        assert "€" in result.answer
        assert "中文" in result.answer
        assert "🎉" in result.answer
        assert result.suggested_actions[0].icon == "✅"


class TestLongResponses:
    """Tests for very long responses."""

    def test_parse_very_long_response(self):
        """Parser handles very long responses efficiently."""
        from app.services.llm_response_parser import parse_llm_response

        long_text = "Lorem ipsum dolor sit amet. " * 500  # ~15000 chars
        raw_response = f"""
<answer>
{long_text}
</answer>

<suggested_actions>
[{{"id": "1", "label": "Test", "icon": "📋", "prompt": "Prompt"}}]
</suggested_actions>
"""
        result = parse_llm_response(raw_response)

        assert "Lorem ipsum" in result.answer
        assert len(result.suggested_actions) == 1


class TestNeverRaises:
    """Tests ensuring parser never raises exceptions."""

    def test_parse_response_never_raises(self):
        """Parser should never raise, always return valid ParsedLLMResponse."""
        from app.services.llm_response_parser import parse_llm_response

        problematic_inputs = [
            None,  # Will be handled as empty string
            "",
            "   ",
            "<answer>",
            "</answer>",
            "<suggested_actions>not json</suggested_actions>",
            "<answer><suggested_actions></answer></suggested_actions>",
            '{"broken": json',
            "null",
            "undefined",
            "<answer>" + "x" * 100000 + "</answer>",  # Very long
        ]

        for inp in problematic_inputs:
            # Should never raise
            if inp is None:
                result = parse_llm_response("")
            else:
                result = parse_llm_response(inp)

            # Always returns valid structure
            assert hasattr(result, "answer")
            assert hasattr(result, "suggested_actions")
            assert isinstance(result.suggested_actions, list)


class TestModelExports:
    """Tests for model class exports."""

    def test_parsed_llm_response_model_exists(self):
        """ParsedLLMResponse model must be importable."""
        from app.services.llm_response_parser import ParsedLLMResponse

        assert ParsedLLMResponse is not None

    def test_suggested_action_model_exists(self):
        """SuggestedAction model must be importable."""
        from app.services.llm_response_parser import SuggestedAction

        assert SuggestedAction is not None

    def test_models_are_pydantic(self):
        """Models should be Pydantic BaseModel instances."""
        from pydantic import BaseModel

        from app.services.llm_response_parser import ParsedLLMResponse, SuggestedAction

        assert issubclass(SuggestedAction, BaseModel)
        assert issubclass(ParsedLLMResponse, BaseModel)
