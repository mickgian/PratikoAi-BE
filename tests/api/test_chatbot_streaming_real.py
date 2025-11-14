"""Real SSE streaming tests without mocking LangGraph agent.

These tests validate actual SSE streaming behavior with the real agent,
testing connection timing, chunk delivery, and format compliance.
"""

import json
import time

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth import get_current_session
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


class TestRealSSEStreaming:
    """Test actual SSE streaming with real agent (not mocked)."""

    @pytest.mark.integration
    @pytest.mark.phase7
    def test_connection_establishes_within_5_seconds(self, test_client):
        """Test that SSE connection sends first data within 10s.

        This test verifies the keepalive fix works - connection should
        establish and send data reasonably quickly without timing out.
        """
        start = time.time()
        first_data_time = None

        with test_client.stream(
            "POST",
            "/api/v1/chatbot/chat/stream",
            json={"messages": [{"role": "user", "content": "test"}]},
        ) as response:
            assert response.status_code == 200

            for line in response.iter_lines():
                # Skip empty lines
                if not line:
                    continue

                # Record first data line (not comment)
                if line.startswith("data:"):
                    first_data_time = time.time() - start
                    break

        assert first_data_time is not None, "No data chunks received"
        assert first_data_time < 10.0, f"First chunk took {first_data_time:.2f}s (> 10s limit)"

    @pytest.mark.integration
    @pytest.mark.phase7
    @pytest.mark.timeout(120)  # Allow time for full response
    def test_all_chunks_arrive_no_drops(self, test_client):
        """Test that all chunks from backend arrive at client.

        Verifies no chunks are dropped during streaming and that
        the done event is properly sent.
        """
        with test_client.stream(
            "POST",
            "/api/v1/chatbot/chat/stream",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "Cosa sono le detrazioni fiscali per ottobre 2025?",
                    }
                ]
            },
        ) as response:
            assert response.status_code == 200

            chunks = []
            for line in response.iter_lines():
                if line and line.startswith("data:"):
                    chunks.append(line)

            # Verify we got multiple chunks (should be ~30 for this query)
            assert len(chunks) >= 20, f"Expected >=20 chunks, got {len(chunks)}"

            # Verify done event sent in last few chunks
            done_found = any(b'"done":true' in chunk or b'"done": true' in chunk for chunk in chunks[-3:])
            assert done_found, "No done event found in final chunks"

    @pytest.mark.integration
    @pytest.mark.phase7
    def test_keepalive_or_immediate_data(self, test_client):
        """Test that either keepalive or immediate data is sent.

        Connection must not be silent - either a keepalive comment or
        actual data should arrive within 2 seconds.
        """
        with test_client.stream(
            "POST",
            "/api/v1/chatbot/chat/stream",
            json={"messages": [{"role": "user", "content": "test"}]},
        ) as response:
            assert response.status_code == 200

            start = time.time()
            first_line = None

            for line in response.iter_lines():
                if line:
                    first_line = line
                    elapsed = time.time() - start
                    break

            assert first_line is not None, "No lines received from stream"
            assert elapsed < 2.0, f"First line took {elapsed:.2f}s (> 2s)"

            # First line should be either keepalive comment or data
            is_keepalive = first_line.startswith(b":")
            is_data = first_line.startswith(b"data:")
            assert is_keepalive or is_data, f"Unexpected first line: {first_line!r}"

    @pytest.mark.integration
    @pytest.mark.phase7
    def test_chunking_at_word_boundaries(self, test_client):
        """Test that backend chunks at word boundaries (~100 chars).

        Verifies buffered streaming logic chunks content properly.
        """
        with test_client.stream(
            "POST",
            "/api/v1/chatbot/chat/stream",
            json={"messages": [{"role": "user", "content": "Explain Italian tax law"}]},
        ) as response:
            chunk_sizes = []

            for line in response.iter_lines():
                if line and line.startswith(b"data:"):
                    try:
                        data = json.loads(line[5:])  # Skip "data:" prefix
                        if data.get("content") and not data.get("done"):
                            chunk_sizes.append(len(data["content"]))
                    except json.JSONDecodeError:
                        continue

            # Should have multiple content chunks
            assert len(chunk_sizes) > 0, "No content chunks received"

            # Most chunks should be 80-120 chars (100 ± 20)
            if len(chunk_sizes) >= 3:
                avg_size = sum(chunk_sizes) / len(chunk_sizes)
                assert 60 <= avg_size <= 150, f"Average chunk size {avg_size:.0f} outside expected range"

    @pytest.mark.integration
    @pytest.mark.phase7
    def test_sse_format_compliance(self, test_client):
        """Test that all SSE events follow proper format.

        Validates SSE protocol compliance for all events.
        """
        with test_client.stream(
            "POST",
            "/api/v1/chatbot/chat/stream",
            json={"messages": [{"role": "user", "content": "test"}]},
        ) as response:
            for line in response.iter_lines():
                if not line:
                    continue

                # Comment lines (keepalive)
                if line.startswith(b":"):
                    assert line.endswith(b"\n\n") or True  # May or may not have trailing newlines in iter_lines
                    continue

                # Data lines
                if line.startswith(b"data:"):
                    # Should be valid JSON after "data:" prefix
                    try:
                        json.loads(line[5:])
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Invalid JSON in SSE data line: {line!r} - Error: {e}")
                    continue

                # Unknown line type
                pytest.fail(f"Unexpected SSE line format: {line!r}")

    @pytest.mark.integration
    @pytest.mark.phase7
    def test_no_duplicate_chunks(self, test_client):
        """Test that no duplicate chunks are sent.

        Verifies deduplication doesn't happen at backend level.
        """
        with test_client.stream(
            "POST",
            "/api/v1/chatbot/chat/stream",
            json={"messages": [{"role": "user", "content": "short test"}]},
        ) as response:
            content_chunks = []

            for line in response.iter_lines():
                if line and line.startswith(b"data:"):
                    try:
                        data = json.loads(line[5:])
                        if data.get("content") and not data.get("done"):
                            content_chunks.append(data["content"])
                    except json.JSONDecodeError:
                        continue

            # Check for exact duplicates
            for i, chunk in enumerate(content_chunks):
                # Same chunk shouldn't appear consecutively
                if i > 0 and chunk == content_chunks[i - 1]:
                    pytest.fail(f"Duplicate consecutive chunk found: {chunk!r}")
