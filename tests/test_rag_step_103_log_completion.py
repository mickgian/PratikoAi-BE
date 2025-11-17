#!/usr/bin/env python3
"""
Tests for RAG STEP 103 — Log completion

This step logs completion of RAG processing for monitoring and metrics.
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.orchestrators.platform import step_103__log_complete
from app.services.domain_action_classifier import Action, Domain, DomainActionClassification


class TestRAGStep103LogCompletion:
    """Test suite for RAG STEP 103 - Log completion"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_successful_completion(self, mock_logger, mock_rag_log):
        """Test Step 103: Log successful RAG completion"""

        response = "This is a successful response from the RAG system."
        classification = DomainActionClassification(
            domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.8, reasoning="Tax information request"
        )

        ctx = {
            "response": response,
            "response_type": "text",
            "processing_time": 1.5,
            "success": True,
            "user_query": "What are the tax rates?",
            "classification": classification,
        }

        # Call the orchestrator function
        result = step_103__log_complete(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["response_type"] == "text"
        assert result["processing_time_ms"] == 1500
        assert result["response_length"] == len(response)
        assert result["has_classification"] is True
        assert "timestamp" in result

        # Verify logger was called with INFO level
        mock_logger.log.assert_called_once()
        log_call = mock_logger.log.call_args
        # INFO level should be used for successful completion
        assert log_call[1]["extra"]["completion_event"] == "rag_processing_complete"
        assert log_call[1]["extra"]["success"] is True
        assert log_call[1]["extra"]["domain"] == "tax"
        assert log_call[1]["extra"]["confidence"] == 0.8

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]
        assert len(completed_logs) > 0
        completed_log = completed_logs[0]
        assert completed_log[1]["step"] == 103
        assert completed_log[1]["completion_event"] == "rag_processing_complete"
        assert completed_log[1]["success"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_failed_completion(self, mock_logger, mock_rag_log):
        """Test Step 103: Log failed RAG completion"""

        ctx = {
            "response": None,
            "response_type": "error",
            "processing_time": 0.8,
            "success": False,
            "error_message": "LLM provider timeout",
            "user_query": "Complex tax question",
        }

        # Call the orchestrator function
        result = step_103__log_complete(ctx=ctx)

        # Verify the result structure
        assert result["success"] is False
        assert result["error_message"] == "LLM provider timeout"
        assert result["response_length"] == 0
        assert result["has_classification"] is False

        # Verify logger was called with WARNING level for failures
        mock_logger.log.assert_called_once()
        log_call = mock_logger.log.call_args
        assert "error" in log_call[0][1].lower()
        assert log_call[1]["extra"]["success"] is False

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_dict_response(self, mock_logger, mock_rag_log):
        """Test Step 103: Handle dictionary response format"""

        response = {"content": "This is response content", "metadata": {"source": "llm"}}

        ctx = {"response": response, "response_type": "structured", "success": True, "user_query": "Test query"}

        # Call the orchestrator function
        result = step_103__log_complete(ctx=ctx)

        # Verify response length extracted from dict
        assert result["response_length"] == len("This is response content")
        assert result["response_type"] == "structured"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_object_response(self, mock_logger, mock_rag_log):
        """Test Step 103: Handle response object with content attribute"""

        response = MagicMock()
        response.content = "This is object response content"

        ctx = {"response": response, "response_type": "object", "success": True}

        # Call the orchestrator function
        result = step_103__log_complete(ctx=ctx)

        # Verify response length extracted from object
        assert result["response_length"] == len("This is object response content")

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_calculated_processing_time(self, mock_logger, mock_rag_log):
        """Test Step 103: Calculate processing time from start_time"""

        start_time = time.time() - 2.0  # 2 seconds ago

        ctx = {"start_time": start_time, "success": True, "response": "Test response"}

        # Call the orchestrator function
        result = step_103__log_complete(ctx=ctx)

        # Verify processing time was calculated
        assert result["processing_time_ms"] is not None
        assert result["processing_time_ms"] > 1500  # Should be around 2000ms
        assert result["processing_time_ms"] < 3000  # But less than 3000ms

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_no_classification(self, mock_logger, mock_rag_log):
        """Test Step 103: Handle completion without classification"""

        ctx = {"response": "Response without classification", "success": True, "classification": None}

        # Call the orchestrator function
        result = step_103__log_complete(ctx=ctx)

        # Verify classification handling
        assert result["has_classification"] is False

        # Verify logging includes None values for classification fields
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]
        completed_log = completed_logs[0]
        assert completed_log[1]["domain"] is None
        assert completed_log[1]["action"] is None
        assert completed_log[1]["confidence"] is None

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 103: Handle empty context gracefully"""

        # Call with minimal context
        result = step_103__log_complete()

        # Verify defaults are used
        assert isinstance(result, dict)
        assert result["success"] is True  # Default success
        assert result["response_type"] == "unknown"
        assert result["query_length"] == 0
        assert result["response_length"] == 0
        assert result["has_classification"] is False

        # Verify logging still occurs
        mock_logger.log.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_streaming_response(self, mock_logger, mock_rag_log):
        """Test Step 103: Handle streaming response completion"""

        ctx = {
            "response_type": "streaming",
            "success": True,
            "chunks_sent": 15,
            "total_bytes": 2048,
            "user_query": "Streaming query",
        }

        # Call the orchestrator function
        result = step_103__log_complete(ctx=ctx)

        # Verify streaming-specific data
        assert result["response_type"] == "streaming"
        assert result["success"] is True

        # Verify logging captures streaming context
        mock_logger.log.assert_called_once()
        log_call = mock_logger.log.call_args
        assert log_call[1]["extra"]["response_type"] == "streaming"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 103: Performance tracking with timer"""

        with patch("app.orchestrators.platform.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            step_103__log_complete(ctx={"success": True})

            # Verify timer was used
            mock_timer.assert_called_with(103, "RAG.platform.logger.info.log.completion", "LogComplete", stage="start")

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 103: Verify comprehensive logging format"""

        classification = DomainActionClassification(
            domain=Domain.BUSINESS,
            action=Action.STRATEGIC_ADVICE,
            confidence=0.9,
            reasoning="Business strategy question",
        )

        ctx = {
            "response": "Comprehensive response",
            "response_type": "detailed",
            "processing_time": 1.2,
            "success": True,
            "user_query": "Business question",
            "classification": classification,
        }

        # Call the orchestrator function
        step_103__log_complete(ctx=ctx)

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
            "completion_event",
            "success",
            "response_type",
            "processing_time_ms",
            "query_length",
            "response_length",
            "has_classification",
            "domain",
            "action",
            "confidence",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 103
        assert log_call[1]["step_id"] == "RAG.platform.logger.info.log.completion"
        assert log_call[1]["node_label"] == "LogComplete"
        assert log_call[1]["completion_event"] == "rag_processing_complete"
        assert log_call[1]["domain"] == "business"
        assert log_call[1]["action"] == "strategic_advice"
        assert log_call[1]["confidence"] == 0.9

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_103_completion_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 103: Verify completion data structure"""

        ctx = {"response": "Test response", "success": True, "processing_time": 0.5}

        # Call the orchestrator function
        result = step_103__log_complete(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            "timestamp",
            "success",
            "response_type",
            "processing_time_ms",
            "query_length",
            "response_length",
            "has_classification",
            "error_message",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in completion data: {field}"

        # Verify data types
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["success"], bool)
        assert isinstance(result["response_type"], str)
        assert isinstance(result["query_length"], int)
        assert isinstance(result["response_length"], int)
        assert isinstance(result["has_classification"], bool)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
