"""
Test suite for RAG STEP 37 - Use LLM classification

This module tests the orchestration function step_37__use_llm which applies
LLM classification results as the final classification when Step 36 determines
LLM is better than rule-based classification.

According to the RAG workflow and GitHub issue 582:
- Takes LLM classification from context
- Applies it as the final classification result
- Tracks metrics and updates context for next steps
- Thin orchestration that preserves existing behavior
"""

from unittest.mock import patch

import pytest

from app.orchestrators.llm import step_37__use_llm


class TestRAGStep37UseLLM:
    """Test suite for RAG STEP 37 - Use LLM classification"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_use_llm_classification_success(self, mock_logger, mock_rag_log):
        """Test Step 37: Successfully applies LLM classification"""

        ctx = {
            "request_id": "test-request-123",
            "llm_classification": {
                "domain": "tax",
                "action": "calculation_request",
                "confidence": 0.85,
                "fallback_used": True,
                "reasoning": "LLM identified tax calculation request",
                "sub_domain": "income_tax",
                "document_type": None,
            },
        }

        # Call the orchestrator function
        result = await step_37__use_llm(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["classification_applied"] is True
        assert result["final_classification"]["domain"] == "tax"
        assert result["final_classification"]["action"] == "calculation_request"
        assert result["final_classification"]["confidence"] == 0.85
        assert result["final_classification"]["fallback_used"] is True
        assert result["classification_source"] == "llm"
        assert result["request_id"] == "test-request-123"
        assert "timestamp" in result

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Applying LLM classification as final result" in log_call[0][0]
        assert log_call[1]["extra"]["classification_source"] == "llm"

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_use_llm_with_high_confidence(self, mock_logger, mock_rag_log):
        """Test Step 37: High confidence LLM classification"""

        ctx = {
            "request_id": "test-request-high-conf",
            "llm_classification": {
                "domain": "legal",
                "action": "document_analysis",
                "confidence": 0.95,
                "fallback_used": True,
                "reasoning": "High confidence legal document analysis",
                "sub_domain": "contract_law",
                "document_type": "contract",
            },
        }

        result = await step_37__use_llm(ctx=ctx)

        assert result["classification_applied"] is True
        assert result["final_classification"]["confidence"] == 0.95
        assert result["final_classification"]["domain"] == "legal"
        assert result["confidence_level"] == "high"  # >= 0.8

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_use_llm_with_medium_confidence(self, mock_logger, mock_rag_log):
        """Test Step 37: Medium confidence LLM classification"""

        ctx = {
            "request_id": "test-request-medium-conf",
            "llm_classification": {
                "domain": "hr",
                "action": "policy_inquiry",
                "confidence": 0.70,
                "fallback_used": True,
                "reasoning": "Medium confidence HR policy inquiry",
            },
        }

        result = await step_37__use_llm(ctx=ctx)

        assert result["classification_applied"] is True
        assert result["final_classification"]["confidence"] == 0.70
        assert result["confidence_level"] == "medium"  # 0.6 <= conf < 0.8

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_use_llm_with_low_confidence_warning(self, mock_logger, mock_rag_log):
        """Test Step 37: Low confidence LLM classification with warning"""

        ctx = {
            "request_id": "test-request-low-conf",
            "llm_classification": {
                "domain": "business",
                "action": "strategic_advice",
                "confidence": 0.55,
                "fallback_used": True,
                "reasoning": "Low confidence business strategy request",
            },
        }

        result = await step_37__use_llm(ctx=ctx)

        assert result["classification_applied"] is True
        assert result["final_classification"]["confidence"] == 0.55
        assert result["confidence_level"] == "low"  # < 0.6

        # Verify warning was logged for low confidence
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert "Low confidence LLM classification" in warning_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_missing_llm_classification_error(self, mock_logger, mock_rag_log):
        """Test Step 37: Error when LLM classification is missing"""

        ctx = {"request_id": "test-request-missing-llm"}

        result = await step_37__use_llm(ctx=ctx)

        assert result["classification_applied"] is False
        assert result["final_classification"] is None
        assert result["classification_source"] == "error"
        assert "No LLM classification available" in result["error"]

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_invalid_llm_classification_data(self, mock_logger, mock_rag_log):
        """Test Step 37: Error with invalid LLM classification data"""

        ctx = {
            "request_id": "test-request-invalid",
            "llm_classification": {
                "domain": None,  # Invalid - missing domain
                "confidence": 0.85,
                # Missing action
            },
        }

        result = await step_37__use_llm(ctx=ctx)

        assert result["classification_applied"] is False
        assert result["final_classification"] is None
        assert result["classification_source"] == "error"
        assert "Invalid LLM classification data" in result["error"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_kwargs_override_ctx(self, mock_logger, mock_rag_log):
        """Test Step 37: kwargs parameters override ctx parameters"""

        ctx = {
            "request_id": "test-request-ctx",
            "llm_classification": {"domain": "old_domain", "action": "old_action", "confidence": 0.50},
        }

        kwargs_llm = {"domain": "new_domain", "action": "new_action", "confidence": 0.90, "fallback_used": True}

        result = await step_37__use_llm(ctx=ctx, llm_classification=kwargs_llm)

        assert result["classification_applied"] is True
        assert result["final_classification"]["domain"] == "new_domain"  # From kwargs, not ctx
        assert result["final_classification"]["confidence"] == 0.90

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_preserves_additional_llm_metadata(self, mock_logger, mock_rag_log):
        """Test Step 37: Preserves additional LLM classification metadata"""

        ctx = {
            "request_id": "test-request-metadata",
            "llm_classification": {
                "domain": "accounting",
                "action": "compliance_check",
                "confidence": 0.88,
                "fallback_used": True,
                "reasoning": "Detected accounting compliance requirements",
                "sub_domain": "financial_reporting",
                "document_type": "financial_statement",
                "model_version": "gpt-4",
                "processing_time_ms": 1250,
            },
        }

        result = await step_37__use_llm(ctx=ctx)

        final_classification = result["final_classification"]
        assert final_classification["reasoning"] == "Detected accounting compliance requirements"
        assert final_classification["sub_domain"] == "financial_reporting"
        assert final_classification["document_type"] == "financial_statement"
        assert final_classification["model_version"] == "gpt-4"
        assert final_classification["processing_time_ms"] == 1250

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_tracks_classification_metrics(self, mock_logger, mock_rag_log):
        """Test Step 37: Tracks classification metrics for monitoring"""

        ctx = {
            "request_id": "test-request-metrics",
            "llm_classification": {
                "domain": "payroll",
                "action": "salary_calculation",
                "confidence": 0.92,
                "fallback_used": True,
            },
        }

        result = await step_37__use_llm(ctx=ctx)

        # Verify metrics are tracked
        assert "metrics" in result
        metrics = result["metrics"]
        assert metrics["classification_method"] == "llm"
        assert metrics["confidence_score"] == 0.92
        assert metrics["domain"] == "payroll"
        assert metrics["action"] == "salary_calculation"
        assert "application_timestamp" in metrics

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_integration_flow_context_preservation(self, mock_logger, mock_rag_log):
        """Test Step 37: Integration test ensuring context is preserved for next steps"""

        ctx = {
            "request_id": "test-integration-37",
            "user_message": "Calculate my 2023 tax deductions",
            "canonical_facts": ["tax", "2023", "deductions", "calculate"],
            "rule_based_classification": {
                "domain": "tax",
                "action": "information_request",
                "confidence": 0.65,
                "fallback_used": False,
            },
            "llm_classification": {
                "domain": "tax",
                "action": "calculation_request",
                "confidence": 0.87,
                "fallback_used": True,
                "reasoning": "User requesting tax calculation for deductions",
            },
            "llm_better_decision": {"llm_better": True, "confidence_improvement": 0.22},
        }

        result = await step_37__use_llm(ctx=ctx)

        # Verify LLM classification was applied
        assert result["classification_applied"] is True
        assert result["final_classification"]["action"] == "calculation_request"  # LLM result, not rule-based

        # Verify context preservation for next steps
        assert result["request_id"] == "test-integration-37"
        assert "timestamp" in result

        # Verify rag_step_log was called with proper parameters
        assert mock_rag_log.call_count >= 2  # start and completed calls
        start_call = mock_rag_log.call_args_list[0][1]
        assert start_call["step"] == 37
        assert start_call["step_id"] == "RAG.llm.use.llm.classification"
        assert start_call["node_label"] == "UseLLM"
        assert start_call["category"] == "llm"
        assert start_call["type"] == "process"
        assert start_call["processing_stage"] == "started"

    @pytest.mark.asyncio
    @patch("app.orchestrators.llm.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_37_parity_test_behavior_preservation(self, mock_logger, mock_rag_log):
        """Test Step 37: Parity test proving identical behavior before/after orchestrator"""

        # Test data representing what would have been direct LLM classification usage
        llm_classification_data = {
            "domain": "legal",
            "action": "document_generation",
            "confidence": 0.82,
            "fallback_used": True,
            "reasoning": "Legal document generation request identified",
            "sub_domain": "corporate_law",
        }

        ctx = {"request_id": "parity-test-123", "llm_classification": llm_classification_data}

        result = await step_37__use_llm(ctx=ctx)

        # Verify that the orchestrator preserves the exact same classification data
        final_classification = result["final_classification"]
        assert final_classification["domain"] == llm_classification_data["domain"]
        assert final_classification["action"] == llm_classification_data["action"]
        assert final_classification["confidence"] == llm_classification_data["confidence"]
        assert final_classification["fallback_used"] == llm_classification_data["fallback_used"]
        assert final_classification["reasoning"] == llm_classification_data["reasoning"]
        assert final_classification["sub_domain"] == llm_classification_data["sub_domain"]

        # Verify the orchestrator adds coordination metadata without changing core behavior
        assert result["classification_applied"] is True
        assert result["classification_source"] == "llm"
        assert "metrics" in result
        assert "timestamp" in result
