#!/usr/bin/env python3
"""
Tests for RAG STEP 33 — Confidence at least threshold?

This step performs a confidence threshold check on classification results.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.orchestrators.classify import step_33__confidence_check
from app.services.domain_action_classifier import Action, Domain


class TestRAGStep33ConfidenceCheck:
    """Test suite for RAG STEP 33 - Confidence threshold check"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_confidence_above_threshold(self, mock_logger, mock_rag_log):
        """Test Step 33: Confidence above threshold (default 0.6)"""

        ctx = {
            "classification": {
                "domain": "tax",
                "action": "information_request",
                "confidence": 0.85,
                "fallback_used": False,
            }
        }

        # Call the orchestrator function
        result = await step_33__confidence_check(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["confidence_met"] is True
        assert result["confidence_value"] == 0.85
        assert result["threshold"] == 0.6
        assert result["domain"] == "tax"
        assert result["action"] == "information_request"
        assert "timestamp" in result

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Confidence threshold met" in log_call[0][0]
        assert log_call[1]["extra"]["confidence_event"] == "threshold_met"
        assert log_call[1]["extra"]["confidence_value"] == 0.85

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_confidence_below_threshold(self, mock_logger, mock_rag_log):
        """Test Step 33: Confidence below threshold"""

        ctx = {
            "classification": {
                "domain": "business",
                "action": "strategic_advice",
                "confidence": 0.45,
                "fallback_used": False,
            }
        }

        result = await step_33__confidence_check(ctx=ctx)

        assert result["confidence_met"] is False
        assert result["confidence_value"] == 0.45
        assert result["threshold"] == 0.6

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert "Confidence threshold not met" in warning_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_custom_threshold(self, mock_logger, mock_rag_log):
        """Test Step 33: Custom confidence threshold"""

        ctx = {
            "classification": {
                "domain": "legal",
                "action": "document_generation",
                "confidence": 0.75,
                "fallback_used": False,
            },
            "confidence_threshold": 0.8,
        }

        result = await step_33__confidence_check(ctx=ctx)

        assert result["confidence_met"] is False
        assert result["confidence_value"] == 0.75
        assert result["threshold"] == 0.8

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_exact_threshold_match(self, mock_logger, mock_rag_log):
        """Test Step 33: Confidence exactly at threshold"""

        ctx = {
            "classification": {
                "domain": "accounting",
                "action": "calculation_request",
                "confidence": 0.6,
                "fallback_used": False,
            }
        }

        result = await step_33__confidence_check(ctx=ctx)

        assert result["confidence_met"] is True
        assert result["confidence_value"] == 0.6
        assert result["threshold"] == 0.6

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_missing_classification(self, mock_logger, mock_rag_log):
        """Test Step 33: Handle missing classification"""

        ctx = {}

        result = await step_33__confidence_check(ctx=ctx)

        # Should return error result
        assert result["confidence_met"] is False
        assert result["error"] == "No classification data provided"
        assert result["confidence_value"] == 0.0

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Confidence check failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_confidence_from_scores(self, mock_logger, mock_rag_log):
        """Test Step 33: Use confidence from scores data when classification missing"""

        ctx = {
            "scores_data": {
                "domain_confidence": 0.85,
                "action_confidence": 0.90,
                "best_domain": Domain.TAX,
                "best_action": Action.INFORMATION_REQUEST,
            }
        }

        result = await step_33__confidence_check(ctx=ctx)

        # Should use domain confidence as primary
        assert result["confidence_met"] is True
        assert result["confidence_value"] == 0.85
        assert result["domain"] == "tax"
        assert result["action"] == "information_request"

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_fallback_detected(self, mock_logger, mock_rag_log):
        """Test Step 33: LLM fallback used in classification"""

        ctx = {
            "classification": {
                "domain": "labor",
                "action": "compliance_check",
                "confidence": 0.75,
                "fallback_used": True,
            }
        }

        result = await step_33__confidence_check(ctx=ctx)

        assert result["confidence_met"] is True
        assert result["fallback_used"] is True

        # Verify fallback was noted in logging
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert log_call[1]["extra"]["fallback_used"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 33: Parameters passed via kwargs"""

        # Call with kwargs instead of ctx
        result = await step_33__confidence_check(
            classification={"domain": "tax", "confidence": 0.88}, confidence_threshold=0.7
        )

        # Verify kwargs are processed correctly
        assert result["confidence_met"] is True
        assert result["confidence_value"] == 0.88
        assert result["threshold"] == 0.7

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 33: Performance tracking with timer"""

        with patch("app.orchestrators.classify.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            await step_33__confidence_check(ctx={"classification": {"confidence": 0.8}})

            # Verify timer was used
            mock_timer.assert_called_with(
                33, "RAG.classify.confidence.at.least.threshold", "ConfidenceCheck", stage="start"
            )

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 33: Verify comprehensive logging format"""

        ctx = {
            "classification": {
                "domain": "tax",
                "action": "information_request",
                "confidence": 0.85,
                "fallback_used": False,
            }
        }

        # Call the orchestrator function
        await step_33__confidence_check(ctx=ctx)

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
            "confidence_event",
            "confidence_met",
            "confidence_value",
            "threshold",
            "domain",
            "action",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 33
        assert log_call[1]["step_id"] == "RAG.classify.confidence.at.least.threshold"
        assert log_call[1]["node_label"] == "ConfidenceCheck"
        assert log_call[1]["confidence_event"] == "threshold_met"

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_33_confidence_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 33: Verify confidence data structure"""

        ctx = {
            "classification": {
                "domain": "tax",
                "action": "information_request",
                "confidence": 0.85,
                "fallback_used": False,
            }
        }

        # Call the orchestrator function
        result = await step_33__confidence_check(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            "timestamp",
            "confidence_met",
            "confidence_value",
            "threshold",
            "domain",
            "action",
            "fallback_used",
            "error",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in confidence data: {field}"

        # Verify data types
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["confidence_met"], bool)
        assert isinstance(result["confidence_value"], float)
        assert isinstance(result["threshold"], float)
        assert isinstance(result["domain"], str) or result["domain"] is None
        assert isinstance(result["action"], str) or result["action"] is None
        assert isinstance(result["fallback_used"], bool)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
