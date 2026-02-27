#!/usr/bin/env python3
"""
Tests for RAG STEP 31 — DomainActionClassifier.classify Rule-based classification

This step performs rule-based classification using the DomainActionClassifier service.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrators.classify import step_31__classify_domain
from app.services.domain_action_classifier import Action, Domain, DomainActionClassification


class TestRAGStep31ClassifyDomain:
    """Test suite for RAG STEP 31 - Rule-based classification"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_31_successful_classification(self, mock_logger, mock_rag_log):
        """Test Step 31: Successful rule-based classification"""

        # Mock classification result
        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.85,
            reasoning="Tax information request about IVA",
            fallback_used=False,
        )

        # Create mock for QueryCompositionType enum
        mock_composition = MagicMock()
        mock_composition.value = "pure_kb"

        ctx = {
            "user_query": "Qual è l'aliquota IVA per i servizi professionali?",
            "classification_service": AsyncMock(),
        }
        ctx["classification_service"].classify.return_value = classification
        ctx["classification_service"].detect_query_composition.return_value = mock_composition

        # Call the orchestrator function
        result = await step_31__classify_domain(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["classification"] == classification
        assert result["domain"] == "tax"
        assert result["action"] == "information_request"
        assert result["confidence"] == 0.85
        assert result["fallback_used"] is False
        assert "timestamp" in result

        # Verify service was called
        ctx["classification_service"].classify.assert_called_once_with(
            "Qual è l'aliquota IVA per i servizi professionali?"
        )

        # Verify logging was called (may be called multiple times - once for query composition, once for classification)
        assert mock_logger.info.call_count >= 1
        # Find the classification log call (not the query_composition_detected one)
        classification_log_calls = [
            call
            for call in mock_logger.info.call_args_list
            if len(call[0]) > 0 and "Rule-based classification completed" in call[0][0]
        ]
        assert len(classification_log_calls) == 1
        log_call = classification_log_calls[0]
        assert log_call[1]["extra"]["classification_event"] == "rule_based_classification"
        assert log_call[1]["extra"]["domain"] == "tax"
        assert log_call[1]["extra"]["confidence"] == 0.85

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]
        assert len(completed_logs) > 0
        completed_log = completed_logs[0]
        assert completed_log[1]["step"] == 31
        assert completed_log[1]["classification_event"] == "rule_based_classification"
        assert completed_log[1]["domain"] == "tax"

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_31_legal_classification(self, mock_logger, mock_rag_log):
        """Test Step 31: Legal domain classification"""

        classification = DomainActionClassification(
            domain=Domain.LEGAL,
            action=Action.DOCUMENT_GENERATION,
            confidence=0.92,
            reasoning="Legal document generation request",
            fallback_used=False,
        )

        ctx = {
            "user_query": "Mi serve un contratto di locazione",
            "classification_service": AsyncMock(),
        }
        ctx["classification_service"].classify.return_value = classification

        result = await step_31__classify_domain(ctx=ctx)

        assert result["domain"] == "legal"
        assert result["action"] == "document_generation"
        assert result["confidence"] == 0.92

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_31_with_fallback(self, mock_logger, mock_rag_log):
        """Test Step 31: Classification with LLM fallback"""

        classification = DomainActionClassification(
            domain=Domain.BUSINESS,
            action=Action.STRATEGIC_ADVICE,
            confidence=0.75,
            reasoning="Business strategy advice via LLM fallback",
            fallback_used=True,
        )

        ctx = {
            "user_query": "Come posso espandere la mia attività?",
            "classification_service": AsyncMock(),
        }
        ctx["classification_service"].classify.return_value = classification

        result = await step_31__classify_domain(ctx=ctx)

        assert result["fallback_used"] is True
        assert result["domain"] == "business"
        assert result["confidence"] == 0.75

        # Verify warning was logged for fallback
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert "Rule-based classification used LLM fallback" in warning_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_31_classification_failure(self, mock_logger, mock_rag_log):
        """Test Step 31: Handle classification service failure"""

        ctx = {
            "user_query": "Test query",
            "classification_service": AsyncMock(),
        }
        ctx["classification_service"].classify.side_effect = Exception("Classification service error")

        result = await step_31__classify_domain(ctx=ctx)

        # Should return error result
        assert result["classification"] is None
        assert result["error"] == "Classification service error"
        assert result["domain"] is None
        assert result["confidence"] == 0.0

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Rule-based classification failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.domain_action_classifier.DomainActionClassifier")
    async def test_step_31_create_classifier_if_missing(self, mock_classifier_class, mock_logger, mock_rag_log):
        """Test Step 31: Create classifier if not provided in context"""

        # Mock classifier instance
        mock_classifier = AsyncMock()
        mock_classifier_class.return_value = mock_classifier

        classification = DomainActionClassification(
            domain=Domain.ACCOUNTING,
            action=Action.CALCULATION_REQUEST,
            confidence=0.88,
            reasoning="Accounting calculation request",
        )
        mock_classifier.classify.return_value = classification

        ctx = {"user_query": "Calcola l'ammortamento del macchinario"}

        result = await step_31__classify_domain(ctx=ctx)

        # Verify classifier was created and used
        mock_classifier_class.assert_called_once()
        mock_classifier.classify.assert_called_once_with("Calcola l'ammortamento del macchinario")
        assert result["domain"] == "accounting"

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_31_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 31: Handle empty context gracefully"""

        result = await step_31__classify_domain()

        # Verify defaults are used
        assert isinstance(result, dict)
        assert result["classification"] is None
        assert result["domain"] is None
        assert result["confidence"] == 0.0
        assert result["error"] == "No user query provided"

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_31_kwargs_parameters(self, mock_logger, mock_rag_log):
        """Test Step 31: Parameters passed via kwargs"""

        classification = DomainActionClassification(
            domain=Domain.LABOR, action=Action.COMPLIANCE_CHECK, confidence=0.90, reasoning="Labor compliance check"
        )

        classification_service = AsyncMock()
        classification_service.classify.return_value = classification

        # Call with kwargs instead of ctx
        result = await step_31__classify_domain(
            user_query="Controlla la conformità del contratto di lavoro", classification_service=classification_service
        )

        # Verify kwargs are processed correctly
        assert result["domain"] == "labor"
        assert result["action"] == "compliance_check"
        assert result["confidence"] == 0.90

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_31_performance_tracking(self, mock_logger, mock_rag_log):
        """Test Step 31: Performance tracking with timer"""

        with patch("app.orchestrators.classify.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Call the orchestrator function
            await step_31__classify_domain(ctx={"user_query": "test query"})

            # Verify timer was used
            mock_timer.assert_called_with(
                31,
                "RAG.classify.domainactionclassifier.classify.rule.based.classification",
                "ClassifyDomain",
                stage="start",
            )

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_31_comprehensive_logging_format(self, mock_logger, mock_rag_log):
        """Test Step 31: Verify comprehensive logging format"""

        classification = DomainActionClassification(
            domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.85, reasoning="Tax query classification"
        )

        ctx = {
            "user_query": "Test tax query",
            "classification_service": AsyncMock(),
        }
        ctx["classification_service"].classify.return_value = classification

        # Call the orchestrator function
        await step_31__classify_domain(ctx=ctx)

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
            "classification_event",
            "domain",
            "action",
            "confidence",
            "fallback_used",
            "query_length",
            "processing_stage",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]["step"] == 31
        assert log_call[1]["step_id"] == "RAG.classify.domainactionclassifier.classify.rule.based.classification"
        assert log_call[1]["node_label"] == "ClassifyDomain"
        assert log_call[1]["classification_event"] == "rule_based_classification"

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_31_classification_data_structure(self, mock_logger, mock_rag_log):
        """Test Step 31: Verify classification data structure"""

        classification = DomainActionClassification(
            domain=Domain.TAX, action=Action.INFORMATION_REQUEST, confidence=0.85, reasoning="Test classification"
        )

        ctx = {
            "user_query": "Test query",
            "classification_service": AsyncMock(),
        }
        ctx["classification_service"].classify.return_value = classification

        # Call the orchestrator function
        result = await step_31__classify_domain(ctx=ctx)

        # Verify all expected fields in result
        expected_fields = [
            "timestamp",
            "classification",
            "domain",
            "action",
            "confidence",
            "fallback_used",
            "query_length",
            "error",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field in classification data: {field}"

        # Verify data types
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["classification"], DomainActionClassification)
        assert isinstance(result["domain"], str)
        assert isinstance(result["action"], str)
        assert isinstance(result["confidence"], float)
        assert isinstance(result["fallback_used"], bool)
        assert isinstance(result["query_length"], int)

        # Verify timestamp format (ISO format)
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
