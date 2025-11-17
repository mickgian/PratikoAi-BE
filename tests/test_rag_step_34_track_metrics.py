#!/usr/bin/env python3
"""
Tests for RAG STEP 34 — ClassificationMetrics.track Record metrics

This step tracks classification metrics using the existing monitoring infrastructure.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrators.metrics import step_34__track_metrics
from app.services.domain_action_classifier import Action, Domain, DomainActionClassification


class TestRAGStep34TrackMetrics:
    """Test suite for RAG STEP 34 - Track classification metrics"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_track_classification_success(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Successful classification metrics tracking"""

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.85,
            reasoning="Tax information request",
            fallback_used=False,
        )

        ctx = {
            "classification": classification,
            "prompt_used": True,
            "user_query": "Qual è l'aliquota IVA per i servizi professionali?",
        }

        # Call the orchestrator function
        result = await step_34__track_metrics(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["metrics_tracked"] is True
        assert result["domain"] == "tax"
        assert result["action"] == "information_request"
        assert result["confidence"] == 0.85
        assert result["fallback_used"] is False
        assert result["prompt_used"] is True
        assert "timestamp" in result

        # Verify track_classification_usage was called correctly
        mock_track_usage.assert_called_once_with(
            domain="tax", action="information_request", confidence=0.85, fallback_used=False, prompt_used=True
        )

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Classification metrics tracked successfully" in log_call[0][0]
        assert log_call[1]["extra"]["metrics_event"] == "classification_tracked"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_track_with_fallback_used(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Track classification with LLM fallback"""

        classification = DomainActionClassification(
            domain=Domain.BUSINESS,
            action=Action.STRATEGIC_ADVICE,
            confidence=0.72,
            reasoning="Business advice via LLM fallback",
            fallback_used=True,
        )

        ctx = {"classification": classification, "prompt_used": False}

        result = await step_34__track_metrics(ctx=ctx)

        assert result["metrics_tracked"] is True
        assert result["fallback_used"] is True
        assert result["prompt_used"] is False

        # Verify fallback usage was tracked
        mock_track_usage.assert_called_once_with(
            domain="business", action="strategic_advice", confidence=0.72, fallback_used=True, prompt_used=False
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_track_dict_format_classification(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Track classification provided as dict"""

        ctx = {
            "classification": {
                "domain": Domain.LEGAL,
                "action": Action.DOCUMENT_GENERATION,
                "confidence": 0.91,
                "reasoning": "Legal document generation",
                "fallback_used": False,
            },
            "prompt_used": True,
        }

        result = await step_34__track_metrics(ctx=ctx)

        assert result["metrics_tracked"] is True
        assert result["domain"] == "legal"
        assert result["action"] == "document_generation"

        mock_track_usage.assert_called_once_with(
            domain="legal", action="document_generation", confidence=0.91, fallback_used=False, prompt_used=True
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_missing_classification_data(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Handle missing classification data"""

        ctx = {}

        result = await step_34__track_metrics(ctx=ctx)

        # Should return error result
        assert result["metrics_tracked"] is False
        assert result["error"] == "No classification data provided"

        # Should not call tracking
        mock_track_usage.assert_not_called()

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Classification metrics tracking failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_metrics_tracking_error(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Handle metrics tracking service error"""

        mock_track_usage.side_effect = Exception("Metrics service error")

        classification = DomainActionClassification(
            domain=Domain.ACCOUNTING,
            action=Action.CALCULATION_REQUEST,
            confidence=0.88,
            reasoning="Accounting calculation",
        )

        ctx = {"classification": classification, "prompt_used": False}

        result = await step_34__track_metrics(ctx=ctx)

        # Should return error result
        assert result["metrics_tracked"] is False
        assert result["error"] == "Metrics service error"

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Classification metrics tracking failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_low_confidence_classification(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Track low confidence classification"""

        classification = DomainActionClassification(
            domain=Domain.LABOR,
            action=Action.COMPLIANCE_CHECK,
            confidence=0.35,
            reasoning="Low confidence labor compliance",
            fallback_used=True,
        )

        ctx = {"classification": classification, "prompt_used": False}

        result = await step_34__track_metrics(ctx=ctx)

        assert result["metrics_tracked"] is True
        assert result["confidence"] == 0.35

        # Should still track low confidence classifications
        mock_track_usage.assert_called_once_with(
            domain="labor", action="compliance_check", confidence=0.35, fallback_used=True, prompt_used=False
        )

        # Should log warning for low confidence
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert "Low confidence classification tracked" in warning_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_kwargs_parameters(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Parameters passed via kwargs"""

        classification = DomainActionClassification(
            domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.89, reasoning="Tax information request"
        )

        # Call with kwargs instead of ctx
        result = await step_34__track_metrics(classification=classification, prompt_used=True)

        # Verify kwargs are processed correctly
        assert result["metrics_tracked"] is True
        assert result["domain"] == "tax"
        assert result["confidence"] == 0.89

        mock_track_usage.assert_called_once_with(
            domain="tax", action="information_request", confidence=0.89, fallback_used=False, prompt_used=True
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_performance_tracking(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Performance tracking with timer"""

        with patch("app.orchestrators.metrics.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            classification = DomainActionClassification(
                domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.85, reasoning="Test classification"
            )

            # Call the orchestrator function
            await step_34__track_metrics(ctx={"classification": classification})

            # Verify timer was used
            mock_timer.assert_called_with(
                34, "RAG.metrics.classificationmetrics.track.record.metrics", "TrackMetrics", stage="start"
            )

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_comprehensive_logging_format(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Verify comprehensive logging format"""

        classification = DomainActionClassification(
            domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.85, reasoning="Tax query classification"
        )

        ctx = {"classification": classification, "prompt_used": True}

        # Call the orchestrator function
        await step_34__track_metrics(ctx=ctx)

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
            "metrics_event",
            "metrics_tracked",
            "domain",
            "action",
            "confidence",
            "fallback_used",
            "prompt_used",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 34
        assert log_call[1]["step_id"] == "RAG.metrics.classificationmetrics.track.record.metrics"
        assert log_call[1]["node_label"] == "TrackMetrics"
        assert log_call[1]["metrics_event"] == "classification_tracked"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.core.monitoring.metrics.track_classification_usage")
    async def test_step_34_metrics_data_structure(self, mock_track_usage, mock_logger, mock_rag_log):
        """Test Step 34: Verify metrics data structure"""

        classification = DomainActionClassification(
            domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.85, reasoning="Test classification"
        )

        ctx = {"classification": classification, "prompt_used": True}

        # Call the orchestrator function
        result = await step_34__track_metrics(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            "timestamp",
            "metrics_tracked",
            "domain",
            "action",
            "confidence",
            "fallback_used",
            "prompt_used",
            "error",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in metrics data: {field}"

        # Verify data types
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["metrics_tracked"], bool)
        assert isinstance(result["domain"], str) or result["domain"] is None
        assert isinstance(result["action"], str) or result["action"] is None
        assert isinstance(result["confidence"], float)
        assert isinstance(result["fallback_used"], bool)
        assert isinstance(result["prompt_used"], bool)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
