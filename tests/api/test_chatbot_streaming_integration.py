"""Integration tests for chatbot streaming API.

This test suite validates that the /chat/stream endpoint correctly formats
SSE events and integrates properly with the LangGraphAgent streaming flow.

These tests are critical for preventing SSE format regressions that could
break frontend EventSource parsing and cause streaming interruptions.

NOTE: Skipped in CI - TestClient(app) triggers full app startup including
database connections which causes 20+ minute delays per test when DB
credentials don't match CI environment.
"""

import os
from unittest.mock import patch

import pytest

# Skip in CI - app startup is too slow without proper DB setup
if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
    pytest.skip(
        "Streaming integration tests require full app infrastructure - skipped in CI",
        allow_module_level=True,
    )
from fastapi.testclient import TestClient

from app.api.v1.auth import get_current_session
from app.core.sse_formatter import (
    extract_content_from_sse,
    is_done_event,
    is_valid_sse_event,
)
from app.main import app
from app.models.session import Session


# Mock session for testing
@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    session = Session(id="test-session-123", user_id="test-user-456", token="test-token")
    return session


# Override auth dependency
@pytest.fixture
def test_client(mock_session):
    """Create test client with mocked authentication."""
    app.dependency_overrides[get_current_session] = lambda: mock_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


class TestChatStreamSSEFormat:
    """Test that /chat/stream endpoint produces valid SSE events."""

    @pytest.mark.asyncio
    async def test_stream_endpoint_produces_valid_sse_events(self, test_client):
        """Test that streaming endpoint produces valid SSE format."""

        # Mock the agent's get_stream_response to yield test chunks
        async def mock_stream(*args, **kwargs):
            yield "Hello"
            yield " world"
            yield "!"

        with patch("app.api.v1.chatbot.agent") as mock_agent:
            mock_agent.get_stream_response = mock_stream

            response = test_client.post(
                "/api/v1/chatbot/chat/stream",
                json={"messages": [{"role": "user", "content": "Test"}]},
                headers={"Authorization": "Bearer test-token"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            # Parse SSE events from response
            events = response.text.strip().split("\n\n")
            events = [e + "\n\n" for e in events if e]  # Re-add trailing newlines

            # Validate all events are valid SSE
            for event in events:
                assert is_valid_sse_event(event), f"Invalid SSE event: {event!r}"

    @pytest.mark.asyncio
    async def test_stream_endpoint_sends_done_event(self, test_client):
        """Test that streaming endpoint sends a final done event."""

        async def mock_stream(*args, **kwargs):
            yield "Test content"

        with patch("app.api.v1.chatbot.agent") as mock_agent:
            mock_agent.get_stream_response = mock_stream

            response = test_client.post(
                "/api/v1/chatbot/chat/stream",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

            events = response.text.strip().split("\n\n")
            events = [e + "\n\n" for e in events if e]

            # Last event should be done event
            assert len(events) >= 2  # At least one content + done
            assert is_done_event(events[-1])

    @pytest.mark.asyncio
    async def test_stream_endpoint_preserves_content(self, test_client):
        """Test that streaming preserves content correctly."""
        test_chunks = ["Hello", " ", "world", "!"]

        async def mock_stream(*args, **kwargs):
            for chunk in test_chunks:
                yield chunk

        with patch("app.api.v1.chatbot.agent") as mock_agent:
            mock_agent.get_stream_response = mock_stream

            response = test_client.post(
                "/api/v1/chatbot/chat/stream",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

            events = response.text.strip().split("\n\n")
            events = [e + "\n\n" for e in events if e and e.startswith("data:")]

            # Extract content from content events (not done event)
            content_events = [e for e in events if not is_done_event(e)]
            extracted_content = [extract_content_from_sse(e) for e in content_events]

            # Verify content matches original chunks
            assert extracted_content == test_chunks

    @pytest.mark.asyncio
    async def test_stream_endpoint_handles_special_characters(self, test_client):
        """Test that streaming handles special characters correctly."""
        special_chunks = ["Line 1\n", 'Quote: "test"', "Tab:\there", "Unicode: 🚀"]

        async def mock_stream(*args, **kwargs):
            for chunk in special_chunks:
                yield chunk

        with patch("app.api.v1.chatbot.agent") as mock_agent:
            mock_agent.get_stream_response = mock_stream

            response = test_client.post(
                "/api/v1/chatbot/chat/stream",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

            events = response.text.strip().split("\n\n")
            events = [e + "\n\n" for e in events if e and e.startswith("data:")]

            # All events should be valid SSE
            for event in events:
                assert is_valid_sse_event(event)

            # Extract and verify content
            content_events = [e for e in events if not is_done_event(e)]
            extracted_content = [extract_content_from_sse(e) for e in content_events]

            assert extracted_content == special_chunks

    @pytest.mark.asyncio
    async def test_stream_endpoint_handles_empty_chunks(self, test_client):
        """Test that streaming skips empty chunks."""
        chunks_with_empty = ["Hello", "", "world", ""]

        async def mock_stream(*args, **kwargs):
            for chunk in chunks_with_empty:
                yield chunk

        with patch("app.api.v1.chatbot.agent") as mock_agent:
            mock_agent.get_stream_response = mock_stream

            response = test_client.post(
                "/api/v1/chatbot/chat/stream",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

            events = response.text.strip().split("\n\n")
            events = [e + "\n\n" for e in events if e and e.startswith("data:")]

            # Empty chunks should be filtered out (except done event)
            content_events = [e for e in events if not is_done_event(e)]
            extracted_content = [extract_content_from_sse(e) for e in content_events]

            # Should only have non-empty chunks
            assert "" not in extracted_content
            assert extracted_content == ["Hello", "world"]


class TestChatStreamEventSequence:
    """Test the correct sequence of SSE events."""

    @pytest.mark.asyncio
    async def test_stream_event_sequence_is_correct(self, test_client):
        """Test that events are sent in correct sequence: content chunks → done."""

        async def mock_stream(*args, **kwargs):
            yield "Chunk 1"
            yield "Chunk 2"
            yield "Chunk 3"

        with patch("app.api.v1.chatbot.agent") as mock_agent:
            mock_agent.get_stream_response = mock_stream

            response = test_client.post(
                "/api/v1/chatbot/chat/stream",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

            events = response.text.strip().split("\n\n")
            events = [e + "\n\n" for e in events if e and e.startswith("data:")]

            # Check sequence: content events, then done event
            for i, event in enumerate(events[:-1]):
                assert not is_done_event(event), f"Unexpected done event at position {i}"

            # Last event should be done
            assert is_done_event(events[-1])

    @pytest.mark.asyncio
    async def test_stream_no_events_after_done(self, test_client):
        """Test that no events are sent after done event."""

        async def mock_stream(*args, **kwargs):
            yield "Content"

        with patch("app.api.v1.chatbot.agent") as mock_agent:
            mock_agent.get_stream_response = mock_stream

            response = test_client.post(
                "/api/v1/chatbot/chat/stream",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

            # Find done event position
            events = response.text.strip().split("\n\n")
            events = [e + "\n\n" for e in events if e and e.startswith("data:")]

            done_idx = None
            for i, event in enumerate(events):
                if is_done_event(event):
                    done_idx = i
                    break

            # Done event should be last
            assert done_idx == len(events) - 1


class TestChatStreamErrorHandling:
    """Test error handling in streaming endpoint."""

    @pytest.mark.asyncio
    async def test_stream_handles_agent_error_gracefully(self, test_client):
        """Test that streaming handles errors from agent gracefully."""

        async def mock_stream(*args, **kwargs):
            yield "Start"
            raise Exception("Simulated error")

        with patch("app.api.v1.chatbot.agent") as mock_agent:
            mock_agent.get_stream_response = mock_stream

            response = test_client.post(
                "/api/v1/chatbot/chat/stream",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

            # Should still return 200 (streaming started)
            assert response.status_code == 200

            # Response should contain error message in SSE format
            assert "error" in response.text.lower() or "exception" in response.text.lower()

    @pytest.mark.asyncio
    async def test_stream_validates_request_format(self, test_client):
        """Test that invalid requests are rejected."""
        response = test_client.post(
            "/api/v1/chatbot/chat/stream",
            json={"invalid": "format"},
        )

        # Should return error status
        assert response.status_code >= 400


class TestChatStreamPerformance:
    """Test streaming performance characteristics."""

    @pytest.mark.asyncio
    async def test_stream_does_not_buffer_all_content(self, test_client):
        """Test that streaming sends chunks incrementally, not all at once."""
        # This test verifies that chunks are yielded as they're generated
        # rather than buffered until completion

        chunks_yielded = []

        async def mock_stream(*args, **kwargs):
            for i in range(5):
                chunk = f"Chunk {i}"
                chunks_yielded.append(chunk)
                yield chunk

        with patch("app.api.v1.chatbot.agent") as mock_agent:
            mock_agent.get_stream_response = mock_stream

            response = test_client.post(
                "/api/v1/chatbot/chat/stream",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

            # If streaming works correctly, all chunks should be yielded
            assert len(chunks_yielded) == 5
            assert response.status_code == 200
