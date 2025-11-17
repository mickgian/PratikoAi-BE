#!/usr/bin/env python3
"""
Tests for RAG STEP 5 — Return 400 Bad Request

This step handles invalid requests by returning appropriate 400 error responses.
It's triggered when request validation fails in earlier steps.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep5Error400:
    """Test suite for RAG STEP 5 - Return 400 bad request"""

    @pytest.fixture
    def mock_validation_errors(self):
        """Mock validation errors from earlier steps."""
        return ["Missing required field: messages", "Invalid content type: text/plain"]

    @pytest.fixture
    def mock_request_context(self):
        """Mock request context."""
        return {"method": "POST", "url": "/api/v1/chat", "request_id": "req_error_123", "user_agent": "TestClient/1.0"}

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_validation_error_response(
        self, mock_logger, mock_rag_log, mock_validation_errors, mock_request_context
    ):
        """Test Step 5: Return 400 for validation errors"""
        from app.orchestrators.platform import step_5__error400

        # Context with validation errors
        ctx = {
            "validation_errors": mock_validation_errors,
            "error_type": "validation_failed",
            "request_context": mock_request_context,
            "session_id": "session_123",
        }

        # Call the orchestrator function
        result = step_5__error400(ctx=ctx)

        # Verify result structure
        assert isinstance(result, dict)
        assert result["status_code"] == 400
        assert result["error_returned"] is True
        assert result["error_type"] == "validation_failed"
        assert result["workflow_terminated"] is True
        assert "error_response" in result
        assert "error_details" in result

        # Verify error response format
        error_response = result["error_response"]
        assert error_response["detail"] == "Request validation failed"
        assert error_response["errors"] == mock_validation_errors
        assert error_response["status_code"] == 400

        # Verify logging
        mock_logger.error.assert_called()
        log_calls = [call[0][0] for call in mock_logger.error.call_args_list]
        assert any("400 Bad Request returned" in call for call in log_calls)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]
        assert len(completed_logs) > 0
        log_call = completed_logs[0]
        assert log_call[1]["step"] == 5
        assert log_call[1]["status_code"] == 400
        assert log_call[1]["error_returned"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_authentication_error(self, mock_logger, mock_rag_log, mock_request_context):
        """Test Step 5: Return 400 for authentication errors"""
        from app.orchestrators.platform import step_5__error400

        ctx = {
            "error_type": "authentication_failed",
            "error_message": "Invalid authentication credentials",
            "request_context": mock_request_context,
        }

        result = step_5__error400(ctx=ctx)

        # Should return 401 for auth errors, not 400
        assert result["status_code"] == 401
        assert result["error_returned"] is True
        assert result["error_type"] == "authentication_failed"

        error_response = result["error_response"]
        assert error_response["detail"] == "Invalid authentication credentials"
        assert error_response["status_code"] == 401

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_malformed_request_error(self, mock_logger, mock_rag_log, mock_request_context):
        """Test Step 5: Return 400 for malformed requests"""
        from app.orchestrators.platform import step_5__error400

        ctx = {
            "error_type": "malformed_request",
            "error_message": "Invalid JSON in request body",
            "request_context": mock_request_context,
        }

        result = step_5__error400(ctx=ctx)

        assert result["status_code"] == 400
        assert result["error_type"] == "malformed_request"

        error_response = result["error_response"]
        assert error_response["detail"] == "Invalid JSON in request body"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_missing_error_context(self, mock_logger, mock_rag_log):
        """Test Step 5: Handle missing error context"""
        from app.orchestrators.platform import step_5__error400

        # Call with minimal context
        result = step_5__error400()

        # Should return generic 400 error
        assert result["status_code"] == 400
        assert result["error_returned"] is True
        assert result["error_type"] == "unknown_error"

        error_response = result["error_response"]
        assert error_response["detail"] == "Bad request"
        assert error_response["status_code"] == 400

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_different_error_types(self, mock_logger, mock_rag_log, mock_request_context):
        """Test Step 5: Handle different error types appropriately"""
        from app.orchestrators.platform import step_5__error400

        # Test rate limiting error
        ctx = {
            "error_type": "rate_limit_exceeded",
            "error_message": "Too many requests",
            "request_context": mock_request_context,
        }

        result = step_5__error400(ctx=ctx)

        assert result["status_code"] == 429
        assert result["error_type"] == "rate_limit_exceeded"

        # Test payload too large
        ctx["error_type"] = "payload_too_large"
        ctx["error_message"] = "Request payload exceeds limit"

        result = step_5__error400(ctx=ctx)

        assert result["status_code"] == 413
        assert result["error_type"] == "payload_too_large"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_workflow_termination(
        self, mock_logger, mock_rag_log, mock_validation_errors, mock_request_context
    ):
        """Test Step 5: Proper workflow termination"""
        from app.orchestrators.platform import step_5__error400

        ctx = {
            "validation_errors": mock_validation_errors,
            "error_type": "validation_failed",
            "request_context": mock_request_context,
        }

        result = step_5__error400(ctx=ctx)

        # Verify workflow is properly terminated
        assert result["workflow_terminated"] is True
        assert result["next_step"] is None
        assert result["terminal_step"] is True

        # Should not proceed to any other steps
        assert "ready_for_next_step" not in result or result.get("ready_for_next_step") is False

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_error_details_collection(self, mock_logger, mock_rag_log, mock_request_context):
        """Test Step 5: Comprehensive error details collection"""
        from app.orchestrators.platform import step_5__error400

        ctx = {
            "error_type": "validation_failed",
            "validation_errors": ["Missing field: query"],
            "request_context": mock_request_context,
            "session_id": "session_456",
            "user_id": 789,
            "additional_context": {"attempted_action": "chat_request"},
        }

        result = step_5__error400(ctx=ctx)

        # Verify comprehensive error details
        error_details = result["error_details"]
        assert error_details["error_type"] == "validation_failed"
        assert error_details["request_id"] == "req_error_123"
        assert error_details["session_id"] == "session_456"
        assert error_details["user_id"] == 789
        assert "timestamp" in error_details

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_security_headers(self, mock_logger, mock_rag_log, mock_request_context):
        """Test Step 5: Security headers in error response"""
        from app.orchestrators.platform import step_5__error400

        ctx = {
            "error_type": "authentication_failed",
            "error_message": "Invalid token",
            "request_context": mock_request_context,
        }

        result = step_5__error400(ctx=ctx)

        # Verify security headers for auth errors
        if result["status_code"] == 401:
            assert "headers" in result["error_response"]
            assert result["error_response"]["headers"].get("WWW-Authenticate") == "Bearer"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_comprehensive_logging(
        self, mock_logger, mock_rag_log, mock_validation_errors, mock_request_context
    ):
        """Test Step 5: Comprehensive logging format"""
        from app.orchestrators.platform import step_5__error400

        ctx = {
            "validation_errors": mock_validation_errors,
            "error_type": "validation_failed",
            "request_context": mock_request_context,
            "session_id": "session_789",
        }

        step_5__error400(ctx=ctx)

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
            "status_code",
            "error_returned",
            "error_type",
            "processing_stage",
            "workflow_terminated",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]["step"] == 5
        assert log_call[1]["step_id"] == "RAG.platform.return.400.bad.request"
        assert log_call[1]["node_label"] == "Error400"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_performance_tracking(self, mock_logger, mock_rag_log, mock_validation_errors):
        """Test Step 5: Performance tracking with timer"""
        from app.orchestrators.platform import step_5__error400

        with patch("app.orchestrators.platform.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            ctx = {"validation_errors": mock_validation_errors}
            step_5__error400(ctx=ctx)

            # Verify timer was used
            mock_timer.assert_called_with(5, "RAG.platform.return.400.bad.request", "Error400", stage="start")

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_error_response_format(self, mock_logger, mock_rag_log, mock_validation_errors):
        """Test Step 5: Proper error response format for API compatibility"""
        from app.orchestrators.platform import step_5__error400

        ctx = {"validation_errors": mock_validation_errors, "error_type": "validation_failed"}

        result = step_5__error400(ctx=ctx)

        # Verify error response follows FastAPI HTTPException format
        error_response = result["error_response"]

        # Must have these fields for FastAPI compatibility
        assert "detail" in error_response
        assert "status_code" in error_response

        # Should have additional context
        assert "errors" in error_response
        assert isinstance(error_response["errors"], list)
        assert len(error_response["errors"]) == 2  # Both validation errors

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_5_parity_preservation(
        self, mock_logger, mock_rag_log, mock_validation_errors, mock_request_context
    ):
        """Test Step 5: Parity test - error format matches original ChatbotController behavior"""
        from app.orchestrators.platform import step_5__error400

        ctx = {
            "validation_errors": mock_validation_errors,
            "error_type": "validation_failed",
            "request_context": mock_request_context,
        }

        result = step_5__error400(ctx=ctx)

        # Verify behavior matches original error handling
        assert result["status_code"] == 400
        assert result["error_returned"] is True
        assert result["workflow_terminated"] is True

        # Error response should match FastAPI HTTPException format
        error_response = result["error_response"]
        assert error_response["status_code"] == 400
        assert isinstance(error_response["detail"], str)
        assert "errors" in error_response

        # Verify logging behavior matches original
        mock_logger.error.assert_called()
        error_log = mock_logger.error.call_args
        assert "request_id" in str(error_log) or "req_error_123" in str(error_log)
