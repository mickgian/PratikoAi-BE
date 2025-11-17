"""
Test suite for RAG STEP 38 - Use rule-based classification

This module tests the orchestration function step_38__use_rule_based which applies
rule-based classification results as the final classification when Step 36 determines
rule-based is better than LLM classification.

According to the RAG workflow and GitHub issue 583:
- Takes rule-based classification from context
- Applies it as the final classification result
- Tracks metrics and updates context for next steps
- Thin orchestration that preserves existing behavior
"""

from unittest.mock import patch

import pytest

from app.orchestrators.platform import step_38__use_rule_based


class TestRAGStep38UseRuleBased:
    """Test suite for RAG STEP 38 - Use rule-based classification"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_use_rule_based_classification_success(self, mock_logger, mock_rag_log):
        """Test Step 38: Successfully applies rule-based classification"""

        ctx = {
            "request_id": "test-request-123",
            "rule_based_classification": {
                "domain": "tax",
                "action": "information_request",
                "confidence": 0.85,
                "fallback_used": False,
                "reasoning": "Rule-based identified tax information request",
                "sub_domain": "income_tax",
                "document_type": None,
            },
        }

        # Call the orchestrator function
        result = await step_38__use_rule_based(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["classification_applied"] is True
        assert result["final_classification"]["domain"] == "tax"
        assert result["final_classification"]["action"] == "information_request"
        assert result["final_classification"]["confidence"] == 0.85
        assert result["final_classification"]["fallback_used"] is False
        assert result["classification_source"] == "rule_based"
        assert result["request_id"] == "test-request-123"
        assert "timestamp" in result

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Applying rule-based classification as final result" in log_call[0][0]
        assert log_call[1]["extra"]["classification_source"] == "rule_based"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_use_rule_based_with_high_confidence(self, mock_logger, mock_rag_log):
        """Test Step 38: High confidence rule-based classification"""

        ctx = {
            "request_id": "test-request-high-conf",
            "rule_based_classification": {
                "domain": "legal",
                "action": "document_analysis",
                "confidence": 0.95,
                "fallback_used": False,
                "reasoning": "High confidence legal document analysis",
                "sub_domain": "contract_law",
                "document_type": "contract",
            },
        }

        result = await step_38__use_rule_based(ctx=ctx)

        assert result["classification_applied"] is True
        assert result["final_classification"]["confidence"] == 0.95
        assert result["final_classification"]["domain"] == "legal"
        assert result["confidence_level"] == "high"  # >= 0.8

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_use_rule_based_with_medium_confidence(self, mock_logger, mock_rag_log):
        """Test Step 38: Medium confidence rule-based classification"""

        ctx = {
            "request_id": "test-request-medium-conf",
            "rule_based_classification": {
                "domain": "hr",
                "action": "policy_inquiry",
                "confidence": 0.70,
                "fallback_used": False,
                "reasoning": "Medium confidence HR policy inquiry",
            },
        }

        result = await step_38__use_rule_based(ctx=ctx)

        assert result["classification_applied"] is True
        assert result["final_classification"]["confidence"] == 0.70
        assert result["confidence_level"] == "medium"  # 0.6 <= conf < 0.8

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_use_rule_based_with_low_confidence_warning(self, mock_logger, mock_rag_log):
        """Test Step 38: Low confidence rule-based classification with warning"""

        ctx = {
            "request_id": "test-request-low-conf",
            "rule_based_classification": {
                "domain": "business",
                "action": "strategic_advice",
                "confidence": 0.55,
                "fallback_used": False,
                "reasoning": "Low confidence business strategy request",
            },
        }

        result = await step_38__use_rule_based(ctx=ctx)

        assert result["classification_applied"] is True
        assert result["final_classification"]["confidence"] == 0.55
        assert result["confidence_level"] == "low"  # < 0.6

        # Verify warning was logged for low confidence
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert "Low confidence rule-based classification" in warning_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_missing_rule_based_classification_error(self, mock_logger, mock_rag_log):
        """Test Step 38: Error when rule-based classification is missing"""

        ctx = {"request_id": "test-request-missing-rule-based"}

        result = await step_38__use_rule_based(ctx=ctx)

        assert result["classification_applied"] is False
        assert result["final_classification"] is None
        assert result["classification_source"] == "error"
        assert "No rule-based classification available" in result["error"]

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_invalid_rule_based_classification_data(self, mock_logger, mock_rag_log):
        """Test Step 38: Error with invalid rule-based classification data"""

        ctx = {
            "request_id": "test-request-invalid",
            "rule_based_classification": {
                "domain": None,  # Invalid - missing domain
                "confidence": 0.85,
                # Missing action
            },
        }

        result = await step_38__use_rule_based(ctx=ctx)

        assert result["classification_applied"] is False
        assert result["final_classification"] is None
        assert result["classification_source"] == "error"
        assert "Invalid rule-based classification data" in result["error"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_kwargs_override_ctx(self, mock_logger, mock_rag_log):
        """Test Step 38: kwargs parameters override ctx parameters"""

        ctx = {
            "request_id": "test-request-ctx",
            "rule_based_classification": {"domain": "old_domain", "action": "old_action", "confidence": 0.50},
        }

        kwargs_rule_based = {
            "domain": "new_domain",
            "action": "new_action",
            "confidence": 0.90,
            "fallback_used": False,
        }

        result = await step_38__use_rule_based(ctx=ctx, rule_based_classification=kwargs_rule_based)

        assert result["classification_applied"] is True
        assert result["final_classification"]["domain"] == "new_domain"  # From kwargs, not ctx
        assert result["final_classification"]["confidence"] == 0.90

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_preserves_additional_rule_based_metadata(self, mock_logger, mock_rag_log):
        """Test Step 38: Preserves additional rule-based classification metadata"""

        ctx = {
            "request_id": "test-request-metadata",
            "rule_based_classification": {
                "domain": "accounting",
                "action": "compliance_check",
                "confidence": 0.88,
                "fallback_used": False,
                "reasoning": "Detected accounting compliance requirements",
                "sub_domain": "financial_reporting",
                "document_type": "financial_statement",
                "processing_time_ms": 450,
                "matched_keywords": ["compliance", "accounting", "financial"],
            },
        }

        result = await step_38__use_rule_based(ctx=ctx)

        final_classification = result["final_classification"]
        assert final_classification["reasoning"] == "Detected accounting compliance requirements"
        assert final_classification["sub_domain"] == "financial_reporting"
        assert final_classification["document_type"] == "financial_statement"
        assert final_classification["processing_time_ms"] == 450
        assert final_classification["matched_keywords"] == ["compliance", "accounting", "financial"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_tracks_classification_metrics(self, mock_logger, mock_rag_log):
        """Test Step 38: Tracks classification metrics for monitoring"""

        ctx = {
            "request_id": "test-request-metrics",
            "rule_based_classification": {
                "domain": "payroll",
                "action": "salary_calculation",
                "confidence": 0.92,
                "fallback_used": False,
            },
        }

        result = await step_38__use_rule_based(ctx=ctx)

        # Verify metrics are tracked
        assert "metrics" in result
        metrics = result["metrics"]
        assert metrics["classification_method"] == "rule_based"
        assert metrics["confidence_score"] == 0.92
        assert metrics["domain"] == "payroll"
        assert metrics["action"] == "salary_calculation"
        assert "application_timestamp" in metrics

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_integration_flow_context_preservation(self, mock_logger, mock_rag_log):
        """Test Step 38: Integration test ensuring context is preserved for next steps"""

        ctx = {
            "request_id": "test-integration-38",
            "user_message": "What are the labor regulations for overtime?",
            "canonical_facts": ["labor", "regulations", "overtime"],
            "rule_based_classification": {
                "domain": "labor",
                "action": "information_request",
                "confidence": 0.87,
                "fallback_used": False,
                "reasoning": "Rule-based identified labor regulations query",
            },
            "llm_classification": {
                "domain": "hr",
                "action": "policy_inquiry",
                "confidence": 0.65,
                "fallback_used": True,
            },
            "llm_better_decision": {"llm_better": False, "confidence_improvement": -0.22},
        }

        result = await step_38__use_rule_based(ctx=ctx)

        # Verify rule-based classification was applied
        assert result["classification_applied"] is True
        assert result["final_classification"]["domain"] == "labor"  # Rule-based result, not LLM

        # Verify context preservation for next steps
        assert result["request_id"] == "test-integration-38"
        assert "timestamp" in result

        # Verify rag_step_log was called with proper parameters
        assert mock_rag_log.call_count >= 2  # start and completed calls
        start_call = mock_rag_log.call_args_list[0][1]
        assert start_call["step"] == 38
        assert start_call["step_id"] == "RAG.platform.use.rule.based.classification"
        assert start_call["node_label"] == "UseRuleBased"
        assert start_call["category"] == "platform"
        assert start_call["type"] == "process"
        assert start_call["processing_stage"] == "started"

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.rag_step_log")
    @patch("app.core.logging.logger")
    async def test_step_38_parity_test_behavior_preservation(self, mock_logger, mock_rag_log):
        """Test Step 38: Parity test proving identical behavior before/after orchestrator"""

        # Test data representing what would have been direct rule-based classification usage
        rule_based_classification_data = {
            "domain": "legal",
            "action": "document_generation",
            "confidence": 0.82,
            "fallback_used": False,
            "reasoning": "Legal document generation request identified",
            "sub_domain": "corporate_law",
            "matched_keywords": ["legal", "document", "generate"],
        }

        ctx = {"request_id": "parity-test-123", "rule_based_classification": rule_based_classification_data}

        result = await step_38__use_rule_based(ctx=ctx)

        # Verify that the orchestrator preserves the exact same classification data
        final_classification = result["final_classification"]
        assert final_classification["domain"] == rule_based_classification_data["domain"]
        assert final_classification["action"] == rule_based_classification_data["action"]
        assert final_classification["confidence"] == rule_based_classification_data["confidence"]
        assert final_classification["fallback_used"] == rule_based_classification_data["fallback_used"]
        assert final_classification["reasoning"] == rule_based_classification_data["reasoning"]
        assert final_classification["sub_domain"] == rule_based_classification_data["sub_domain"]
        assert final_classification["matched_keywords"] == rule_based_classification_data["matched_keywords"]

        # Verify the orchestrator adds coordination metadata without changing core behavior
        assert result["classification_applied"] is True
        assert result["classification_source"] == "rule_based"
        assert "metrics" in result
        assert "timestamp" in result
