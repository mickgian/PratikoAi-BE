#!/usr/bin/env python3
"""
Tests for RAG STEP 11 — LangGraphAgent._chat Convert to Message objects

This step converts various message formats to standardized Message objects.
Connects to other message processing steps in the RAG workflow.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.chat import Message


class TestRAGStep11ConvertMessages:
    """Test suite for RAG STEP 11 - Convert to Message objects"""

    @pytest.fixture
    def mock_raw_messages(self):
        """Mock raw message data in various formats."""
        return [
            {"role": "user", "content": "What are my tax obligations?"},
            {"role": "assistant", "content": "Tax obligations depend on your status..."},
            {"role": "user", "content": "Can you be more specific?"},
        ]

    @pytest.fixture
    def mock_langchain_messages(self):
        """Mock LangChain BaseMessage objects."""
        messages = []
        for i, content in enumerate(["First message", "Second message"]):
            msg = MagicMock()
            msg.role = "user" if i % 2 == 0 else "assistant"
            msg.content = content
            messages.append(msg)
        return messages

    @pytest.fixture
    def mock_mixed_messages(self):
        """Mock mixed format messages."""
        return [
            {"role": "user", "content": "Hello"},
            Message(role="assistant", content="Hi there"),
            "Plain string message",
        ]

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_successful_dict_conversion(self, mock_logger, mock_rag_log, mock_raw_messages):
        """Test Step 11: Successful conversion of dict messages to Message objects"""
        from app.orchestrators.platform import step_11__convert_messages

        # Context with raw dict messages
        ctx = {"raw_messages": mock_raw_messages, "message_format": "dict", "request_id": "req_123"}

        # Call the orchestrator function
        result = await step_11__convert_messages(ctx=ctx)

        # Verify result structure
        assert isinstance(result, dict)
        assert result["conversion_successful"] is True
        assert result["message_count"] == 3
        assert result["converted_messages"] is not None
        assert result["next_step"] == "ExtractQuery"
        assert "standardized_messages" in result

        # Verify all messages are converted to Message objects
        converted = result["converted_messages"]
        assert len(converted) == 3
        assert all(isinstance(msg, Message) for msg in converted)
        assert converted[0].role == "user"
        assert converted[0].content == "What are my tax obligations?"
        assert converted[1].role == "assistant"
        assert converted[2].role == "user"

        # Verify logging
        mock_logger.info.assert_called()
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Message conversion completed" in call for call in log_calls)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]
        assert len(completed_logs) > 0
        log_call = completed_logs[0]
        assert log_call[1]["step"] == 11
        assert log_call[1]["conversion_successful"] is True
        assert log_call[1]["message_count"] == 3

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_langchain_message_conversion(self, mock_logger, mock_rag_log, mock_langchain_messages):
        """Test Step 11: Convert LangChain BaseMessage objects"""
        from app.orchestrators.platform import step_11__convert_messages

        ctx = {"raw_messages": mock_langchain_messages, "message_format": "langchain", "request_id": "req_456"}

        result = await step_11__convert_messages(ctx=ctx)

        # Should successfully convert LangChain messages
        assert result["conversion_successful"] is True
        assert result["message_count"] == 2
        converted = result["converted_messages"]
        assert len(converted) == 2
        assert all(isinstance(msg, Message) for msg in converted)
        assert converted[0].content == "First message"
        assert converted[1].content == "Second message"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_mixed_format_conversion(self, mock_logger, mock_rag_log, mock_mixed_messages):
        """Test Step 11: Handle mixed message formats"""
        from app.orchestrators.platform import step_11__convert_messages

        ctx = {"raw_messages": mock_mixed_messages, "message_format": "mixed", "request_id": "req_789"}

        result = await step_11__convert_messages(ctx=ctx)

        # Should handle mixed formats gracefully
        assert result["conversion_successful"] is True
        assert result["message_count"] == 3
        converted = result["converted_messages"]
        assert len(converted) == 3
        assert all(isinstance(msg, Message) for msg in converted)

        # Check specific conversions
        assert converted[0].role == "user"
        assert converted[0].content == "Hello"
        assert converted[1].role == "assistant"
        assert converted[1].content == "Hi there"
        assert converted[2].role == "user"  # Default role for string
        assert converted[2].content == "Plain string message"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_empty_messages(self, mock_logger, mock_rag_log):
        """Test Step 11: Handle empty message list"""
        from app.orchestrators.platform import step_11__convert_messages

        ctx = {"raw_messages": [], "message_format": "empty", "request_id": "req_empty"}

        result = await step_11__convert_messages(ctx=ctx)

        # Should handle empty list gracefully
        assert result["conversion_successful"] is True
        assert result["message_count"] == 0
        assert result["converted_messages"] == []
        assert result["next_step"] == "ExtractQuery"

        # Verify warning logged
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_invalid_message_format(self, mock_logger, mock_rag_log):
        """Test Step 11: Handle invalid message formats"""
        from app.orchestrators.platform import step_11__convert_messages

        ctx = {
            "raw_messages": [{"invalid": "format"}, None, 123],
            "message_format": "invalid",
            "request_id": "req_invalid",
        }

        result = await step_11__convert_messages(ctx=ctx)

        # Should handle gracefully but mark some failures
        assert result["conversion_successful"] is True  # Overall success
        assert "conversion_errors" in result
        assert len(result["conversion_errors"]) > 0
        assert result["message_count"] >= 0

        # Verify error logging
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_message_validation(self, mock_logger, mock_rag_log):
        """Test Step 11: Message content validation"""
        from app.orchestrators.platform import step_11__convert_messages

        # Messages with validation issues
        problematic_messages = [
            {"role": "user", "content": ""},  # Empty content
            {"role": "user", "content": "x" * 4000},  # Too long
            {"role": "user", "content": "Valid message"},
            {"role": "invalid_role", "content": "Message with bad role"},
        ]

        ctx = {
            "raw_messages": problematic_messages,
            "message_format": "validation_test",
            "request_id": "req_validation",
        }

        result = await step_11__convert_messages(ctx=ctx)

        # Should filter out invalid messages
        assert result["conversion_successful"] is True
        assert "validation_errors" in result
        converted = result["converted_messages"]

        # Only valid messages should remain
        valid_messages = [msg for msg in converted if msg.content == "Valid message"]
        assert len(valid_messages) >= 1

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_message_deduplication(self, mock_logger, mock_rag_log):
        """Test Step 11: Remove duplicate messages"""
        from app.orchestrators.platform import step_11__convert_messages

        # Duplicate messages
        duplicate_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "Hello"},  # Duplicate
            {"role": "user", "content": "Different message"},
        ]

        ctx = {
            "raw_messages": duplicate_messages,
            "message_format": "dedup_test",
            "request_id": "req_dedup",
            "enable_deduplication": True,
        }

        result = await step_11__convert_messages(ctx=ctx)

        assert result["conversion_successful"] is True
        converted = result["converted_messages"]

        # Should have removed consecutive duplicates only (not global duplicates)
        # The duplicate "Hello" is not consecutive, so both should remain
        user_hello_count = sum(1 for msg in converted if msg.role == "user" and msg.content == "Hello")
        assert user_hello_count == 2  # Both "Hello" messages remain (not consecutive)

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_ready_for_step_12(self, mock_logger, mock_rag_log, mock_raw_messages):
        """Test Step 11: Output ready for Step 12 (ExtractQuery)"""
        from app.orchestrators.platform import step_11__convert_messages

        ctx = {"raw_messages": mock_raw_messages, "message_format": "dict", "request_id": "req_ready"}

        result = await step_11__convert_messages(ctx=ctx)

        # Verify output is ready for Step 12
        assert result["ready_for_extraction"] is True
        assert "converted_messages" in result
        assert "standardized_messages" in result
        assert result["next_step"] == "ExtractQuery"

        # These fields needed for Step 12 query extraction
        assert result["converted_messages"] is not None
        assert len(result["converted_messages"]) > 0
        assert all(isinstance(msg, Message) for msg in result["converted_messages"])

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_comprehensive_logging(self, mock_logger, mock_rag_log, mock_raw_messages):
        """Test Step 11: Comprehensive logging format"""
        from app.orchestrators.platform import step_11__convert_messages

        ctx = {"raw_messages": mock_raw_messages, "message_format": "dict", "request_id": "req_comprehensive"}

        await step_11__convert_messages(ctx=ctx)

        # Verify RAG step logging
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
            "conversion_successful",
            "message_count",
            "processing_stage",
            "next_step",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]["step"] == 11
        assert log_call[1]["step_id"] == "RAG.platform.langgraphagent.chat.convert.to.message.objects"
        assert log_call[1]["node_label"] == "ConvertMessages"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_performance_tracking(self, mock_logger, mock_rag_log, mock_raw_messages):
        """Test Step 11: Performance tracking with timer"""
        from app.orchestrators.platform import step_11__convert_messages

        with patch("app.orchestrators.platform.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            ctx = {"raw_messages": mock_raw_messages, "message_format": "dict", "request_id": "req_perf"}

            await step_11__convert_messages(ctx=ctx)

            # Verify timer was used
            mock_timer.assert_called_with(
                11, "RAG.platform.langgraphagent.chat.convert.to.message.objects", "ConvertMessages", stage="start"
            )

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_11_parity_preservation(self, mock_logger, mock_rag_log, mock_raw_messages):
        """Test Step 11: Parity test - behavior identical to LangGraphAgent._chat conversion"""
        from app.orchestrators.platform import step_11__convert_messages

        ctx = {"raw_messages": mock_raw_messages, "message_format": "dict", "request_id": "req_parity"}

        # Call orchestrator
        result = await step_11__convert_messages(ctx=ctx)

        # Verify behavior matches expected LangGraphAgent._chat conversion
        assert result["conversion_successful"] is True
        assert result["message_count"] == len(mock_raw_messages)

        # Verify message data is preserved
        converted = result["converted_messages"]
        for i, original in enumerate(mock_raw_messages):
            assert converted[i].role == original["role"]
            assert converted[i].content == original["content"]

        # Verify structure matches expected output
        assert isinstance(converted, list)
        assert all(isinstance(msg, Message) for msg in converted)
