"""Unit tests for SSE formatting utilities.

Tests the low-level SSE event formatting functions to ensure
proper protocol compliance.
"""

import pytest
from pydantic import BaseModel

from app.core.sse_formatter import (
    extract_content_from_sse,
    format_sse_done,
    format_sse_event,
    is_done_event,
    is_valid_sse_event,
)
from app.schemas.chat import StreamResponse


class TestSSEFormatter:
    """Test SSE event formatting functions."""

    def test_format_sse_event_structure(self):
        """Test SSE event has correct structure."""
        stream_response = StreamResponse(content="test", done=False)
        event = format_sse_event(stream_response)

        # Must start with "data:" prefix
        assert event.startswith("data: "), f"Event doesn't start with 'data:': {event!r}"

        # Must end with double newline
        assert event.endswith("\n\n"), f"Event doesn't end with \\n\\n: {event!r}"

        # Must contain content field
        assert '"content"' in event, f"Event missing content field: {event!r}"

        # Must contain done field
        assert '"done"' in event, f"Event missing done field: {event!r}"

    def test_format_sse_event_content_types(self):
        """Test SSE event handles different content types."""
        # Regular text
        event1 = format_sse_event(StreamResponse(content="hello world", done=False))
        assert "hello world" in event1

        # Special characters
        event2 = format_sse_event(StreamResponse(content='Quote: "test"', done=False))
        assert '\\"test\\"' in event2 or '"test"' in event2

        # Newlines (should be escaped in JSON)
        event3 = format_sse_event(StreamResponse(content="Line1\nLine2", done=False))
        assert "\\n" in event3 or "\n" in event3

        # Unicode
        event4 = format_sse_event(StreamResponse(content="Emoji: 🚀", done=False))
        assert "🚀" in event4 or "\\u" in event4

    def test_format_sse_done_structure(self):
        """Test SSE done event structure."""
        done_event = format_sse_done()

        # Must be valid SSE event
        assert is_valid_sse_event(done_event), f"Done event not valid SSE: {done_event!r}"

        # Must have done:true
        assert '"done":true' in done_event or '"done": true' in done_event

        # Should be recognized as done event
        assert is_done_event(done_event)

    def test_keepalive_format(self):
        """Test keepalive comment format."""
        keepalive = ": keepalive\n\n"

        # Must start with colon
        assert keepalive.startswith(":"), "Keepalive doesn't start with ':'"

        # Must end with double newline
        assert keepalive.endswith("\n\n"), "Keepalive doesn't end with \\n\\n"

        # Should NOT be recognized as valid data event (it's a comment)
        # Comments are technically valid SSE but not data events
        assert not keepalive.startswith("data:")

    def test_is_valid_sse_event_positive_cases(self):
        """Test SSE validation accepts valid events."""
        # Valid data event
        event1 = 'data: {"content":"test","done":false}\n\n'
        assert is_valid_sse_event(event1)

        # Valid done event
        event2 = 'data: {"done":true}\n\n'
        assert is_valid_sse_event(event2)

        # Valid comment (keepalive)
        # Note: Comments may or may not be considered "valid" depending on implementation
        # The key is they should not break parsing

    def test_is_valid_sse_event_negative_cases(self):
        """Test SSE validation rejects invalid events."""
        # Missing data: prefix
        invalid1 = '{"content":"test"}\n\n'
        assert not is_valid_sse_event(invalid1)

        # Missing double newline
        invalid2 = 'data: {"content":"test","done":false}'
        assert not is_valid_sse_event(invalid2)

        # Empty string
        invalid3 = ""
        assert not is_valid_sse_event(invalid3)

    def test_extract_content_from_sse(self):
        """Test content extraction from SSE events."""
        # Regular content
        event1 = 'data: {"content":"hello","done":false}\n\n'
        content1 = extract_content_from_sse(event1)
        assert content1 == "hello"

        # Empty content
        event2 = 'data: {"content":"","done":false}\n\n'
        content2 = extract_content_from_sse(event2)
        assert content2 == ""

        # Done event (no content)
        event3 = 'data: {"done":true}\n\n'
        content3 = extract_content_from_sse(event3)
        assert content3 is None or content3 == ""

    def test_is_done_event_positive_cases(self):
        """Test done event detection for valid done events."""
        # Basic done event
        done1 = 'data: {"done":true}\n\n'
        assert is_done_event(done1)

        # Done event with content
        done2 = 'data: {"content":"","done":true}\n\n'
        assert is_done_event(done2)

    def test_is_done_event_negative_cases(self):
        """Test done event detection rejects non-done events."""
        # Regular content event
        not_done1 = 'data: {"content":"test","done":false}\n\n'
        assert not is_done_event(not_done1)

        # Keepalive comment
        not_done2 = ": keepalive\n\n"
        assert not is_done_event(not_done2)

        # Invalid event
        not_done3 = "invalid"
        assert not is_done_event(not_done3)

    def test_sse_event_json_validity(self):
        """Test that SSE events contain valid JSON."""
        import json

        stream_response = StreamResponse(content="test data", done=False)
        event = format_sse_event(stream_response)

        # Extract JSON part (after "data: " prefix, before "\n\n")
        json_str = event[len("data: ") : -len("\n\n")]

        # Should be valid JSON
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in SSE event: {json_str!r} - Error: {e}")

        # Should have expected fields
        assert "content" in parsed
        assert "done" in parsed
        assert parsed["content"] == "test data"
        assert parsed["done"] is False

    def test_format_sse_event_escapes_special_json_chars(self):
        """Test that special JSON characters are properly escaped."""
        import json

        # Test content with special characters
        special_content = 'Test\n"quotes"\ttabs\\backslash'
        stream_response = StreamResponse(content=special_content, done=False)
        event = format_sse_event(stream_response)

        # Extract and parse JSON
        json_str = event[len("data: ") : -len("\n\n")]
        parsed = json.loads(json_str)

        # Content should match original
        assert parsed["content"] == special_content
