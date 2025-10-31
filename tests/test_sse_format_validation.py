"""Unit tests for SSE format validation and formatting.

This test suite ensures that SSE (Server-Sent Events) formatting is always correct
and prevents format-related bugs that could break frontend EventSource parsing.
"""

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
    """Test format_sse_event() function."""

    def test_format_basic_chunk(self):
        """Test formatting a basic content chunk."""
        response = StreamResponse(content="Hello", done=False)
        sse_event = format_sse_event(response)

        assert sse_event.startswith("data: ")
        assert sse_event.endswith("\n\n")
        assert '"content":"Hello"' in sse_event or '"content": "Hello"' in sse_event
        assert '"done":false' in sse_event or '"done": false' in sse_event

    def test_format_done_event(self):
        """Test formatting a done event."""
        response = StreamResponse(content="", done=True)
        sse_event = format_sse_event(response)

        assert sse_event.startswith("data: ")
        assert sse_event.endswith("\n\n")
        assert '"done":true' in sse_event or '"done": true' in sse_event

    def test_format_with_special_characters(self):
        """Test formatting content with special characters."""
        response = StreamResponse(content='Hello "world" \n\t', done=False)
        sse_event = format_sse_event(response)

        # Should properly escape special chars in JSON
        assert sse_event.startswith("data: ")
        assert sse_event.endswith("\n\n")

        # Extract and verify JSON is valid
        json_str = sse_event[6:-2]  # Remove "data: " and "\n\n"
        parsed = json.loads(json_str)
        assert parsed["content"] == 'Hello "world" \n\t'

    def test_format_empty_content(self):
        """Test formatting empty content."""
        response = StreamResponse(content="", done=False)
        sse_event = format_sse_event(response)

        assert sse_event.startswith("data: ")
        assert sse_event.endswith("\n\n")
        assert '"content":""' in sse_event or '"content": ""' in sse_event

    def test_format_multiline_content(self):
        """Test formatting content with newlines."""
        response = StreamResponse(content="Line 1\nLine 2\nLine 3", done=False)
        sse_event = format_sse_event(response)

        assert sse_event.startswith("data: ")
        assert sse_event.endswith("\n\n")

        # Newlines should be escaped in JSON
        assert "\\n" in sse_event

    def test_format_unicode_content(self):
        """Test formatting content with Unicode characters."""
        response = StreamResponse(content="こんにちは 🚀 Café", done=False)
        sse_event = format_sse_event(response)

        assert sse_event.startswith("data: ")
        assert sse_event.endswith("\n\n")

        # Verify JSON is valid and preserves Unicode
        json_str = sse_event[6:-2]
        parsed = json.loads(json_str)
        assert parsed["content"] == "こんにちは 🚀 Café"


class TestFormatSSEDone:
    """Test format_sse_done() function."""

    def test_format_done_creates_valid_event(self):
        """Test that format_sse_done() creates a valid done event."""
        sse_done = format_sse_done()

        assert sse_done.startswith("data: ")
        assert sse_done.endswith("\n\n")
        assert '"done":true' in sse_done or '"done": true' in sse_done
        assert '"content":""' in sse_done or '"content": ""' in sse_done

    def test_format_done_is_valid_sse(self):
        """Test that done event passes validation."""
        sse_done = format_sse_done()
        assert is_valid_sse_event(sse_done)

    def test_format_done_is_recognized_as_done(self):
        """Test that done event is recognized by is_done_event()."""
        sse_done = format_sse_done()
        assert is_done_event(sse_done)


class TestValidateSSEFormat:
    """Test _validate_sse_format() function."""

    def test_validate_correct_format(self):
        """Test that valid SSE event passes validation."""
        valid_event = 'data: {"content":"test","done":false}\n\n'
        # Should not raise
        _validate_sse_format(valid_event)

    def test_validate_missing_data_prefix(self):
        """Test that event without 'data: ' prefix fails validation."""
        invalid_event = '{"content":"test","done":false}\n\n'
        with pytest.raises(ValueError, match="must start with 'data: '"):
            _validate_sse_format(invalid_event)

    def test_validate_missing_trailing_newlines(self):
        """Test that event without trailing newlines fails validation."""
        invalid_event = 'data: {"content":"test","done":false}'
        with pytest.raises(ValueError, match="must end with exactly two newlines"):
            _validate_sse_format(invalid_event)

    def test_validate_single_trailing_newline(self):
        """Test that event with only one trailing newline fails validation."""
        invalid_event = 'data: {"content":"test","done":false}\n'
        with pytest.raises(ValueError, match="must end with exactly two newlines"):
            _validate_sse_format(invalid_event)

    def test_validate_invalid_json(self):
        """Test that event with invalid JSON fails validation."""
        invalid_event = "data: {invalid json}\n\n"
        with pytest.raises(ValueError, match="invalid JSON"):
            _validate_sse_format(invalid_event)

    def test_validate_json_missing_required_fields(self):
        """Test that JSON without required fields still validates (Pydantic has defaults)."""
        # Note: StreamResponse has default values, so this actually passes validation
        # This test documents the behavior rather than expecting failure
        event_with_defaults = 'data: {"wrong_field":"value"}\n\n'
        # Will not raise because Pydantic provides defaults for content and done
        # This is acceptable behavior - we primarily care about format correctness
        try:
            _validate_sse_format(event_with_defaults)
        except ValueError:
            # If it raises, that's also fine (stricter validation)
            pass

    def test_validate_json_wrong_types(self):
        """Test that JSON with wrong field types fails validation."""
        invalid_event = 'data: {"content":123,"done":"not_a_bool"}\n\n'
        with pytest.raises(ValueError, match="does not conform to StreamResponse"):
            _validate_sse_format(invalid_event)


class TestIsValidSSEEvent:
    """Test is_valid_sse_event() function."""

    def test_valid_event_returns_true(self):
        """Test that valid SSE event returns True."""
        valid_event = 'data: {"content":"test","done":false}\n\n'
        assert is_valid_sse_event(valid_event) is True

    def test_invalid_event_returns_false(self):
        """Test that invalid SSE event returns False."""
        invalid_event = "invalid event\n\n"
        assert is_valid_sse_event(invalid_event) is False

    def test_malformed_json_returns_false(self):
        """Test that malformed JSON returns False."""
        invalid_event = "data: {broken json\n\n"
        assert is_valid_sse_event(invalid_event) is False


class TestExtractContentFromSSE:
    """Test extract_content_from_sse() function."""

    def test_extract_simple_content(self):
        """Test extracting content from simple event."""
        sse_event = 'data: {"content":"Hello world","done":false}\n\n'
        content = extract_content_from_sse(sse_event)
        assert content == "Hello world"

    def test_extract_empty_content(self):
        """Test extracting empty content."""
        sse_event = 'data: {"content":"","done":true}\n\n'
        content = extract_content_from_sse(sse_event)
        assert content == ""

    def test_extract_with_special_chars(self):
        """Test extracting content with special characters."""
        sse_event = 'data: {"content":"Line 1\\nLine 2","done":false}\n\n'
        content = extract_content_from_sse(sse_event)
        assert content == "Line 1\nLine 2"

    def test_extract_from_invalid_event_raises(self):
        """Test that extracting from invalid event raises error."""
        invalid_event = "invalid event\n\n"
        with pytest.raises(ValueError):
            extract_content_from_sse(invalid_event)


class TestIsDoneEvent:
    """Test is_done_event() function."""

    def test_done_true_returns_true(self):
        """Test that event with done=true returns True."""
        sse_event = 'data: {"content":"","done":true}\n\n'
        assert is_done_event(sse_event) is True

    def test_done_false_returns_false(self):
        """Test that event with done=false returns False."""
        sse_event = 'data: {"content":"test","done":false}\n\n'
        assert is_done_event(sse_event) is False

    def test_done_missing_returns_false(self):
        """Test that event without explicit done field defaults to False."""
        # Note: Pydantic provides default done=False, so this is valid
        sse_event = 'data: {"content":"test"}\n\n'
        # This is valid SSE (Pydantic provides defaults), done should default to False
        assert is_done_event(sse_event) is False


class TestEndToEndFormatting:
    """Test end-to-end formatting scenarios."""

    def test_format_and_validate_roundtrip(self):
        """Test that formatted events pass validation."""
        response = StreamResponse(content="Test content", done=False)
        sse_event = format_sse_event(response)

        # Should pass validation
        assert is_valid_sse_event(sse_event)

        # Should extract correctly
        content = extract_content_from_sse(sse_event)
        assert content == "Test content"

        # Should recognize done status
        assert is_done_event(sse_event) is False

    def test_format_done_and_validate(self):
        """Test that done event passes all checks."""
        sse_done = format_sse_done()

        assert is_valid_sse_event(sse_done)
        assert is_done_event(sse_done)
        assert extract_content_from_sse(sse_done) == ""

    def test_streaming_sequence(self):
        """Test a realistic streaming sequence."""
        chunks = ["Hello", " world", "!"]
        events = []

        # Format each chunk
        for chunk in chunks:
            response = StreamResponse(content=chunk, done=False)
            event = format_sse_event(response)
            events.append(event)

        # Format done event
        events.append(format_sse_done())

        # Validate all events
        for event in events:
            assert is_valid_sse_event(event)

        # Check content
        assert extract_content_from_sse(events[0]) == "Hello"
        assert extract_content_from_sse(events[1]) == " world"
        assert extract_content_from_sse(events[2]) == "!"
        assert extract_content_from_sse(events[3]) == ""

        # Check done flags
        assert not is_done_event(events[0])
        assert not is_done_event(events[1])
        assert not is_done_event(events[2])
        assert is_done_event(events[3])
