#!/usr/bin/env python3
"""
Tests for RAG STEP 110 — Send DONE frame

This step sends DONE frame to terminate streaming responses properly.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.orchestrators.platform import step_110__send_done


class TestRAGStep110SendDone:
    """Test suite for RAG STEP 110 - Send DONE frame"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_sse_done_frame(self, mock_logger, mock_rag_log):
        """Test Step 110: Send SSE DONE frame"""

        # Mock stream writer
        stream_writer = MagicMock()
        stream_writer.write = MagicMock()
        stream_writer.drain = MagicMock()

        ctx = {
            "stream_writer": stream_writer,
            "streaming_format": "sse",
            "client_connected": True,
            "chunks_sent": 10,
            "total_bytes": 1024,
            "stream_id": "test-stream-123",
        }

        # Call the orchestrator function
        result = step_110__send_done(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["streaming_format"] == "sse"
        assert result["done_sent"] is True
        assert result["chunks_sent"] == 10
        assert result["total_bytes"] == 1024
        assert result["stream_id"] == "test-stream-123"
        assert "timestamp" in result

        # Verify SSE DONE frame was written
        stream_writer.write.assert_called_once()
        written_data = stream_writer.write.call_args[0][0]
        assert written_data == b"data: [DONE]\n\n"

        # Verify drain was called (if available)
        stream_writer.drain.assert_called_once()

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "DONE frame sent" in log_call[0][0]
        assert log_call[1]["extra"]["streaming_event"] == "done_frame_sent"
        assert log_call[1]["extra"]["done_sent"] is True

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]
        assert len(completed_logs) > 0
        completed_log = completed_logs[0]
        assert completed_log[1]["step"] == 110
        assert completed_log[1]["streaming_event"] == "done_frame_sent"
        assert completed_log[1]["done_sent"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_websocket_done_frame(self, mock_logger, mock_rag_log):
        """Test Step 110: Send WebSocket DONE frame"""

        # Mock stream writer with send method (WebSocket-style)
        stream_writer = MagicMock()
        stream_writer.send = MagicMock()

        ctx = {
            "stream_writer": stream_writer,
            "streaming_format": "websocket",
            "chunks_sent": 5,
            "client_connected": True,
        }

        # Call the orchestrator function
        result = step_110__send_done(ctx=ctx)

        # Verify WebSocket DONE frame was sent
        assert result["done_sent"] is True
        stream_writer.send.assert_called_once()
        sent_data = stream_writer.send.call_args[0][0]
        assert '"type": "done"' in sent_data
        assert '"timestamp"' in sent_data

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_generic_done_frame(self, mock_logger, mock_rag_log):
        """Test Step 110: Send generic DONE frame"""

        stream_writer = MagicMock()
        stream_writer.write = MagicMock()

        ctx = {"stream_writer": stream_writer, "streaming_format": "generic", "chunks_sent": 8}

        # Call the orchestrator function
        result = step_110__send_done(ctx=ctx)

        # Verify generic DONE frame was written
        assert result["done_sent"] is True
        stream_writer.write.assert_called_once()
        written_data = stream_writer.write.call_args[0][0]
        assert written_data == b"\n[DONE]\n"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_response_generator(self, mock_logger, mock_rag_log):
        """Test Step 110: Send DONE frame via response generator"""

        # Mock response generator
        response_generator = MagicMock()
        response_generator.send = MagicMock()

        ctx = {"response_generator": response_generator, "streaming_format": "sse", "chunks_sent": 3}

        # Call the orchestrator function
        result = step_110__send_done(ctx=ctx)

        # Verify DONE frame was sent via generator
        assert result["done_sent"] is True
        response_generator.send.assert_called_once()
        sent_data = response_generator.send.call_args[0][0]
        assert sent_data == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_generator_exception(self, mock_logger, mock_rag_log):
        """Test Step 110: Handle generator exceptions gracefully"""

        # Mock response generator that raises StopIteration
        response_generator = MagicMock()
        response_generator.send = MagicMock(side_effect=StopIteration())

        ctx = {"response_generator": response_generator, "streaming_format": "sse"}

        # Call the orchestrator function
        result = step_110__send_done(ctx=ctx)

        # Should still mark as sent (generator is closed)
        assert result["done_sent"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_no_stream_writer(self, mock_logger, mock_rag_log):
        """Test Step 110: Handle missing stream writer (testing scenario)"""

        ctx = {"streaming_format": "sse", "chunks_sent": 2}

        # Call the orchestrator function
        result = step_110__send_done(ctx=ctx)

        # Should still mark as sent for testing scenarios
        assert result["done_sent"] is True
        assert result["streaming_format"] == "sse"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_stream_write_error(self, mock_logger, mock_rag_log):
        """Test Step 110: Handle stream write errors gracefully"""

        # Mock stream writer that raises exception
        stream_writer = MagicMock()
        stream_writer.write = MagicMock(side_effect=ConnectionError("Connection lost"))

        ctx = {"stream_writer": stream_writer, "streaming_format": "sse"}

        # Call the orchestrator function
        result = step_110__send_done(ctx=ctx)

        # Should handle error gracefully
        assert result["done_sent"] is False
        assert "error" in result
        assert "Connection lost" in result["error"]

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert "Failed to send DONE frame" in warning_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_async_drain(self, mock_logger, mock_rag_log):
        """Test Step 110: Handle async drain method gracefully"""

        # Mock stream writer with async drain method
        async def async_drain():
            pass

        stream_writer = MagicMock()
        stream_writer.write = MagicMock()
        stream_writer.drain = MagicMock()
        stream_writer.drain.__await__ = async_drain().__await__

        ctx = {"stream_writer": stream_writer, "streaming_format": "sse"}

        # Call the orchestrator function
        result = step_110__send_done(ctx=ctx)

        # Should handle async drain without awaiting
        assert result["done_sent"] is True
        stream_writer.write.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 110: Handle empty context gracefully"""

        # Call with minimal context
        result = step_110__send_done()

        # Verify defaults are used
        assert isinstance(result, dict)
        assert result["streaming_format"] == "sse"  # Default format
        assert result["chunks_sent"] == 0
        assert result["total_bytes"] == 0
        assert result["client_connected"] is True
        assert result["done_sent"] is True  # No writer, so marked as sent

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 110: Parameters passed via kwargs"""

        stream_writer = MagicMock()
        stream_writer.write = MagicMock()

        # Call with kwargs instead of ctx
        result = step_110__send_done(
            stream_writer=stream_writer, streaming_format="sse", chunks_sent=15, total_bytes=2048
        )

        # Verify kwargs are processed correctly
        assert result["streaming_format"] == "sse"
        assert result["chunks_sent"] == 15
        assert result["total_bytes"] == 2048
        assert result["done_sent"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 110: Performance tracking with timer"""

        with patch("app.orchestrators.platform.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            step_110__send_done(ctx={"streaming_format": "sse"})

            # Verify timer was used
            mock_timer.assert_called_with(110, "RAG.platform.send.done.frame", "SendDone", stage="start")

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 110: Verify comprehensive logging format"""

        stream_writer = MagicMock()
        stream_writer.write = MagicMock()

        ctx = {
            "stream_writer": stream_writer,
            "streaming_format": "sse",
            "chunks_sent": 20,
            "total_bytes": 4096,
            "stream_id": "stream-456",
            "client_connected": True,
        }

        # Call the orchestrator function
        step_110__send_done(ctx=ctx)

        # Verify RAG step logging format
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            "step",
            "step_id",
            "node_label",
            "streaming_event",
            "streaming_format",
            "chunks_sent",
            "total_bytes",
            "done_sent",
            "client_connected",
            "stream_id",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 110
        assert log_call[1]["step_id"] == "RAG.platform.send.done.frame"
        assert log_call[1]["node_label"] == "SendDone"
        assert log_call[1]["streaming_event"] == "done_frame_sent"
        assert log_call[1]["streaming_format"] == "sse"
        assert log_call[1]["chunks_sent"] == 20
        assert log_call[1]["total_bytes"] == 4096
        assert log_call[1]["stream_id"] == "stream-456"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_done_frame_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 110: Verify DONE frame data structure"""

        ctx = {"streaming_format": "sse", "chunks_sent": 5, "total_bytes": 512}

        # Call the orchestrator function
        result = step_110__send_done(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            "timestamp",
            "streaming_format",
            "chunks_sent",
            "total_bytes",
            "stream_id",
            "done_sent",
            "client_connected",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in DONE frame data: {field}"

        # Verify data types
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["streaming_format"], str)
        assert isinstance(result["chunks_sent"], int)
        assert isinstance(result["total_bytes"], int)
        assert isinstance(result["done_sent"], bool)
        assert isinstance(result["client_connected"], bool)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_110_different_streaming_formats(self, mock_logger, mock_rag_log):
        """Test Step 110: Handle different streaming formats"""

        formats_and_writers = [
            ("sse", "write", "data: [DONE]\n\n"),
            ("websocket", "send", None),  # JSON format, checked differently
            ("custom", "write", "\n[DONE]\n"),
        ]

        for format_name, method_name, expected_content in formats_and_writers:
            # Create fresh mock for each test
            stream_writer = MagicMock()
            setattr(stream_writer, method_name, MagicMock())

            ctx = {"stream_writer": stream_writer, "streaming_format": format_name}

            # Call the orchestrator function
            result = step_110__send_done(ctx=ctx)

            # Verify DONE frame was sent
            assert result["done_sent"] is True
            assert result["streaming_format"] == format_name

            # Verify correct method was called
            method = getattr(stream_writer, method_name)
            method.assert_called_once()

            if expected_content:
                sent_data = method.call_args[0][0]
                if method_name == "write":
                    # Write method gets bytes
                    assert sent_data == expected_content.encode("utf-8")
                else:
                    # Send method gets string
                    assert sent_data == expected_content
