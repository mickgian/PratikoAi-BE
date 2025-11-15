"""
Test Suite for RAG Step 119: ExpertFeedbackCollector.collect_feedback
Process orchestrator that collects expert feedback and routes to credential validation.

Following MASTER_GUARDRAILS methodology:
- Unit tests: Core functionality, error handling, context preservation
- Parity tests: Behavioral consistency before/after orchestrator
- Integration tests: Step 116/117/118→119, 119→120, and full pipeline flows
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the orchestrator function
from app.orchestrators.metrics import step_119__expert_feedback_collector


class TestRAGStep119ExpertFeedbackCollector:
    """Unit tests for Step 119 expert feedback collector orchestrator."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_basic_expert_feedback_collection(self, mock_rag_log):
        """Test Step 119: Basic expert feedback collection."""
        ctx = {
            "feedback_data": {
                "query_id": "query_123",
                "expert_id": "expert_456",
                "feedback_type": "incorrect",
                "category": "interpretazione_errata",
                "expert_answer": "The correct interpretation is...",
                "confidence_score": 0.9,
            },
            "user_id": "user_789",
            "session_id": "session_012",
        }

        result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

        # Verify result structure and routing
        assert result is not None
        assert result["expert_feedback_collected"] is True
        assert result["feedback_id"] is not None
        assert result["next_step"] == "validate_expert_credentials"  # Routes to Step 120
        assert result["expert_id"] == "expert_456"
        assert result["feedback_type"] == "incorrect"

        # Verify context preservation
        assert result["user_id"] == "user_789"
        assert result["session_id"] == "session_012"
        assert result["feedback_data"]["query_id"] == "query_123"

        # Verify logging
        mock_rag_log.assert_called()
        assert any("expert_feedback_collected" in str(call) for call in mock_rag_log.call_args_list)

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_feedback_types_processing(self, mock_rag_log):
        """Test Step 119: Different feedback types processing."""
        test_cases = [
            {"feedback_type": "correct", "category": None, "expected_priority": "normal"},
            {"feedback_type": "incomplete", "category": "caso_mancante", "expected_priority": "high"},
            {"feedback_type": "incorrect", "category": "calcolo_sbagliato", "expected_priority": "high"},
        ]

        for test_case in test_cases:
            ctx = {
                "feedback_data": {
                    "query_id": "query_456",
                    "expert_id": "expert_789",
                    "feedback_type": test_case["feedback_type"],
                    "category": test_case["category"],
                    "confidence_score": 0.8,
                }
            }

            result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

            assert result["expert_feedback_collected"] is True
            assert result["feedback_type"] == test_case["feedback_type"]
            assert result["next_step"] == "validate_expert_credentials"
            assert result["feedback_priority"] == test_case["expected_priority"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_preserves_context_data(self, mock_rag_log):
        """Test Step 119: Preserves all context data while adding feedback metadata."""
        ctx = {
            "request_id": "req_12345",
            "user_query": "original query about taxes",
            "classification_data": {"domain": "tax", "confidence": 0.85},
            "feedback_routing_decision": "expert_feedback",
            "feedback_data": {
                "query_id": "query_789",
                "expert_id": "expert_012",
                "feedback_type": "incomplete",
                "expert_answer": "Additional information needed...",
                "improvement_suggestions": ["Add more examples", "Include recent changes"],
            },
            "session_metadata": {"start_time": "2024-01-01T10:00:00Z"},
        }

        result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

        # Verify context preservation
        assert result["request_id"] == "req_12345"
        assert result["user_query"] == "original query about taxes"
        assert result["classification_data"] == {"domain": "tax", "confidence": 0.85}
        assert result["feedback_routing_decision"] == "expert_feedback"
        assert result["session_metadata"] == {"start_time": "2024-01-01T10:00:00Z"}

        # Verify feedback processing
        assert result["expert_feedback_collected"] is True
        assert result["feedback_id"] is not None
        assert result["expert_id"] == "expert_012"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_logs_feedback_processing_details(self, mock_rag_log):
        """Test Step 119: Logs comprehensive feedback processing details."""
        ctx = {
            "feedback_data": {
                "query_id": "query_999",
                "expert_id": "expert_999",
                "feedback_type": "correct",
                "time_spent_seconds": 45,
                "confidence_score": 0.95,
            }
        }

        await step_119__expert_feedback_collector(messages=[], ctx=ctx)

        # Verify logging calls contain expected details
        mock_rag_log.assert_called()
        log_calls = [str(call) for call in mock_rag_log.call_args_list]

        # Check for specific log attributes
        assert any("expert_id" in call for call in log_calls)
        assert any("feedback_type" in call for call in log_calls)
        assert any("validate_expert_credentials" in call for call in log_calls)

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_feedback_performance_tracking(self, mock_rag_log):
        """Test Step 119: Tracks feedback collection performance and timing."""
        ctx = {
            "feedback_data": {
                "query_id": "query_111",
                "expert_id": "expert_111",
                "feedback_type": "incorrect",
                "time_spent_seconds": 120,
            }
        }

        result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

        # Verify performance tracking
        assert "feedback_processing_time_ms" in result
        assert isinstance(result["feedback_processing_time_ms"], int | float)
        assert result["feedback_processing_time_ms"] >= 0

        # Verify successful collection tracking
        assert result["expert_feedback_collected"] is True
        assert result["collection_status"] == "success"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_error_handling_missing_feedback_data(self, mock_rag_log):
        """Test Step 119: Handle missing or invalid feedback data gracefully."""
        ctx = {
            "user_id": "user_123",
            "session_id": "session_123",
            # Missing feedback_data
        }

        result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

        # Should handle gracefully and still route to validate expert credentials
        assert result["expert_feedback_collected"] is False
        assert result["next_step"] == "validate_expert_credentials"
        assert result["error_type"] == "missing_feedback_data"
        assert "error_message" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_error_handling_invalid_expert(self, mock_rag_log):
        """Test Step 119: Handle invalid expert ID gracefully."""
        ctx = {
            "feedback_data": {
                "query_id": "query_123",
                "expert_id": "",  # Invalid expert ID
                "feedback_type": "correct",
            }
        }

        result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

        # Should handle gracefully
        assert result["expert_feedback_collected"] is False
        assert result["next_step"] == "validate_expert_credentials"
        assert result["error_type"] == "invalid_expert_id"

        # Verify error logging
        mock_rag_log.assert_called()
        assert mock_rag_log.call_count >= 2  # started and completed/error calls

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_expert_trust_scoring(self, mock_rag_log):
        """Test Step 119: Expert trust scoring and validation preparation."""
        ctx = {
            "feedback_data": {
                "query_id": "query_222",
                "expert_id": "expert_222",
                "feedback_type": "incorrect",
                "confidence_score": 0.8,
            },
            "expert_user": True,  # Expert user context
            "expert_trust_score": 0.85,
        }

        result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

        # Should prepare trust score validation
        assert result["expert_feedback_collected"] is True
        assert result["expert_validation_required"] is True
        assert result["expert_trust_score"] == 0.85
        assert result["next_step"] == "validate_expert_credentials"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_italian_category_processing(self, mock_rag_log):
        """Test Step 119: Italian feedback category processing."""
        italian_categories = [
            "normativa_obsoleta",
            "interpretazione_errata",
            "caso_mancante",
            "calcolo_sbagliato",
            "troppo_generico",
        ]

        for category in italian_categories:
            ctx = {
                "feedback_data": {
                    "query_id": "query_333",
                    "expert_id": "expert_333",
                    "feedback_type": "incorrect",
                    "category": category,
                }
            }

            result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

            assert result["expert_feedback_collected"] is True
            assert result["feedback_category"] == category
            assert result["category_localized"] is True  # Italian category detected
            assert result["next_step"] == "validate_expert_credentials"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_feedback_routing_consistency(self, mock_rag_log):
        """Test Step 119: Ensures consistent routing to Step 120 regardless of feedback source."""
        input_sources = [
            {"source": "feedback_type_sel", "feedback_routing_decision": "expert_feedback"},
            {"source": "faq_feedback", "faq_feedback_submitted": True},
            {"source": "knowledge_feedback", "knowledge_feedback_submitted": True},
        ]

        for source_ctx in input_sources:
            ctx = {
                **source_ctx,
                "feedback_data": {"query_id": "query_444", "expert_id": "expert_444", "feedback_type": "incomplete"},
            }

            result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

            # All feedback should route to expert credential validation
            assert result["next_step"] == "validate_expert_credentials"
            assert result["expert_feedback_collected"] is True


class TestRAGStep119Parity:
    """Parity tests ensuring behavioral consistency before/after orchestrator."""

    @pytest.mark.asyncio
    async def test_step_119_parity_feedback_collection_structure(self):
        """Test Step 119: Maintains consistent output structure for expert feedback."""
        ctx = {
            "feedback_data": {
                "query_id": "query_555",
                "expert_id": "expert_555",
                "feedback_type": "correct",
                "confidence_score": 0.9,
            },
            "user_id": "user_555",
            "session_id": "session_555",
        }

        result = await step_119__expert_feedback_collector(messages=[], ctx=ctx)

        # Verify expected output structure matches service expectations
        expected_fields = [
            "expert_feedback_collected",
            "feedback_id",
            "expert_id",
            "feedback_type",
            "next_step",
            "collection_status",
            "user_id",
            "session_id",
        ]

        for field in expected_fields:
            assert field in result, f"Expected field '{field}' missing from result"

        # Verify routing consistency
        assert result["next_step"] == "validate_expert_credentials"


class TestRAGStep119Integration:
    """Integration tests for Step 119 with neighboring steps."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.step_116__feedback_type_sel")
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_116_to_119_integration(self, mock_rag_log, mock_step_116):
        """Test Step 116→119: Feedback type selection routes to expert feedback collector."""
        # Mock Step 116 routing directly to Step 119
        mock_step_116.return_value = {
            "feedback_routing_decision": "expert_feedback",
            "next_step": "expert_feedback_collector",
            "feedback_data": {"query_id": "query_666", "expert_id": "expert_666", "feedback_type": "incorrect"},
            "routing_reason": "expert_feedback_priority",
        }

        # Call Step 116 first
        step_116_result = await mock_step_116(messages=[], ctx={"feedback_type": "expert", "expert_user": True})

        # Then call Step 119 with Step 116's output
        step_119_result = await step_119__expert_feedback_collector(messages=[], ctx=step_116_result)

        # Verify integration flow
        assert step_116_result["next_step"] == "expert_feedback_collector"
        assert step_119_result["expert_feedback_collected"] is True
        assert step_119_result["next_step"] == "validate_expert_credentials"
        assert step_119_result["expert_id"] == "expert_666"

    @pytest.mark.asyncio
    @patch("app.orchestrators.kb.step_118__knowledge_feedback")
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_118_to_119_integration(self, mock_rag_log, mock_step_118):
        """Test Step 118→119: Knowledge feedback routes to expert feedback collector."""
        # Mock Step 118 knowledge feedback
        mock_step_118.return_value = {
            "knowledge_feedback_submitted": True,
            "next_step": "expert_feedback_collector",
            "feedback_data": {
                "query_id": "query_777",
                "expert_id": "expert_777",
                "feedback_type": "incomplete",
                "knowledge_item_id": 123,
            },
        }

        # Call Step 118 first
        step_118_result = await mock_step_118(messages=[], ctx={"feedback_data": {"knowledge_item_id": 123}})

        # Then call Step 119 with Step 118's output
        step_119_result = await step_119__expert_feedback_collector(messages=[], ctx=step_118_result)

        # Verify integration flow
        assert step_118_result["next_step"] == "expert_feedback_collector"
        assert step_119_result["expert_feedback_collected"] is True
        assert step_119_result["next_step"] == "validate_expert_credentials"
        assert step_119_result["expert_id"] == "expert_777"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_to_120_integration(self, mock_rag_log):
        """Test Step 119→120: Expert feedback collector routes to credential validation."""
        # Call Step 119
        step_119_result = await step_119__expert_feedback_collector(
            messages=[],
            ctx={"feedback_data": {"query_id": "query_888", "expert_id": "expert_888", "feedback_type": "correct"}},
        )

        # Verify Step 119 prepares proper routing to Step 120
        assert step_119_result["next_step"] == "validate_expert_credentials"
        assert step_119_result["expert_feedback_collected"] is True
        assert step_119_result["expert_id"] == "expert_888"

        # Verify all context is preserved for Step 120
        assert "feedback_data" in step_119_result
        assert step_119_result["feedback_data"]["expert_id"] == "expert_888"

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.step_116__feedback_type_sel")
    @patch("app.orchestrators.kb.step_118__knowledge_feedback")
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_full_expert_feedback_pipeline(self, mock_rag_log, mock_step_118, mock_step_116):
        """Test Step 116→118→119→120: Full expert feedback pipeline integration."""
        # Mock Step 116
        mock_step_116.return_value = {
            "feedback_routing_decision": "knowledge_feedback",
            "next_step": "knowledge_feedback_endpoint",
            "feedback_data": {"query_id": "query_999", "expert_id": "expert_999", "feedback_type": "incorrect"},
        }

        # Mock Step 118
        mock_step_118.return_value = {
            "knowledge_feedback_submitted": True,
            "next_step": "expert_feedback_collector",
            "feedback_routing_decision": "knowledge_feedback",  # Preserve from Step 116
            "feedback_data": {"query_id": "query_999", "expert_id": "expert_999", "feedback_type": "incorrect"},
        }

        # Execute pipeline through Step 119
        step_116_result = await mock_step_116(messages=[], ctx={"feedback_type": "kb"})
        step_118_result = await mock_step_118(messages=[], ctx=step_116_result)
        step_119_result = await step_119__expert_feedback_collector(messages=[], ctx=step_118_result)

        # Verify full pipeline flow through Step 119
        assert step_116_result["feedback_routing_decision"] == "knowledge_feedback"
        assert step_118_result["knowledge_feedback_submitted"] is True
        assert step_119_result["expert_feedback_collected"] is True
        assert step_119_result["next_step"] == "validate_expert_credentials"

        # Verify Step 119 preserves pipeline context
        assert step_119_result["feedback_routing_decision"] == "knowledge_feedback"
        assert step_119_result["knowledge_feedback_submitted"] is True
        assert step_119_result["expert_id"] == "expert_999"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    async def test_step_119_multiple_feedback_scenarios(self, mock_rag_log):
        """Test Step 119: Multiple expert feedback scenarios in sequence."""
        test_scenarios = [
            {
                "name": "direct_expert_feedback",
                "ctx": {
                    "feedback_routing_decision": "expert_feedback",
                    "feedback_data": {"query_id": "query_000", "expert_id": "expert_000", "feedback_type": "correct"},
                },
                "expected_validation": True,
            },
            {
                "name": "faq_expert_feedback",
                "ctx": {
                    "faq_feedback_submitted": True,
                    "feedback_data": {
                        "query_id": "query_000",
                        "expert_id": "expert_000",
                        "feedback_type": "incomplete",
                    },
                },
                "expected_validation": True,
            },
            {
                "name": "knowledge_expert_feedback",
                "ctx": {
                    "knowledge_feedback_submitted": True,
                    "feedback_data": {
                        "query_id": "query_000",
                        "expert_id": "expert_000",
                        "feedback_type": "incorrect",
                    },
                },
                "expected_validation": True,
            },
        ]

        for scenario in test_scenarios:
            result = await step_119__expert_feedback_collector(messages=[], ctx=scenario["ctx"])

            assert result["expert_feedback_collected"] is True
            assert result["next_step"] == "validate_expert_credentials"
            assert result["expert_id"] == "expert_000"

            if scenario["expected_validation"]:
                assert result["expert_validation_required"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
