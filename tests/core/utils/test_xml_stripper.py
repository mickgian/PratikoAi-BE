"""Tests for XML stripping utility (DEV-201).

TDD tests for clean_proactivity_content() function that strips
<answer> and <suggested_actions> XML tags from LLM responses.
"""

import pytest

from app.core.utils.xml_stripper import (
    clean_proactivity_content,
    strip_answer_tags,
    strip_suggested_actions_block,
)


class TestStripAnswerTags:
    """Tests for strip_answer_tags() function."""

    def test_strips_opening_answer_tag(self) -> None:
        """Should remove <answer> tag."""
        content = "<answer>This is the response."
        result = strip_answer_tags(content)
        assert result == "This is the response."

    def test_strips_closing_answer_tag(self) -> None:
        """Should remove </answer> tag."""
        content = "This is the response.</answer>"
        result = strip_answer_tags(content)
        assert result == "This is the response."

    def test_strips_both_answer_tags(self) -> None:
        """Should remove both <answer> and </answer> tags."""
        content = "<answer>This is the response.</answer>"
        result = strip_answer_tags(content)
        assert result == "This is the response."

    def test_case_insensitive(self) -> None:
        """Should handle case variations."""
        content = "<ANSWER>Response</ANSWER>"
        result = strip_answer_tags(content)
        assert result == "Response"

    def test_preserves_content_without_tags(self) -> None:
        """Should return content unchanged if no answer tags."""
        content = "No tags here"
        result = strip_answer_tags(content)
        assert result == "No tags here"

    def test_handles_multiline_content(self) -> None:
        """Should handle multiline content inside answer tags."""
        content = "<answer>\nLine 1\nLine 2\nLine 3\n</answer>"
        result = strip_answer_tags(content)
        assert result == "\nLine 1\nLine 2\nLine 3\n"


class TestStripSuggestedActionsBlock:
    """Tests for strip_suggested_actions_block() function."""

    def test_strips_suggested_actions_block(self) -> None:
        """Should remove entire suggested_actions block."""
        content = 'Content before <suggested_actions>[{"id": "1"}]</suggested_actions> after'
        result = strip_suggested_actions_block(content)
        assert result == "Content before  after"

    def test_strips_multiline_suggested_actions(self) -> None:
        """Should handle multiline suggested_actions block."""
        content = """Response text.

<suggested_actions>
[
  {"id": "1", "label": "Action 1", "icon": "💰", "prompt": "Do action 1"},
  {"id": "2", "label": "Action 2", "icon": "📋", "prompt": "Do action 2"}
]
</suggested_actions>"""
        result = strip_suggested_actions_block(content)
        assert result == "Response text.\n\n"

    def test_case_insensitive(self) -> None:
        """Should handle case variations."""
        content = "<SUGGESTED_ACTIONS>[...]</SUGGESTED_ACTIONS>"
        result = strip_suggested_actions_block(content)
        assert result == ""

    def test_preserves_content_without_block(self) -> None:
        """Should return content unchanged if no suggested_actions block."""
        content = "No actions here"
        result = strip_suggested_actions_block(content)
        assert result == "No actions here"

    def test_handles_empty_block(self) -> None:
        """Should handle empty suggested_actions block."""
        content = "Text<suggested_actions></suggested_actions>"
        result = strip_suggested_actions_block(content)
        assert result == "Text"


class TestCleanProactivityContent:
    """Tests for clean_proactivity_content() main function."""

    def test_strips_both_answer_and_suggested_actions(self) -> None:
        """Should strip both types of tags."""
        content = """<answer>
This is the response.

<suggested_actions>
[{"id": "1", "label": "Action", "icon": "💰", "prompt": "Do it"}]
</suggested_actions>
</answer>"""
        result = clean_proactivity_content(content)
        assert "<answer>" not in result
        assert "</answer>" not in result
        assert "<suggested_actions>" not in result
        assert "This is the response." in result

    def test_strips_and_trims_whitespace(self) -> None:
        """Should strip tags and trim leading/trailing whitespace."""
        content = "  <answer>Response</answer>  "
        result = clean_proactivity_content(content)
        assert result == "Response"

    def test_handles_empty_string(self) -> None:
        """Should handle empty string input."""
        result = clean_proactivity_content("")
        assert result == ""

    def test_handles_content_without_any_tags(self) -> None:
        """Should return trimmed content if no tags present."""
        content = "  Plain text response  "
        result = clean_proactivity_content(content)
        assert result == "Plain text response"

    def test_real_world_example_with_actions(self) -> None:
        """Test with realistic LLM output containing suggested actions."""
        content = """<answer>
Il regime forfettario è un regime fiscale agevolato previsto dalla normativa italiana...

Per ulteriori informazioni, posso cercare nella knowledge base di PratikoAI.
</answer>

<suggested_actions>
[
  {"id": "1", "label": "Approfondisci requisiti", "icon": "📖", "prompt": "Quali sono i requisiti per accedere al regime forfettario?"},
  {"id": "2", "label": "Calcola tassazione", "icon": "💰", "prompt": "Calcola la tassazione per un forfettario con ricavi di 50000 euro"},
  {"id": "3", "label": "Confronta regimi", "icon": "📊", "prompt": "Confronta il regime forfettario con il regime ordinario"}
]
</suggested_actions>"""
        result = clean_proactivity_content(content)

        # Should not contain any XML tags
        assert "<answer>" not in result
        assert "</answer>" not in result
        assert "<suggested_actions>" not in result
        assert "</suggested_actions>" not in result

        # Should contain the actual response text
        assert "regime forfettario" in result
        assert "knowledge base" in result

        # Should not contain the JSON actions
        assert '"id"' not in result
        assert '"label"' not in result

    def test_preserves_markdown_formatting(self) -> None:
        """Should preserve markdown formatting in content."""
        content = """<answer>
# Heading

**Bold text** and *italic text*.

- List item 1
- List item 2

```python
code_block = True
```
</answer>"""
        result = clean_proactivity_content(content)
        assert "# Heading" in result
        assert "**Bold text**" in result
        assert "- List item 1" in result
        assert "code_block = True" in result

    def test_handles_nested_angle_brackets_in_content(self) -> None:
        """Should not strip angle brackets that aren't answer/suggested_actions tags."""
        content = "<answer>Use <tag> and </tag> in your code.</answer>"
        result = clean_proactivity_content(content)
        assert "<tag>" in result
        assert "</tag>" in result
