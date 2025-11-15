#!/usr/bin/env python3
"""
Tests for RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification

This step provides LLM fallback classification when rule-based classification
has low confidence. Connects from Step 33 (ConfidenceCheck) and feeds into Step 36 (LLMBetter).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.domain_action_classifier import Action, Domain, DomainActionClassification


class TestRAGStep35LLMFallback:
    """Test suite for RAG STEP 35 - LLM fallback classification"""

    @pytest.fixture
    def mock_low_confidence_context(self):
        """Mock context from Step 33 with low confidence classification."""
        return {
            "user_query": "Ho bisogno di aiuto con la mia situazione fiscale complessa",
            "rule_based_classification": DomainActionClassification(
                domain=Domain.TAX,
                action=Action.INFORMATION_REQUEST,
                confidence=0.45,  # Below threshold
                sub_domain="generale",
                document_type=None,
                reasoning="Low confidence rule-based classification",
            ),
            "rule_based_confidence": 0.45,
            "classification_method": "rule_based",
            "request_id": "req_123",
        }

    @pytest.fixture
    def mock_llm_classification(self):
        """Mock successful LLM classification result."""
        return DomainActionClassification(
            domain=Domain.TAX,
            action=Action.STRATEGIC_ADVICE,
            confidence=0.87,
            sub_domain="situazioni_complesse",
            document_type=None,
            reasoning="LLM identified complex tax situation requiring strategic guidance",
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_successful_llm_fallback(
        self, mock_logger, mock_rag_log, mock_low_confidence_context, mock_llm_classification
    ):
        """Test Step 35: Successful LLM fallback classification"""
        from app.orchestrators.classify import step_35__llm_fallback

        # Mock the DomainActionClassifier service
        mock_classifier = MagicMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_llm_classification)

        # Call the orchestrator function with mocked classifier
        result = await step_35__llm_fallback(ctx=mock_low_confidence_context, classifier=mock_classifier)

        # Verify result structure
        assert isinstance(result, dict)
        assert result["llm_fallback_successful"] is True
        assert result["llm_classification"] == mock_llm_classification
        assert result["llm_fallback_used"] is True
        assert result["classification_method"] == "llm_fallback"
        assert result["next_step"] == "LLMBetter"
        assert "improved_confidence" in result
        assert result["improved_confidence"] > mock_low_confidence_context["rule_based_confidence"]

        # Verify logging
        mock_logger.info.assert_called()
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("LLM fallback classification completed" in call for call in log_calls)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]
        assert len(completed_logs) > 0
        log_call = completed_logs[0]
        assert log_call[1]["step"] == 35
        assert log_call[1]["llm_fallback_successful"] is True
        assert log_call[1]["classification_method"] == "llm_fallback"

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_llm_classification_failure(self, mock_logger, mock_rag_log, mock_low_confidence_context):
        """Test Step 35: Handle LLM classification failure gracefully"""
        from app.orchestrators.classify import step_35__llm_fallback

        # Mock the DomainActionClassifier service to return None (failure)
        mock_classifier = MagicMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=None)

        result = await step_35__llm_fallback(ctx=mock_low_confidence_context, classifier=mock_classifier)

        # Should fall back to rule-based classification
        assert result["llm_fallback_successful"] is False
        assert result["fallback_to_rule_based"] is True
        assert result["classification_method"] == "rule_based_fallback"
        assert result["llm_classification"] == mock_low_confidence_context["rule_based_classification"]
        assert result["next_step"] == "UseRuleBased"

        # Verify warning logged
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_missing_context(self, mock_logger, mock_rag_log):
        """Test Step 35: Handle missing context gracefully"""
        from app.orchestrators.classify import step_35__llm_fallback

        # Call with no context
        result = await step_35__llm_fallback(ctx=None)

        # Should handle gracefully
        assert result["llm_fallback_successful"] is False
        assert "error" in result
        assert "Missing context" in result["error"]

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_missing_query(self, mock_logger, mock_rag_log):
        """Test Step 35: Handle missing user query"""
        from app.orchestrators.classify import step_35__llm_fallback

        ctx = {"rule_based_classification": None, "request_id": "req_no_query"}

        result = await step_35__llm_fallback(ctx=ctx)

        # Should handle missing query
        assert result["llm_fallback_successful"] is False
        assert "error" in result
        assert "user_query" in result["error"]

        # Verify warning logged
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_service_exception(self, mock_logger, mock_rag_log, mock_low_confidence_context):
        """Test Step 35: Handle service exceptions"""
        from app.orchestrators.classify import step_35__llm_fallback

        # Mock the DomainActionClassifier service to raise exception
        mock_classifier = MagicMock()
        mock_classifier._llm_fallback_classification = AsyncMock(side_effect=Exception("LLM service error"))

        result = await step_35__llm_fallback(ctx=mock_low_confidence_context, classifier=mock_classifier)

        # Should handle exception gracefully
        assert result["llm_fallback_successful"] is False
        assert result["fallback_to_rule_based"] is True
        assert "service_error" in result
        assert "LLM service error" in result["service_error"]

        # Verify error logging
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_query_preprocessing(self, mock_logger, mock_rag_log, mock_llm_classification):
        """Test Step 35: Query preprocessing for LLM classification"""
        from app.orchestrators.classify import step_35__llm_fallback

        # Context with query needing preprocessing
        ctx = {
            "user_query": "  \n\t Come posso gestire la mia situazione fiscale?  \n  ",
            "rule_based_classification": None,
            "rule_based_confidence": 0.3,
            "request_id": "req_preprocess",
        }

        mock_classifier = MagicMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_llm_classification)

        result = await step_35__llm_fallback(ctx=ctx, classifier=mock_classifier)

        # Should preprocess and use clean query
        mock_classifier._llm_fallback_classification.assert_called_once()
        called_query = mock_classifier._llm_fallback_classification.call_args[0][0]
        assert called_query == "Come posso gestire la mia situazione fiscale?"  # Cleaned
        assert result["preprocessing_applied"] is True
        assert result["original_query"] == ctx["user_query"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_confidence_improvement_analysis(
        self, mock_logger, mock_rag_log, mock_low_confidence_context, mock_llm_classification
    ):
        """Test Step 35: Analyze confidence improvement from LLM"""
        from app.orchestrators.classify import step_35__llm_fallback

        mock_classifier = MagicMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_llm_classification)

        result = await step_35__llm_fallback(ctx=mock_low_confidence_context, classifier=mock_classifier)

        # Should analyze confidence improvement
        assert "confidence_analysis" in result
        analysis = result["confidence_analysis"]
        assert analysis["rule_based_confidence"] == 0.45
        assert analysis["llm_confidence"] == 0.87
        assert analysis["improvement"] == 0.42
        assert analysis["significant_improvement"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_ready_for_step_36(
        self, mock_logger, mock_rag_log, mock_low_confidence_context, mock_llm_classification
    ):
        """Test Step 35: Output ready for Step 36 (LLMBetter)"""
        from app.orchestrators.classify import step_35__llm_fallback

        mock_classifier = MagicMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_llm_classification)

        result = await step_35__llm_fallback(ctx=mock_low_confidence_context, classifier=mock_classifier)

        # Verify output is ready for Step 36
        assert result["ready_for_comparison"] is True
        assert "llm_classification" in result
        assert "rule_based_classification" in result
        assert result["next_step"] == "LLMBetter"

        # These fields needed for Step 36 comparison
        assert result["llm_classification"] is not None
        assert result["rule_based_classification"] is not None
        assert "confidence_analysis" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_comprehensive_logging(
        self, mock_logger, mock_rag_log, mock_low_confidence_context, mock_llm_classification
    ):
        """Test Step 35: Comprehensive logging format"""
        from app.orchestrators.classify import step_35__llm_fallback

        mock_classifier = MagicMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_llm_classification)

        await step_35__llm_fallback(ctx=mock_low_confidence_context, classifier=mock_classifier)

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
            "llm_fallback_successful",
            "classification_method",
            "improved_confidence",
            "processing_stage",
            "next_step",
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]["step"] == 35
        assert log_call[1]["step_id"] == "RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification"
        assert log_call[1]["node_label"] == "LLMFallback"

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_performance_tracking(
        self, mock_logger, mock_rag_log, mock_low_confidence_context, mock_llm_classification
    ):
        """Test Step 35: Performance tracking with timer"""
        from app.orchestrators.classify import step_35__llm_fallback

        with patch("app.orchestrators.classify.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_classifier = MagicMock()
            mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_llm_classification)

            await step_35__llm_fallback(ctx=mock_low_confidence_context, classifier=mock_classifier)

            # Verify timer was used
            mock_timer.assert_called_with(
                35,
                "RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification",
                "LLMFallback",
                stage="start",
            )

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_parity_preservation(self, mock_logger, mock_rag_log, mock_low_confidence_context):
        """Test Step 35: Parity test - behavior identical to direct service call"""
        from app.orchestrators.classify import step_35__llm_fallback
        from app.services.domain_action_classifier import DomainActionClassifier

        # Get direct service result
        classifier = DomainActionClassifier()
        direct_result = await classifier._llm_fallback_classification(mock_low_confidence_context["user_query"])

        # Call orchestrator
        mock_classifier = MagicMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=direct_result)

        orchestrator_result = await step_35__llm_fallback(ctx=mock_low_confidence_context, classifier=mock_classifier)

        # Verify core classification behavior is preserved
        if direct_result:
            assert orchestrator_result["llm_classification"] == direct_result
            assert orchestrator_result["llm_fallback_successful"] is True
        else:
            assert orchestrator_result["llm_fallback_successful"] is False
            assert orchestrator_result["fallback_to_rule_based"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.classify.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_35_integration_flow(self, mock_logger, mock_rag_log, mock_llm_classification):
        """Test Step 35: Integration flow from Step 33 to Step 36"""
        from app.orchestrators.classify import step_35__llm_fallback

        # Simulate Step 33 output (low confidence)
        step_33_output = {
            "confidence_check_passed": False,
            "confidence_below_threshold": True,
            "user_query": "Domanda fiscale complessa",
            "rule_based_classification": DomainActionClassification(
                domain=Domain.TAX,
                action=Action.INFORMATION_REQUEST,
                confidence=0.4,
                sub_domain="generale",
                document_type=None,
                reasoning="Low confidence",
            ),
            "next_step": "LLMFallback",
            "request_id": "req_integration",
        }

        mock_classifier = MagicMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_llm_classification)

        # Call Step 35 with Step 33 output
        step_35_output = await step_35__llm_fallback(ctx=step_33_output, classifier=mock_classifier)

        # Verify Step 35 output is compatible with Step 36 input
        assert step_35_output["ready_for_comparison"] is True
        assert step_35_output["next_step"] == "LLMBetter"
        assert step_35_output["llm_classification"] == mock_llm_classification
        assert step_35_output["rule_based_classification"] == step_33_output["rule_based_classification"]

        # Verify the flow preserves request tracking
        assert step_35_output["request_id"] == step_33_output["request_id"]
