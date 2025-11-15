"""
Tests for RAG Step 115: FeedbackEnd (No feedback).

This step is a process node that handles the "no feedback" scenario.
Finalizes the feedback pipeline when no feedback is provided.
"""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep115FeedbackEnd:
    """Unit tests for Step 115: FeedbackEnd process logic."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_no_feedback_completion(self, mock_rag_log):
        """Test Step 115: Complete no feedback flow."""
        from app.orchestrators.feedback import step_115__feedback_end

        ctx = {
            "response_id": "response-no-feedback-123",
            "feedback_provided": False,
            "decision_reason": "no_user_feedback",
            "request_id": "test-115-completion",
            "user_id": "user-no-feedback",
        }

        result = await step_115__feedback_end(messages=[], ctx=ctx)

        # Verify completion processing
        assert result["feedback_pipeline_completed"] is True
        assert result["completion_reason"] == "no_feedback"
        assert result["processing_stage"] == "feedback_pipeline_ended"

        # Verify context preservation
        assert result["response_id"] == "response-no-feedback-123"
        assert result["feedback_provided"] is False
        assert result["user_id"] == "user-no-feedback"

        # Verify logging
        assert mock_rag_log.call_count == 2
        start_call = mock_rag_log.call_args_list[0]
        assert start_call[1]["processing_stage"] == "started"
        end_call = mock_rag_log.call_args_list[1]
        assert end_call[1]["processing_stage"] == "completed"
        assert end_call[1]["completion_reason"] == "no_feedback"

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_ui_not_displayed_completion(self, mock_rag_log):
        """Test Step 115: Complete flow when UI was not displayed."""
        from app.orchestrators.feedback import step_115__feedback_end

        ctx = {
            "response_id": "response-ui-disabled-456",
            "feedback_provided": False,
            "decision_reason": "feedback_ui_not_displayed",
            "feedback_disabled_reason": "anonymous_user_not_allowed",
            "request_id": "test-115-ui-disabled",
            "anonymous_user": True,
        }

        result = await step_115__feedback_end(messages=[], ctx=ctx)

        # Verify completion handling
        assert result["feedback_pipeline_completed"] is True
        assert result["completion_reason"] == "feedback_ui_not_available"
        assert result["feedback_disabled_reason"] == "anonymous_user_not_allowed"

        # Verify anonymous user handling
        assert result["anonymous_user"] is True
        assert result["feedback_provided"] is False

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_golden_approval_rejected(self, mock_rag_log):
        """Test Step 115: Handle Golden approval rejection flow."""
        from app.orchestrators.feedback import step_115__feedback_end

        ctx = {
            "response_id": "response-golden-rejected-789",
            "expert_feedback_processed": True,
            "golden_approval_status": "rejected",
            "rejection_reason": "quality_threshold_not_met",
            "expert_trust_score": 0.65,  # Below threshold
            "request_id": "test-115-golden-rejected",
        }

        result = await step_115__feedback_end(messages=[], ctx=ctx)

        # Verify rejection handling
        assert result["feedback_pipeline_completed"] is True
        assert result["completion_reason"] == "golden_approval_rejected"
        assert result["rejection_reason"] == "quality_threshold_not_met"
        assert result["expert_trust_score"] == 0.65

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_preserves_context_data(self, mock_rag_log):
        """Test Step 115: Preserves all context data while completing flow."""
        from app.orchestrators.feedback import step_115__feedback_end

        ctx = {
            "response_id": "response-preserve-999",
            "query_text": "Context preservation test",
            "feedback_provided": False,
            "request_id": "test-115-preserve",
            "user_id": "user-preserve",
            "session_id": "session-preserve",
            # Pipeline metadata that should be preserved
            "provider": "openai",
            "model": "gpt-4",
            "tokens_used": 200,
            "response_time_ms": 1500,
            "upstream_data": {"preserved": "data"},
            # Feedback flow metadata
            "feedback_ui_displayed": True,
            "feedback_options": ["correct", "incomplete", "wrong"],
            "decision_reason": "no_user_feedback",
        }

        result = await step_115__feedback_end(messages=[], ctx=ctx)

        # Verify completion output
        assert result["feedback_pipeline_completed"] is True
        assert result["completion_reason"] == "no_feedback"

        # Verify all original context preserved
        assert result["query_text"] == "Context preservation test"
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4"
        assert result["tokens_used"] == 200
        assert result["upstream_data"] == {"preserved": "data"}
        assert result["feedback_ui_displayed"] is True
        assert result["feedback_options"] == ["correct", "incomplete", "wrong"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_logs_completion_details(self, mock_rag_log):
        """Test Step 115: Logs comprehensive completion details."""
        from app.orchestrators.feedback import step_115__feedback_end

        ctx = {
            "response_id": "response-logging-test",
            "feedback_provided": False,
            "decision_reason": "session_timeout",
            "request_id": "test-115-logging",
            "processing_start_time": datetime.now(UTC),
        }

        await step_115__feedback_end(messages=[], ctx=ctx)

        # Verify comprehensive logging
        assert mock_rag_log.call_count == 2

        # Check start log
        start_call = mock_rag_log.call_args_list[0]
        assert start_call[1]["step"] == 115
        assert start_call[1]["node_label"] == "FeedbackEnd"
        assert start_call[1]["category"] == "feedback"
        assert start_call[1]["type"] == "process"

        # Check completion log
        end_call = mock_rag_log.call_args_list[1]
        assert end_call[1]["processing_stage"] == "completed"
        assert end_call[1]["completion_reason"] == "session_timeout"
        assert "completion_time_ms" in end_call[1]

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_anonymous_user_completion(self, mock_rag_log):
        """Test Step 115: Handle anonymous user completion."""
        from app.orchestrators.feedback import step_115__feedback_end

        ctx = {
            "response_id": "response-anon-555",
            "feedback_provided": False,
            "user_id": None,  # Anonymous user
            "anonymous_user": True,
            "decision_reason": "anonymous_user_timeout",
            "request_id": "test-115-anonymous",
        }

        result = await step_115__feedback_end(messages=[], ctx=ctx)

        assert result["feedback_pipeline_completed"] is True
        assert result["completion_reason"] == "anonymous_user_timeout"
        assert result["anonymous_user"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_expert_feedback_completed(self, mock_rag_log):
        """Test Step 115: Handle expert feedback completion scenarios."""
        from app.orchestrators.feedback import step_115__feedback_end

        ctx = {
            "response_id": "response-expert-completed",
            "expert_feedback_processed": True,
            "expert_user": True,
            "expert_trust_score": 0.95,
            "feedback_cache_invalidated": True,
            "completion_from_golden_flow": True,
            "request_id": "test-115-expert-complete",
        }

        result = await step_115__feedback_end(messages=[], ctx=ctx)

        assert result["feedback_pipeline_completed"] is True
        assert result["completion_reason"] == "expert_feedback_processed"
        assert result["expert_feedback_processed"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_error_recovery_completion(self, mock_rag_log):
        """Test Step 115: Handle error recovery and graceful completion."""
        from app.orchestrators.feedback import step_115__feedback_end

        ctx = {
            "response_id": "response-error-recovery",
            "feedback_processing_error": True,
            "error_details": "timeout_during_validation",
            "fallback_completion": True,
            "request_id": "test-115-error-recovery",
        }

        result = await step_115__feedback_end(messages=[], ctx=ctx)

        assert result["feedback_pipeline_completed"] is True
        assert result["completion_reason"] == "error_recovery"
        assert result["fallback_completion"] is True
        assert result["error_details"] == "timeout_during_validation"

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_metrics_finalization(self, mock_rag_log):
        """Test Step 115: Finalizes metrics and tracking."""
        from app.orchestrators.feedback import step_115__feedback_end

        ctx = {
            "response_id": "response-metrics-final",
            "feedback_provided": False,
            "session_duration_ms": 5000,
            "ui_display_time_ms": 1500,
            "decision_time_ms": 50,
            "processing_start_time": datetime.now(UTC) - timedelta(seconds=1),
            "request_id": "test-115-metrics",
        }

        result = await step_115__feedback_end(messages=[], ctx=ctx)

        # Verify metrics finalization
        assert result["feedback_pipeline_completed"] is True
        assert result["final_metrics_collected"] is True
        assert result["total_pipeline_time_ms"] > 0
        assert result["session_duration_ms"] == 5000

        # Check that completion metrics are logged
        end_call = mock_rag_log.call_args_list[1]
        assert "session_duration_ms" in end_call[1]
        assert "total_pipeline_time_ms" in end_call[1]


class TestRAGStep115Parity:
    """Parity tests ensuring Step 115 behavior is consistent."""

    @pytest.mark.asyncio
    async def test_step_115_parity_completion_structure(self):
        """Test Step 115 parity: completion output structure is consistent."""
        from app.orchestrators.feedback import step_115__feedback_end

        # Expected completion structure
        expected_keys = ["feedback_pipeline_completed", "completion_reason", "processing_stage"]

        # Test with no feedback
        ctx_no_feedback = {"feedback_provided": False, "response_id": "parity-test-no-feedback"}

        with patch("app.orchestrators.feedback.rag_step_log"):
            result_no_feedback = await step_115__feedback_end(messages=[], ctx=ctx_no_feedback)

        # Test with golden rejection
        ctx_golden_reject = {"golden_approval_status": "rejected", "response_id": "parity-test-golden-reject"}

        with patch("app.orchestrators.feedback.rag_step_log"):
            result_golden_reject = await step_115__feedback_end(messages=[], ctx=ctx_golden_reject)

        # Verify consistent structure
        for key in expected_keys:
            assert key in result_no_feedback
            assert key in result_golden_reject

        # Verify completion consistency
        assert result_no_feedback["feedback_pipeline_completed"] is True
        assert result_golden_reject["feedback_pipeline_completed"] is True


class TestRAGStep115Integration:
    """Integration tests for Step 115 with neighboring steps."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_114_to_115_integration(self, mock_rag_log):
        """Test integration: Step 114 (No feedback) → Step 115 (Feedback end)."""
        from app.orchestrators.feedback import step_114__feedback_provided, step_115__feedback_end

        # Step 114 context (no feedback provided)
        step_114_ctx = {
            "response_id": "integration-response-114-115",
            "request_id": "test-114-115-integration",
            "feedback_ui_displayed": True,
            "user_id": "integration-user-3",
        }

        step_114_result = await step_114__feedback_provided(messages=[], ctx=step_114_ctx)

        # Step 115 receives Step 114 output
        step_115_ctx = step_114_result.copy()

        step_115_result = await step_115__feedback_end(messages=[], ctx=step_115_ctx)

        # Verify integration flow
        assert step_115_result["feedback_provided"] is False  # From step 114
        assert step_115_result["next_step"] == "feedback_end"  # From step 114
        assert step_115_result["feedback_pipeline_completed"] is True  # From step 115
        assert step_115_result["response_id"] == "integration-response-114-115"

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_golden_approval_to_115_integration(self, mock_rag_log):
        """Test integration: Golden approval rejected → Step 115 (Feedback end)."""
        from app.orchestrators.feedback import step_115__feedback_end

        # Simulate golden approval rejection context
        golden_rejection_ctx = {
            "response_id": "integration-golden-rejection",
            "expert_feedback": {"feedback_type": "incomplete"},
            "expert_user": True,
            "expert_trust_score": 0.65,  # Below threshold
            "golden_approval_status": "rejected",
            "rejection_reason": "trust_score_below_threshold",
            "request_id": "test-golden-115-integration",
        }

        step_115_result = await step_115__feedback_end(messages=[], ctx=golden_rejection_ctx)

        # Verify golden rejection handling
        assert step_115_result["feedback_pipeline_completed"] is True
        assert step_115_result["completion_reason"] == "golden_approval_rejected"
        assert step_115_result["expert_trust_score"] == 0.65
        assert step_115_result["rejection_reason"] == "trust_score_below_threshold"

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_full_feedback_end_pipeline(self, mock_rag_log):
        """Test Step 115 in full feedback pipeline completion."""
        from app.orchestrators.feedback import step_115__feedback_end

        # Simulate full pipeline context ending in no feedback
        pipeline_ctx = {
            "response_id": "pipeline-completion-123",
            "query_text": "Full pipeline completion test",
            "user_id": "pipeline-user",
            "session_id": "pipeline-session",
            "request_id": "test-115-full-pipeline",
            "processing_start_time": datetime.now(UTC),
            # From Step 113 (UI display)
            "feedback_ui_displayed": True,
            "feedback_options": ["correct", "incomplete", "wrong"],
            "ui_element_type": "feedback_buttons",
            # From Step 114 (No feedback decision)
            "feedback_provided": False,
            "decision_reason": "no_user_feedback",
            "next_step": "feedback_end",
        }

        result = await step_115__feedback_end(messages=[], ctx=pipeline_ctx)

        # Verify pipeline completion
        assert result["feedback_pipeline_completed"] is True
        assert result["completion_reason"] == "no_feedback"
        assert result["query_text"] == "Full pipeline completion test"
        assert result["feedback_ui_displayed"] is True
        assert result["processing_start_time"] == pipeline_ctx["processing_start_time"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_completion_performance_tracking(self, mock_rag_log):
        """Test Step 115: Performance tracking for completion logic."""
        from app.orchestrators.feedback import step_115__feedback_end

        start_time = datetime.now(UTC)

        ctx = {
            "response_id": "performance-test-completion",
            "feedback_provided": False,
            "request_id": "test-115-performance",
            "processing_start_time": start_time,
        }

        datetime.now(UTC)

        result = await step_115__feedback_end(messages=[], ctx=ctx)

        # Verify completion was processed efficiently
        assert result["feedback_pipeline_completed"] is True

        # Check that timing information is logged
        end_call = mock_rag_log.call_args_list[1]
        assert "completion_time_ms" in end_call[1]
        assert end_call[1]["completion_time_ms"] >= 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.feedback.rag_step_log")
    async def test_step_115_multiple_completion_scenarios(self, mock_rag_log):
        """Test Step 115: Handle multiple completion scenarios in sequence."""
        from app.orchestrators.feedback import step_115__feedback_end

        # Test various completion scenarios
        scenarios = [
            {
                "name": "no_user_feedback",
                "ctx": {"feedback_provided": False, "decision_reason": "no_user_feedback"},
                "expected_reason": "no_feedback",
            },
            {
                "name": "ui_disabled",
                "ctx": {"feedback_ui_displayed": False, "decision_reason": "feedback_ui_not_displayed"},
                "expected_reason": "feedback_ui_not_available",
            },
            {
                "name": "golden_rejected",
                "ctx": {"golden_approval_status": "rejected", "rejection_reason": "quality_issues"},
                "expected_reason": "golden_approval_rejected",
            },
        ]

        for scenario in scenarios:
            ctx = {
                "response_id": f"scenario-{scenario['name']}",
                "request_id": f"test-115-{scenario['name']}",
                **scenario["ctx"],
            }

            result = await step_115__feedback_end(messages=[], ctx=ctx)

            # Verify each scenario completes correctly
            assert result["feedback_pipeline_completed"] is True
            assert result["completion_reason"] == scenario["expected_reason"]
