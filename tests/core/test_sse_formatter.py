"""Tests for SSE formatter utilities."""

import json

import pytest

from app.core.sse_formatter import (
    _validate_sse_format,
    extract_content_from_sse,
    format_sse_done,
    format_sse_event,
    is_done_event,
    is_valid_sse_event,
)
from app.schemas.chat import StreamResponse


class TestFormatSSEEvent:
    """Test format_sse_event function."""

    def test_format_basic_event(self):
        """Test formatting basic SSE event."""
        response = StreamResponse(content="Hello", done=False)
        result = format_sse_event(response)

        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        assert "Hello" in result
        assert "false" in result.lower()

    def test_format_event_with_empty_content(self):
        """Test formatting event with empty content."""
        response = StreamResponse(content="", done=False)
        result = format_sse_event(response)

        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        assert is_valid_sse_event(result)

    def test_format_event_preserves_special_chars(self):
        """Test that special characters are properly escaped in JSON."""
        response = StreamResponse(content='Test "quotes" and \\backslash', done=False)
        result = format_sse_event(response)

        assert is_valid_sse_event(result)
        content = extract_content_from_sse(result)
        assert content == 'Test "quotes" and \\backslash'

    def test_format_event_with_unicode(self):
        """Test formatting event with unicode characters."""
        response = StreamResponse(content="Àrticolo 42: Café ☕", done=False)
        result = format_sse_event(response)

        assert is_valid_sse_event(result)
        content = extract_content_from_sse(result)
        assert content == "Àrticolo 42: Café ☕"

    def test_format_event_done_flag(self):
        """Test formatting event with done flag."""
        response = StreamResponse(content="Final", done=True)
        result = format_sse_event(response)

        assert is_valid_sse_event(result)
        assert is_done_event(result)


class TestFormatSSEDone:
    """Test format_sse_done function."""

    def test_format_done_event(self):
        """Test formatting done event."""
        result = format_sse_done()

        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        assert is_valid_sse_event(result)
        assert is_done_event(result)

    def test_done_event_has_empty_content(self):
        """Test done event has empty content."""
        result = format_sse_done()
        content = extract_content_from_sse(result)

        assert content == ""

    def test_done_event_structure(self):
        """Test done event has correct structure."""
        result = format_sse_done()

        # Extract JSON
        json_str = result[len("data: ") : -2]
        data = json.loads(json_str)

        assert data["done"] is True
        assert data["content"] == ""


class TestValidateSSEFormat:
    """Test _validate_sse_format function."""

    def test_validate_correct_format(self):
        """Test validation passes for correct format."""
        event = 'data: {"content":"test","done":false}\n\n'
        _validate_sse_format(event)  # Should not raise

    def test_validate_missing_data_prefix(self):
        """Test validation fails without 'data: ' prefix."""
        event = '{"content":"test","done":false}\n\n'

        with pytest.raises(ValueError, match="must start with 'data: '"):
            _validate_sse_format(event)

    def test_validate_missing_trailing_newlines(self):
        """Test validation fails without trailing newlines."""
        event = 'data: {"content":"test","done":false}'

        with pytest.raises(ValueError, match="must end with exactly two newlines"):
            _validate_sse_format(event)

    def test_validate_single_trailing_newline(self):
        """Test validation fails with only one trailing newline."""
        event = 'data: {"content":"test","done":false}\n'

        with pytest.raises(ValueError, match="must end with exactly two newlines"):
            _validate_sse_format(event)

    def test_validate_invalid_json(self):
        """Test validation fails with invalid JSON."""
        event = "data: {invalid json}\n\n"

        with pytest.raises(ValueError, match="invalid JSON"):
            _validate_sse_format(event)

    def test_validate_json_missing_required_fields(self):
        """Test validation passes with missing optional fields (defaults used)."""
        # StreamResponse has default values, so this actually passes
        event = "data: {}\n\n"
        _validate_sse_format(event)  # Should not raise with defaults

    def test_validate_extra_fields_allowed(self):
        """Test validation passes with extra fields (ignored by pydantic)."""
        event = 'data: {"content":"test","done":false,"extra":"field"}\n\n'
        _validate_sse_format(event)  # Should not raise


class TestIsValidSSEEvent:
    """Test is_valid_sse_event function."""

    def test_valid_event_returns_true(self):
        """Test valid event returns True."""
        event = 'data: {"content":"test","done":false}\n\n'
        assert is_valid_sse_event(event) is True

    def test_invalid_prefix_returns_false(self):
        """Test invalid prefix returns False."""
        event = '{"content":"test","done":false}\n\n'
        assert is_valid_sse_event(event) is False

    def test_invalid_json_returns_false(self):
        """Test invalid JSON returns False."""
        event = "data: invalid\n\n"
        assert is_valid_sse_event(event) is False

    def test_missing_newlines_returns_false(self):
        """Test missing newlines returns False."""
        event = 'data: {"content":"test","done":false}'
        assert is_valid_sse_event(event) is False

    def test_empty_string_returns_false(self):
        """Test empty string returns False."""
        assert is_valid_sse_event("") is False


class TestExtractContentFromSSE:
    """Test extract_content_from_sse function."""

    def test_extract_simple_content(self):
        """Test extracting simple content."""
        event = 'data: {"content":"Hello World","done":false}\n\n'
        content = extract_content_from_sse(event)

        assert content == "Hello World"

    def test_extract_empty_content(self):
        """Test extracting empty content."""
        event = 'data: {"content":"","done":false}\n\n'
        content = extract_content_from_sse(event)

        assert content == ""

    def test_extract_unicode_content(self):
        """Test extracting unicode content."""
        event = 'data: {"content":"Testo italiano: è à ì","done":false}\n\n'
        content = extract_content_from_sse(event)

        assert content == "Testo italiano: è à ì"

    def test_extract_from_invalid_event_raises(self):
        """Test extraction from invalid event raises ValueError."""
        event = "invalid event"

        with pytest.raises(ValueError):
            extract_content_from_sse(event)

    def test_extract_escaped_content(self):
        """Test extracting content with escaped characters."""
        event = r'data: {"content":"Quote: \"Hello\"","done":false}' + "\n\n"
        content = extract_content_from_sse(event)

        assert content == 'Quote: "Hello"'


class TestIsDoneEvent:
    """Test is_done_event function."""

    def test_done_event_returns_true(self):
        """Test done event returns True."""
        event = 'data: {"content":"","done":true}\n\n'
        assert is_done_event(event) is True

    def test_non_done_event_returns_false(self):
        """Test non-done event returns False."""
        event = 'data: {"content":"test","done":false}\n\n'
        assert is_done_event(event) is False

    def test_comment_event_returns_false(self):
        """Test SSE comment (starting with :) returns False."""
        event = ": keepalive\n\n"
        assert is_done_event(event) is False

    def test_invalid_event_returns_false(self):
        """Test invalid event returns False."""
        event = "invalid"
        assert is_done_event(event) is False

    def test_malformed_json_returns_false(self):
        """Test malformed JSON returns False."""
        event = "data: {bad json}\n\n"
        assert is_done_event(event) is False

    def test_missing_done_field_returns_false(self):
        """Test missing done field returns False (defaults to False)."""
        event = 'data: {"content":"test"}\n\n'
        # This will fail validation, so should return False
        assert is_done_event(event) is False

    def test_done_with_content_returns_true(self):
        """Test done event with content returns True."""
        event = 'data: {"content":"Final message","done":true}\n\n'
        assert is_done_event(event) is True


class TestSSEIntegration:
    """Integration tests for SSE formatting workflow."""

    def test_format_and_validate_roundtrip(self):
        """Test formatting and validation roundtrip."""
        response = StreamResponse(content="Test", done=False)
        event = format_sse_event(response)

        assert is_valid_sse_event(event)
        assert extract_content_from_sse(event) == "Test"
        assert not is_done_event(event)

    def test_multiple_events_sequence(self):
        """Test sequence of multiple events."""
        events = [
            StreamResponse(content="First", done=False),
            StreamResponse(content="Second", done=False),
            StreamResponse(content="Third", done=True),
        ]

        formatted = [format_sse_event(e) for e in events]

        # All should be valid
        assert all(is_valid_sse_event(e) for e in formatted)

        # Only last should be done
        assert not is_done_event(formatted[0])
        assert not is_done_event(formatted[1])
        assert is_done_event(formatted[2])

    def test_done_event_workflow(self):
        """Test complete done event workflow."""
        done_event = format_sse_done()

        assert is_valid_sse_event(done_event)
        assert is_done_event(done_event)
        assert extract_content_from_sse(done_event) == ""
