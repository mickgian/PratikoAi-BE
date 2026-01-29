"""Tests for unified response prompt content.

DEV-250: Ensures prompt contains required formatting instructions.
"""

from pathlib import Path


class TestUnifiedResponsePrompt:
    """Test that the unified response prompt contains required instructions."""

    def test_prompt_contains_sequential_numbering_instructions(self):
        """DEV-250: Prompt must include sequential numbering rules.

        Section headers like ## 1., ## 2., ## 3. must be sequential,
        not all starting with ## 1.

        This test ensures the prompt explicitly instructs the LLM to use
        sequential numbers in both section headers and lists.
        """
        prompt_path = Path("app/prompts/v1/unified_response_simple.md")
        content = prompt_path.read_text()

        # Check for sequential numbering instruction
        assert (
            "SEQUENZIALI" in content or "sequenziali" in content
        ), "Prompt must include instruction for sequential numbering"
        assert "1, 2, 3" in content, "Prompt must show example of sequential numbering (1, 2, 3)"

    def test_prompt_warns_against_repeating_one(self):
        """DEV-250: Prompt must warn against repeating '1.' for every section.

        The LLM was generating ## 1. for every section header instead of
        ## 1., ## 2., ## 3., ## 4.
        """
        prompt_path = Path("app/prompts/v1/unified_response_simple.md")
        content = prompt_path.read_text()

        # Check for warning about repeating "1."
        assert (
            "MAI ripetere" in content or "mai ripetere" in content.lower()
        ), "Prompt must warn against repeating '1.' for every section"

    def test_prompt_shows_correct_and_incorrect_section_examples(self):
        """DEV-250: Prompt must show correct numbered section header examples."""
        prompt_path = Path("app/prompts/v1/unified_response_simple.md")
        content = prompt_path.read_text()

        # Check for section header examples with sequential numbers
        assert (
            "## 1." in content and "## 2." in content
        ), "Prompt must show sequential section header examples (## 1., ## 2.)"
        # Check for correct/incorrect indicators
        assert "CORRETTO" in content, "Prompt must show correct format example"
        assert "ERRATO" in content, "Prompt must show incorrect format example to avoid"

    def test_prompt_warns_against_blank_lines_in_lists(self):
        """DEV-250: Prompt must warn against blank lines between list items."""
        prompt_path = Path("app/prompts/v1/unified_response_simple.md")
        content = prompt_path.read_text()

        # Check for warning about blank lines
        assert "righe vuote" in content.lower(), "Prompt must warn about blank lines between list items"
