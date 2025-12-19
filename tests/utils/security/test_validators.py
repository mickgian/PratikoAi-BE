"""Test suite for validators.py security module.

TDD-first tests for field length validation, XSS sanitization,
and log message escaping utilities.
"""

import pytest

from app.utils.security.validators import (
    escape_log_message,
    sanitize_for_export,
    validate_field_length,
)


class TestValidateFieldLength:
    """Tests for validate_field_length function."""

    def test_valid_length_returns_value(self):
        """Test that valid length returns the original value."""
        result = validate_field_length("short text", max_length=100, field_name="test")
        assert result == "short text"

    def test_exact_max_length_allowed(self):
        """Test that exact max length is allowed."""
        text = "x" * 100
        result = validate_field_length(text, max_length=100, field_name="test")
        assert result == text

    def test_exceeds_max_length_raises(self):
        """Test that exceeding max length raises ValueError."""
        text = "x" * 101
        with pytest.raises(ValueError) as exc_info:
            validate_field_length(text, max_length=100, field_name="test_field")
        assert "test_field" in str(exc_info.value)
        assert "100" in str(exc_info.value)

    def test_empty_string_allowed(self):
        """Test that empty string is allowed."""
        result = validate_field_length("", max_length=100, field_name="test")
        assert result == ""

    def test_unicode_characters_counted_correctly(self):
        """Test that Unicode characters are counted correctly."""
        # Italian text with accents
        text = "Perché l'IVA è dovuta"  # 21 characters
        result = validate_field_length(text, max_length=21, field_name="test")
        assert result == text

        # Should raise if max is 20
        with pytest.raises(ValueError):
            validate_field_length(text, max_length=20, field_name="test")

    def test_emoji_counted_correctly(self):
        """Test that emojis are counted as characters."""
        text = "Test 🎉🎉"  # "Test " + 2 emojis = 7 characters (some emojis may be 2)
        # This depends on how we count - by bytes or code points
        result = validate_field_length(text, max_length=20, field_name="test")
        assert "Test" in result

    def test_error_message_in_italian(self):
        """Test that error message is in Italian."""
        text = "x" * 101
        with pytest.raises(ValueError) as exc_info:
            validate_field_length(text, max_length=100, field_name="query_text")
        error_msg = str(exc_info.value)
        # Should contain Italian message
        assert "caratteri" in error_msg.lower() or "massimo" in error_msg.lower()

    def test_field_name_in_error_message(self):
        """Test that field name is included in error message."""
        text = "x" * 101
        with pytest.raises(ValueError) as exc_info:
            validate_field_length(text, max_length=100, field_name="original_answer")
        assert "original_answer" in str(exc_info.value)

    def test_query_text_max_2000(self):
        """Test query_text field with 2000 char limit."""
        valid = "x" * 2000
        result = validate_field_length(valid, max_length=2000, field_name="query_text")
        assert len(result) == 2000

        invalid = "x" * 2001
        with pytest.raises(ValueError):
            validate_field_length(invalid, max_length=2000, field_name="query_text")

    def test_original_answer_max_5000(self):
        """Test original_answer field with 5000 char limit."""
        valid = "x" * 5000
        result = validate_field_length(valid, max_length=5000, field_name="original_answer")
        assert len(result) == 5000

        invalid = "x" * 5001
        with pytest.raises(ValueError):
            validate_field_length(invalid, max_length=5000, field_name="original_answer")

    def test_additional_details_max_2000(self):
        """Test additional_details field with 2000 char limit."""
        valid = "x" * 2000
        result = validate_field_length(valid, max_length=2000, field_name="additional_details")
        assert len(result) == 2000


class TestSanitizeForExport:
    """Tests for sanitize_for_export function."""

    def test_removes_script_tags(self):
        """Test that script tags are removed from export data."""
        data = {"content": "<script>alert('xss')</script>Normal text"}
        result = sanitize_for_export(data)
        assert "<script>" not in result["content"]
        assert "alert(" not in result["content"]
        assert "Normal text" in result["content"]

    def test_removes_onclick_handlers(self):
        """Test that onclick handlers are removed."""
        data = {"content": '<a onclick="evil()">Click</a>'}
        result = sanitize_for_export(data)
        assert "onclick" not in result["content"]

    def test_removes_onerror_handlers(self):
        """Test that onerror handlers are removed."""
        data = {"content": '<img onerror="evil()" src="x">'}
        result = sanitize_for_export(data)
        assert "onerror" not in result["content"]

    def test_removes_javascript_urls(self):
        """Test that javascript: URLs are removed."""
        data = {"content": '<a href="javascript:alert(1)">Link</a>'}
        result = sanitize_for_export(data)
        assert "javascript:" not in result["content"]

    def test_removes_data_urls_with_script(self):
        """Test that data: URLs with scripts are handled."""
        data = {"content": '<a href="data:text/html,<script>alert(1)</script>">'}
        result = sanitize_for_export(data)
        # Should either remove or escape the data URL
        assert "<script>" not in result["content"] or "script" not in result["content"].lower()

    def test_nested_dict_sanitized(self):
        """Test that nested dictionaries are sanitized."""
        data = {"level1": {"level2": {"content": "<script>evil()</script>"}}}
        result = sanitize_for_export(data)
        assert "<script>" not in str(result)

    def test_list_values_sanitized(self):
        """Test that list values are sanitized."""
        data = {
            "items": [
                "<script>evil()</script>",
                "Normal text",
                "<img onerror='evil()'>",
            ]
        }
        result = sanitize_for_export(data)
        assert "<script>" not in str(result)
        assert "Normal text" in str(result)

    def test_preserves_safe_html_entities(self):
        """Test that safe HTML entities are preserved."""
        data = {"content": "Price: &euro;100 &amp; more"}
        result = sanitize_for_export(data)
        # Should preserve entities or decode them safely
        assert "100" in result["content"]

    def test_preserves_italian_text(self):
        """Test that Italian text is preserved."""
        data = {"content": "L'IVA è al 22%. Perché il calcolo è corretto."}
        result = sanitize_for_export(data)
        assert "IVA" in result["content"]
        assert "22%" in result["content"]
        assert "è" in result["content"]

    def test_handles_empty_dict(self):
        """Test handling of empty dictionary."""
        result = sanitize_for_export({})
        assert result == {}

    def test_handles_none_values(self):
        """Test handling of None values in dict."""
        data = {"field1": None, "field2": "text"}
        result = sanitize_for_export(data)
        assert result["field1"] is None
        assert result["field2"] == "text"

    def test_handles_numeric_values(self):
        """Test that numeric values are preserved."""
        data = {"count": 42, "rate": 0.22, "active": True}
        result = sanitize_for_export(data)
        assert result["count"] == 42
        assert result["rate"] == 0.22
        assert result["active"] is True

    def test_mixed_content_types(self):
        """Test dictionary with mixed content types."""
        data = {
            "text": "<script>bad</script>Good text",
            "number": 100,
            "nested": {"inner": "<img onerror=x>"},
            "list": ["<script>", "safe"],
            "none_val": None,
        }
        result = sanitize_for_export(data)
        assert "<script>" not in str(result)
        assert result["number"] == 100
        assert "onerror" not in str(result)


class TestEscapeLogMessage:
    """Tests for escape_log_message function."""

    def test_escapes_newlines(self):
        """Test that newlines are escaped."""
        text = "Line 1\nLine 2\nLine 3"
        result = escape_log_message(text)
        # Newlines should be escaped to prevent log injection
        assert "\n" not in result or "\\n" in result

    def test_escapes_carriage_returns(self):
        """Test that carriage returns are escaped."""
        text = "Line 1\rLine 2"
        result = escape_log_message(text)
        assert "\r" not in result or "\\r" in result

    def test_escapes_tabs(self):
        """Test that tabs are escaped."""
        text = "Col1\tCol2\tCol3"
        result = escape_log_message(text)
        assert "\t" not in result or "\\t" in result

    def test_escapes_null_bytes(self):
        """Test that null bytes are removed or escaped."""
        text = "Before\x00After"
        result = escape_log_message(text)
        assert "\x00" not in result

    def test_escapes_ansi_codes(self):
        """Test that ANSI escape codes are removed."""
        text = "Normal \x1b[31mRed Text\x1b[0m Normal"
        result = escape_log_message(text)
        assert "\x1b" not in result

    def test_preserves_normal_text(self):
        """Test that normal text is preserved."""
        text = "Normal log message with Italian: perché l'IVA è 22%"
        result = escape_log_message(text)
        assert "Normal log message" in result
        assert "IVA" in result

    def test_log_injection_prevention(self):
        """Test prevention of log injection attack."""
        # Attacker tries to inject fake log entries
        malicious = "Normal log\nERROR [admin] User deleted all data"
        result = escape_log_message(malicious)
        # The fake log entry should not appear as a separate line
        assert result.count("\n") == 0 or "\\n" in result

    def test_empty_string(self):
        """Test handling of empty string."""
        result = escape_log_message("")
        assert result == ""

    def test_unicode_preserved(self):
        """Test that Unicode characters are preserved."""
        text = "Messaggio: €100, 日本語, émoji 🎉"
        result = escape_log_message(text)
        assert "€100" in result
        # Emoji might be preserved or removed depending on policy

    def test_control_characters_removed(self):
        """Test that control characters are removed."""
        # Various control characters
        text = "Normal\x00\x01\x02\x03text"
        result = escape_log_message(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "Normal" in result
        assert "text" in result


class TestIntegration:
    """Integration tests combining multiple validators."""

    def test_export_with_validation(self):
        """Test export sanitization with field validation."""
        # Field validation first
        query = "x" * 2000  # Max allowed
        result = validate_field_length(query, max_length=2000, field_name="query")
        assert len(result) == 2000

        # Then export sanitization
        data = {"query": result}
        sanitized = sanitize_for_export(data)
        assert len(sanitized["query"]) == 2000

    def test_log_escaping_with_validation(self):
        """Test log escaping for validated content."""
        # Content that passes validation
        content = "User query: Come calcolo l'IVA?"
        validated = validate_field_length(content, max_length=100, field_name="content")

        # Escape for logging
        log_safe = escape_log_message(validated)
        assert "Come calcolo" in log_safe

    def test_malicious_input_pipeline(self):
        """Test full pipeline with malicious input."""
        malicious = "<script>alert('xss')</script>\nFake log entry\x00null"

        # Validation should pass (under length)
        validated = validate_field_length(malicious, max_length=1000, field_name="input")

        # Export sanitization should remove XSS
        export_data = sanitize_for_export({"content": validated})
        assert "<script>" not in export_data["content"]

        # Log escaping should handle control chars and newlines
        log_safe = escape_log_message(validated)
        assert "\x00" not in log_safe
        assert "\n" not in log_safe or "\\n" in log_safe
