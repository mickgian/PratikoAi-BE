"""
Unit tests for SSE write helper with sampled logging.

Tests the write_sse() function and log_sse_summary() to verify:
- Frames pass through unchanged
- Logging is sampled correctly (first 5 chunks)
- Statistics are tracked accurately
- Summary logging works correctly
"""

import json
import logging
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from app.core.sse_write import (
    _write_stats,
    log_sse_summary,
    write_sse,
)


@pytest.fixture(autouse=True)
def clear_stats():
    """Clear _write_stats before each test to ensure isolation."""
    _write_stats.clear()
    yield
    _write_stats.clear()


class TestWriteSSE:
    """Test write_sse() frame pass-through and logging."""

    def test_frame_passthrough_unchanged(self):
        """Test that write_sse returns the frame unchanged."""
        frame = 'data: {"content":"Hello","done":false}\n\n'
        result = write_sse(None, frame, request_id="test-1")

        assert result == frame, "Frame must pass through unchanged"

    def test_sse_keepalive_passthrough(self):
        """Test that SSE keepalives pass through unchanged."""
        keepalive = ": starting\n\n"
        result = write_sse(None, keepalive, request_id="test-2")

        assert result == keepalive, "Keepalive must pass through unchanged"

    def test_statistics_tracking(self):
        """Test that write_sse tracks frame count and bytes."""
        frames = [
            'data: {"content":"A","done":false}\n\n',  # 39 bytes
            'data: {"content":"B","done":false}\n\n',  # 39 bytes
            'data: {"content":"C","done":false}\n\n',  # 39 bytes
        ]

        request_id = "test-stats"

        # Write 3 frames
        for frame in frames:
            write_sse(None, frame, request_id=request_id)

        # Check stats
        assert request_id in _write_stats
        stats = _write_stats[request_id]
        assert stats["count"] == 3, "Should track 3 frames"
        assert stats["total_bytes"] == sum(len(f) for f in frames)

    def test_default_request_id(self):
        """Test that default request_id is 'unknown' when not provided."""
        frame = 'data: {"content":"test","done":false}\n\n'
        write_sse(None, frame, request_id=None)

        # Should create stats for "unknown"
        assert "unknown" in _write_stats
        assert _write_stats["unknown"]["count"] == 1

    def test_multiple_request_ids_tracked_separately(self):
        """Test that different request IDs have separate statistics."""
        frame1 = 'data: {"content":"req1","done":false}\n\n'
        frame2 = 'data: {"content":"req2","done":false}\n\n'

        write_sse(None, frame1, request_id="request-1")
        write_sse(None, frame1, request_id="request-1")  # Second chunk for request-1
        write_sse(None, frame2, request_id="request-2")

        # Both requests should be tracked separately
        assert _write_stats["request-1"]["count"] == 2
        assert _write_stats["request-2"]["count"] == 1

    @patch("app.core.sse_write.logger")
    def test_logging_first_five_chunks(self, mock_logger):
        """Test that only first 5 chunks are logged at DEBUG level."""
        request_id = "test-sampling"

        # Write 7 chunks
        for i in range(7):
            frame = f'data: {{"content":"chunk{i}","done":false}}\n\n'
            write_sse(None, frame, request_id=request_id)

        # Should have logged exactly 5 DEBUG messages
        debug_calls = [call for call in mock_logger.debug.call_args_list]
        assert len(debug_calls) == 5, "Should log only first 5 chunks"

    @patch("app.core.sse_write.logger")
    def test_logging_parses_json_payload(self, mock_logger):
        """Test that logging extracts and logs JSON payload fields."""
        frame = 'data: {"content":"test","done":false,"seq":42}\n\n'
        write_sse(None, frame, request_id="test-json")

        # Should have called logger.debug with extracted fields
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0]

        # Check that seq field was extracted
        assert 42 in call_args, "Should extract seq field from JSON"

    @patch("app.core.sse_write.logger")
    def test_logging_handles_non_json_frames(self, mock_logger):
        """Test that logging handles non-JSON frames gracefully."""
        frame = ": keepalive\n\n"
        write_sse(None, frame, request_id="test-non-json")

        # Should log without crashing
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0]

        # Should mention raw_frame_len
        assert "raw_frame_len" in call_args[0]

    @patch("app.core.sse_write.logger")
    def test_logging_handles_malformed_json(self, mock_logger):
        """Test that logging handles malformed JSON without crashing."""
        frame = "data: {invalid json}\n\n"
        write_sse(None, frame, request_id="test-malformed")

        # Should log with (unparsed) marker
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0]
        assert "(unparsed)" in call_args[0] or "raw_frame_len" in call_args[0]


class TestLogSSESummary:
    """Test log_sse_summary() aggregated statistics logging."""

    @patch("app.core.sse_write.logger")
    def test_summary_logs_statistics(self, mock_logger):
        """Test that summary logs total chunks, bytes, and average."""
        request_id = "test-summary"

        # Write 3 frames
        frames = [
            'data: {"content":"A","done":false}\n\n',
            'data: {"content":"B","done":false}\n\n',
            'data: {"content":"C","done":false}\n\n',
        ]
        for frame in frames:
            write_sse(None, frame, request_id=request_id)

        # Call summary
        log_sse_summary(request_id=request_id)

        # Should have logged summary at INFO level
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0]

        # Check summary contains expected data
        assert "SSE_SUMMARY" in call_args[0]
        assert "total_chunks=3" in call_args[0] or 3 in call_args

    @patch("app.core.sse_write.logger")
    def test_summary_calculates_average_chunk_size(self, mock_logger):
        """Test that summary calculates correct average chunk size."""
        request_id = "test-avg"

        # Write 2 frames with known sizes
        frame1 = "A" * 100  # 100 bytes
        frame2 = "B" * 200  # 200 bytes
        write_sse(None, frame1, request_id=request_id)
        write_sse(None, frame2, request_id=request_id)

        log_sse_summary(request_id=request_id)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0]

        # Average should be (100 + 200) / 2 = 150.0
        assert 150.0 in call_args or "150" in str(call_args)

    @patch("app.core.sse_write.logger")
    def test_summary_clears_stats_after_logging(self, mock_logger):
        """Test that summary clears stats after logging to prevent memory leak."""
        request_id = "test-cleanup"

        # Write frame
        write_sse(None, "test", request_id=request_id)

        # Stats should exist before summary
        assert request_id in _write_stats

        # Call summary
        log_sse_summary(request_id=request_id)

        # Stats should be cleared after summary
        assert request_id not in _write_stats

    @patch("app.core.sse_write.logger")
    def test_summary_handles_nonexistent_request_id(self, mock_logger):
        """Test that summary handles request_id that doesn't exist."""
        # Call summary for nonexistent request
        log_sse_summary(request_id="nonexistent")

        # Should not crash, should not log anything
        mock_logger.info.assert_not_called()

    @patch("app.core.sse_write.logger")
    def test_summary_handles_default_request_id(self, mock_logger):
        """Test that summary uses 'unknown' as default request_id."""
        # Write frame with no request_id
        write_sse(None, "test", request_id=None)

        # Summary with no request_id should find "unknown"
        log_sse_summary(request_id=None)

        mock_logger.info.assert_called_once()


class TestWriteSSEThreadSafety:
    """Test thread safety of write_sse and statistics tracking."""

    def test_concurrent_writes_tracked_correctly(self):
        """
        Test that concurrent writes from different requests are tracked separately.

        While not using actual threading, this documents the thread-safe design.
        """
        # Simulate concurrent writes from 3 different requests
        requests = ["req-1", "req-2", "req-3"]

        for _ in range(10):
            for req_id in requests:
                frame = f'data: {{"content":"test","done":false}}\n\n'
                write_sse(None, frame, request_id=req_id)

        # Each request should have 10 chunks tracked
        for req_id in requests:
            assert _write_stats[req_id]["count"] == 10

    def test_statistics_isolation(self):
        """Test that statistics for different requests don't interfere."""
        # Write different amount of data for each request
        write_sse(None, "A" * 100, request_id="req-1")  # 100 bytes
        write_sse(None, "B" * 200, request_id="req-2")  # 200 bytes
        write_sse(None, "C" * 300, request_id="req-3")  # 300 bytes

        # Each should have correct isolated stats
        assert _write_stats["req-1"]["total_bytes"] == 100
        assert _write_stats["req-2"]["total_bytes"] == 200
        assert _write_stats["req-3"]["total_bytes"] == 300


class TestWriteSSERegressionProtection:
    """Regression tests for specific bugs."""

    def test_frame_not_modified_during_logging(self):
        """
        Regression: Ensure frame content is never modified during logging.

        Critical for streaming integrity - logging must be side-effect free.
        """
        original_frame = 'data: {"content":"Critical content","done":false}\n\n'
        returned_frame = write_sse(None, original_frame, request_id="test")

        # Must be identical
        assert returned_frame == original_frame
        assert returned_frame is original_frame or returned_frame == original_frame

    def test_stats_tracking_doesnt_affect_output(self):
        """
        Regression: Ensure statistics tracking doesn't affect streamed output.
        """
        frames_in = [f"frame-{i}" for i in range(10)]
        frames_out = []

        for frame in frames_in:
            result = write_sse(None, frame, request_id="test")
            frames_out.append(result)

        # Output must match input exactly
        assert frames_out == frames_in

    def test_malformed_json_handled_gracefully(self):
        """
        Regression: Ensure malformed JSON in frames doesn't crash write_sse.

        The function should handle malformed JSON in the exception handler
        and log with (unparsed) marker.
        """
        # Malformed JSON - missing quotes
        frame = "data: {content:test,done:false}\n\n"

        # Should not raise during normal processing
        result = write_sse(None, frame, request_id="test")

        # Frame should pass through unchanged despite malformed JSON
        assert result == frame
