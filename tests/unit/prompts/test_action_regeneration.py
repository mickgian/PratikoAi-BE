"""TDD tests for action_regeneration.md prompt template.

DEV-216: Tests written FIRST per TDD methodology.
Tests cover template loading, variable substitution, and content requirements.
"""

import json
import re

import pytest

from app.services.prompt_loader import PromptLoader


class TestActionRegenerationPromptLoading:
    """Test that the prompt loads correctly via PromptLoader."""

    @pytest.fixture
    def loader(self):
        return PromptLoader()

    def test_prompt_loads_via_loader(self, loader):
        """PromptLoader can load action_regeneration.md."""
        prompt = loader.load("action_regeneration")
        assert prompt is not None
        assert len(prompt) > 0

    def test_prompt_loads_from_v1_directory(self, loader):
        """Prompt loads from app/prompts/v1/ directory."""
        # Load with required variables
        prompt = loader.load(
            "action_regeneration",
            version="v1",
            rejection_reasons="Test",
            main_source_ref="Test",
            source_paragraph_text="Test",
            extracted_values="Test",
        )
        assert prompt is not None
        assert "Correzione Azioni Suggerite" in prompt or "azioni" in prompt.lower()


class TestActionRegenerationVariables:
    """Test template variable substitution."""

    @pytest.fixture
    def loader(self):
        return PromptLoader()

    @pytest.fixture
    def template(self, loader):
        return loader.load("action_regeneration")

    def test_prompt_contains_rejection_reasons_variable(self, template):
        """Template contains {rejection_reasons} variable."""
        assert "{rejection_reasons}" in template

    def test_prompt_contains_main_source_ref_variable(self, template):
        """Template contains {main_source_ref} variable."""
        assert "{main_source_ref}" in template

    def test_prompt_contains_source_paragraph_text_variable(self, template):
        """Template contains {source_paragraph_text} variable."""
        assert "{source_paragraph_text}" in template

    def test_prompt_contains_extracted_values_variable(self, template):
        """Template contains {extracted_values} variable."""
        assert "{extracted_values}" in template

    def test_all_variables_substitute_correctly(self, loader):
        """All template variables can be substituted via PromptLoader."""
        substituted = loader.load(
            "action_regeneration",
            rejection_reasons="- Label troppo corto\n- Pattern vietato",
            main_source_ref="Circolare INPS 45/2024",
            source_paragraph_text="Il contributo minimo per i forfettari è pari a €4.200 annui.",
            extracted_values="€4.200, 2024, forfettario",
        )
        assert "{rejection_reasons}" not in substituted
        assert "{main_source_ref}" not in substituted
        assert "{source_paragraph_text}" not in substituted
        assert "{extracted_values}" not in substituted
        assert "Label troppo corto" in substituted
        assert "Circolare INPS 45/2024" in substituted
        assert "€4.200" in substituted

    def test_variables_with_empty_values(self, loader):
        """Template handles empty variable values gracefully."""
        substituted = loader.load(
            "action_regeneration",
            rejection_reasons="",
            main_source_ref="",
            source_paragraph_text="",
            extracted_values="",
        )
        # Should not raise an error
        assert substituted is not None


class TestActionRegenerationContent:
    """Test prompt content requirements."""

    @pytest.fixture
    def loader(self):
        return PromptLoader()

    @pytest.fixture
    def template(self, loader):
        return loader.load("action_regeneration")

    def test_prompt_contains_italian_title(self, template):
        """Prompt has Italian title for action correction."""
        assert "Correzione" in template or "Azioni" in template

    def test_prompt_contains_rejection_section(self, template):
        """Prompt has section for rejection reasons."""
        template_lower = template.lower()
        assert "scartate" in template_lower or "rifiutate" in template_lower or "motivi" in template_lower

    def test_prompt_contains_source_reference_section(self, template):
        """Prompt has section for source references."""
        template_lower = template.lower()
        assert "fonte" in template_lower

    def test_prompt_contains_values_section(self, template):
        """Prompt has section for extracted values."""
        template_lower = template.lower()
        assert "valori" in template_lower

    def test_prompt_contains_rules_section(self, template):
        """Prompt has imperative rules section."""
        template_lower = template.lower()
        assert "regole" in template_lower or "imperative" in template_lower


class TestActionRegenerationJSONSchema:
    """Test JSON output schema in prompt."""

    @pytest.fixture
    def loader(self):
        return PromptLoader()

    @pytest.fixture
    def template(self, loader):
        return loader.load("action_regeneration")

    def test_prompt_contains_json_schema(self, template):
        """Prompt includes JSON output schema."""
        assert "```json" in template.lower() or "json" in template.lower()

    def test_prompt_contains_id_field(self, template):
        """JSON schema includes id field."""
        assert '"id"' in template

    def test_prompt_contains_label_field(self, template):
        """JSON schema includes label field."""
        assert '"label"' in template

    def test_prompt_contains_icon_field(self, template):
        """JSON schema includes icon field."""
        assert '"icon"' in template

    def test_prompt_contains_prompt_field(self, template):
        """JSON schema includes prompt field."""
        assert '"prompt"' in template

    def test_prompt_contains_source_basis_field(self, template):
        """JSON schema includes source_basis field."""
        assert '"source_basis"' in template

    def test_prompt_specifies_label_length(self, template):
        """Prompt specifies label length constraints (8-40 chars)."""
        assert "8" in template and "40" in template

    def test_prompt_specifies_prompt_length(self, template):
        """Prompt specifies prompt length constraint (>25 chars)."""
        assert "25" in template


class TestActionRegenerationExamples:
    """Test correct and incorrect examples in prompt."""

    @pytest.fixture
    def loader(self):
        return PromptLoader()

    @pytest.fixture
    def template(self, loader):
        return loader.load("action_regeneration")

    def test_prompt_contains_correct_examples(self, template):
        """Prompt includes examples of correct actions."""
        # Should have checkmark or "corrette" examples
        assert "✅" in template or "CORRETTE" in template.upper() or "corrette" in template.lower()

    def test_prompt_contains_incorrect_examples(self, template):
        """Prompt includes examples of incorrect actions."""
        # Should have X mark or "errate" examples
        assert "❌" in template or "ERRATE" in template.upper() or "errate" in template.lower()

    def test_correct_example_includes_specific_value(self, template):
        """Correct examples include specific values."""
        # Look for examples with percentages, amounts, or dates
        examples_pattern = r"(?:✅|CORRETTE).*?(?:€|%|\d{4})"
        assert re.search(examples_pattern, template, re.IGNORECASE | re.DOTALL)

    def test_incorrect_example_includes_generic_label(self, template):
        """Incorrect examples show generic labels like 'Approfondisci'."""
        template_lower = template.lower()
        # Common generic labels that should appear in bad examples
        assert any(
            generic in template_lower
            for generic in ["approfondisci", "calcola", "verifica"]
        )

    def test_incorrect_example_includes_forbidden_pattern(self, template):
        """Incorrect examples show forbidden patterns."""
        template_lower = template.lower()
        # Should show forbidden patterns like consulting professionals
        assert any(
            pattern in template_lower
            for pattern in ["commercialista", "consulta", "sito"]
        )


class TestActionRegenerationForbiddenPatterns:
    """Test forbidden pattern documentation in prompt."""

    @pytest.fixture
    def loader(self):
        return PromptLoader()

    @pytest.fixture
    def template(self, loader):
        return loader.load("action_regeneration")

    def test_prompt_forbids_consulting_professionals(self, template):
        """Prompt explicitly forbids suggesting professional consultation."""
        template_lower = template.lower()
        assert "professionisti" in template_lower or "commercialista" in template_lower

    def test_prompt_forbids_external_site_verification(self, template):
        """Prompt explicitly forbids external site verification suggestions."""
        template_lower = template.lower()
        assert "siti" in template_lower or "esterno" in template_lower or "esterni" in template_lower


class TestActionRegenerationIconValues:
    """Test icon enumeration in prompt."""

    @pytest.fixture
    def loader(self):
        return PromptLoader()

    @pytest.fixture
    def template(self, loader):
        return loader.load("action_regeneration")

    def test_prompt_contains_calculator_icon(self, template):
        """Prompt lists calculator as valid icon."""
        assert "calculator" in template.lower()

    def test_prompt_contains_multiple_icon_options(self, template):
        """Prompt lists multiple valid icon options."""
        template_lower = template.lower()
        icon_count = sum(
            1 for icon in ["calculator", "search", "calendar", "file", "alert", "check"]
            if icon in template_lower
        )
        assert icon_count >= 3, "Should list at least 3 icon options"


class TestActionRegenerationOutputCount:
    """Test action generation count specification."""

    @pytest.fixture
    def loader(self):
        return PromptLoader()

    @pytest.fixture
    def template(self, loader):
        return loader.load("action_regeneration")

    def test_prompt_specifies_action_count(self, template):
        """Prompt specifies number of actions to generate (3)."""
        assert "3" in template
        # Should mention generating 3 actions
        template_lower = template.lower()
        assert "3" in template and ("azioni" in template_lower or "nuove" in template_lower)
