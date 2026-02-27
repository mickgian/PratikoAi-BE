"""
Comprehensive test suite for RAG STEP 126 — Determine action.

Tests the orchestrator function that analyzes cached expert feedback to determine
what action to take (route to Golden Set candidate creation or other outcomes),
following MASTER_GUARDRAILS TDD methodology.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.quality_analysis import FeedbackType
from app.orchestrators.platform import step_126__determine_action


class TestStep126DetermineActionUnit:
    """Unit tests for Step 126 DetermineAction orchestrator function."""

    @pytest.fixture
    def sample_expert_feedback_context(self):
        """Sample context with expert feedback from CacheFeedback step."""
        return {
            "request_id": "test-request-126",
            "rag_step": 125,  # CacheFeedback previous step
            "expert_feedback": {
                "feedback_id": "feedback-123",
                "expert_id": "expert-456",
                "feedback_type": "INCORRECT",
                "query_text": "What is the IRPEF rate for 2024?",
                "original_answer": "The rate is 20%",
                "expert_answer": "The IRPEF rates for 2024 are progressive: 23% up to €15k, 27% from €15k-28k, 38% from €28k-55k, 41% from €55k-75k, 43% above €75k",
                "category": "tassazione",
                "regulatory_references": ["Art. 11 TUIR", "L. 197/2022"],
                "confidence_score": 0.95,
                "trust_score": 0.85,
                "frequency": 15,
            },
            "cache_results": {
                "feedback_cached": True,
                "cache_key": "expert_feedback:feedback-123",
                "ttl_seconds": 3600,
            },
            "expert_metrics": {"total_feedback_count": 47, "accuracy_score": 0.89, "response_quality_avg": 0.92},
        }

    @pytest.fixture
    def correct_feedback_context(self):
        """Context with CORRECT feedback type."""
        return {
            "request_id": "test-request-correct",
            "rag_step": 125,
            "expert_feedback": {
                "feedback_id": "feedback-correct",
                "expert_id": "expert-789",
                "feedback_type": "CORRECT",
                "query_text": "What is VAT rate in Italy?",
                "original_answer": "Standard VAT rate in Italy is 22%",
                "expert_answer": None,  # No correction needed
                "category": "iva",
                "confidence_score": 0.98,
                "trust_score": 0.91,
                "frequency": 8,
            },
        }

    @pytest.fixture
    def incomplete_feedback_context(self):
        """Context with INCOMPLETE feedback type."""
        return {
            "request_id": "test-request-incomplete",
            "rag_step": 125,
            "expert_feedback": {
                "feedback_id": "feedback-incomplete",
                "expert_id": "expert-101",
                "feedback_type": "INCOMPLETE",
                "query_text": "How to calculate TFR?",
                "original_answer": "TFR is calculated annually",
                "expert_answer": "TFR calculation: (gross annual salary / 13.5) + annual revaluation based on ISTAT index and 1.5% fixed rate",
                "category": "lavoro",
                "confidence_score": 0.88,
                "trust_score": 0.79,
                "frequency": 5,
            },
        }

    @pytest.mark.asyncio
    async def test_determine_action_incorrect_with_correction(self, sample_expert_feedback_context):
        """Test action determination for INCORRECT feedback with expert correction."""
        with (
            patch("app.orchestrators.platform.rag_step_log") as mock_log,
            patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
        ):
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = await step_126__determine_action(ctx=sample_expert_feedback_context)

            # Verify action determination
            assert result is not None
            assert result["rag_step"] == 126
            assert result["request_id"] == "test-request-126"
            assert result["action_determined"] == "correction_queued"
            assert result["route_to_golden_candidate"] is True
            assert result["action_reasoning"] == "Expert provided correction for incorrect answer"

            # Verify routing
            assert result["next_step"] == 127  # GoldenCandidate
            assert result["next_step_id"] == "RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback"

            # Verify observability
            mock_log.assert_called()
            mock_timer.assert_called_with(
                126, "RAG.platform.determine.action", "DetermineAction", request_id="test-request-126", stage="start"
            )

    @pytest.mark.asyncio
    async def test_determine_action_correct_feedback(self, correct_feedback_context):
        """Test action determination for CORRECT feedback."""
        with (
            patch("app.orchestrators.platform.rag_step_log"),
            patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
        ):
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = await step_126__determine_action(ctx=correct_feedback_context)

            # Verify action determination
            assert result["action_determined"] == "feedback_acknowledged"
            assert result["route_to_golden_candidate"] is False
            assert result["action_reasoning"] == "Expert confirmed answer is correct"

            # Should not route to GoldenCandidate for correct feedback
            assert "next_step" not in result or result.get("next_step") != 127
            assert "completion_reason" in result
            assert result["feedback_processing_complete"] is True

    @pytest.mark.asyncio
    async def test_determine_action_incomplete_with_enhancement(self, incomplete_feedback_context):
        """Test action determination for INCOMPLETE feedback with expert enhancement."""
        with (
            patch("app.orchestrators.platform.rag_step_log"),
            patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
        ):
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = await step_126__determine_action(ctx=incomplete_feedback_context)

            # Verify action determination
            assert result["action_determined"] == "answer_enhancement_queued"
            assert result["route_to_golden_candidate"] is True
            assert result["action_reasoning"] == "Expert provided enhancement for incomplete answer"

            # Should route to GoldenCandidate for enhancement
            assert result["next_step"] == 127
            assert result["next_step_id"] == "RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback"

    @pytest.mark.asyncio
    async def test_missing_expert_feedback(self):
        """Test handling of missing expert feedback data."""
        ctx = {
            "request_id": "test-request-missing",
            "rag_step": 125,
            # Missing expert_feedback
        }

        with patch("app.orchestrators.platform.rag_step_log"):
            result = await step_126__determine_action(ctx=ctx)

            assert result is not None
            assert result["action_determined"] == "no_action"
            assert result["route_to_golden_candidate"] is False
            assert "error" in result
            assert "missing expert feedback" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_feedback_type(self):
        """Test handling of invalid feedback type."""
        ctx = {
            "request_id": "test-request-invalid",
            "rag_step": 125,
            "expert_feedback": {
                "feedback_id": "feedback-invalid",
                "feedback_type": "UNKNOWN_TYPE",  # Invalid type
                "query_text": "Test query",
                "expert_id": "expert-test",
            },
        }

        with patch("app.orchestrators.platform.rag_step_log"):
            result = await step_126__determine_action(ctx=ctx)

            assert result["action_determined"] == "feedback_logged"
            assert result["route_to_golden_candidate"] is False
            assert result["action_reasoning"] == "Unknown feedback type, logging for review"

    @pytest.mark.asyncio
    async def test_incorrect_feedback_without_correction(self):
        """Test INCORRECT feedback without expert correction."""
        ctx = {
            "request_id": "test-request-no-correction",
            "rag_step": 125,
            "expert_feedback": {
                "feedback_id": "feedback-no-correction",
                "feedback_type": "INCORRECT",
                "query_text": "Test query",
                "original_answer": "Wrong answer",
                "expert_answer": None,  # No correction provided
                "expert_id": "expert-test",
            },
        }

        with patch("app.orchestrators.platform.rag_step_log"):
            result = await step_126__determine_action(ctx=ctx)

            assert result["action_determined"] == "critical_review_flagged"
            assert result["route_to_golden_candidate"] is False
            assert result["action_reasoning"] == "Expert flagged incorrect answer but provided no correction"

    @pytest.mark.asyncio
    async def test_quality_score_calculation(self, sample_expert_feedback_context):
        """Test that quality scores influence action determination."""
        # Low trust score scenario
        low_trust_ctx = sample_expert_feedback_context.copy()
        low_trust_ctx["expert_feedback"] = sample_expert_feedback_context["expert_feedback"].copy()
        low_trust_ctx["expert_feedback"]["trust_score"] = 0.45  # Below threshold

        with (
            patch("app.orchestrators.platform.rag_step_log"),
            patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
        ):
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = await step_126__determine_action(ctx=low_trust_ctx)

            # Should still determine action but with quality concerns
            assert "quality_concerns" in result
            assert result["expert_trust_score"] == 0.45
            assert result["quality_assessment"] == "low_trust"


class TestStep126DetermineActionIntegration:
    """Integration tests for Step 126 in the RAG workflow."""

    @pytest.mark.asyncio
    async def test_cache_feedback_to_determine_action_flow(self):
        """Test integration from CacheFeedback step to DetermineAction step."""
        # Simulate context from CacheFeedback step (Step 125)
        cache_feedback_result_ctx = {
            "request_id": "integration-test-001",
            "rag_step": 125,
            "cache_operation": "feedback_stored",
            "cache_key": "expert_feedback:test-001",
            "expert_feedback": {
                "feedback_id": "feedback-integration-001",
                "expert_id": "expert-integration",
                "feedback_type": "INCORRECT",
                "query_text": "Integration test query",
                "expert_answer": "Corrected answer for integration test",
                "confidence_score": 0.92,
                "trust_score": 0.88,
            },
            "previous_step": 124,  # UpdateExpertMetrics
        }

        with (
            patch("app.orchestrators.platform.rag_step_log"),
            patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
        ):
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = await step_126__determine_action(ctx=cache_feedback_result_ctx)

            # Verify flow progression
            assert result["previous_step"] == 125  # CacheFeedback
            assert result["rag_step"] == 126  # DetermineAction
            assert result["next_step"] == 127  # GoldenCandidate
            assert result["action_determined"] == "correction_queued"

    @pytest.mark.asyncio
    async def test_determine_action_to_golden_candidate_flow(self):
        """Test integration from DetermineAction step to GoldenCandidate step."""
        ctx = {
            "request_id": "integration-test-002",
            "rag_step": 125,
            "expert_feedback": {
                "feedback_id": "feedback-integration-002",
                "expert_id": "expert-candidate-test",
                "feedback_type": "INCOMPLETE",
                "query_text": "Test query for golden candidate",
                "original_answer": "Partial answer",
                "expert_answer": "Complete enhanced answer with references",
                "category": "test_category",
                "regulatory_references": ["Test Regulation 1"],
                "confidence_score": 0.94,
                "trust_score": 0.87,
                "frequency": 12,
            },
        }

        with (
            patch("app.orchestrators.platform.rag_step_log"),
            patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
        ):
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = await step_126__determine_action(ctx=ctx)

            # Verify preparation for GoldenCandidate step
            assert result["route_to_golden_candidate"] is True
            assert "golden_candidate_data" in result
            candidate_data = result["golden_candidate_data"]

            # Verify data structure for Step 127
            assert candidate_data["action"] == "answer_enhancement_queued"
            assert candidate_data["expert_feedback"] == ctx["expert_feedback"]
            assert candidate_data["should_create_candidate"] is True

    @pytest.mark.asyncio
    async def test_end_to_end_feedback_decision_workflow(self):
        """Test complete workflow from cached feedback to action determination."""
        # Complete context as would be received from the feedback pipeline
        complete_ctx = {
            "request_id": "e2e-test-003",
            "rag_step": 125,
            "user_query": "What are the new tax rates for 2024?",
            "original_response_id": "resp-123",
            "expert_feedback": {
                "feedback_id": "feedback-e2e-003",
                "expert_id": "expert-senior-001",
                "feedback_type": "INCORRECT",
                "query_text": "What are the new tax rates for 2024?",
                "original_answer": "Tax rates remain unchanged from 2023",
                "expert_answer": "Several tax rates changed for 2024: IRPEF brackets adjusted, VAT unchanged at 22%, corporate tax reduced from 24% to 23.5%",
                "category": "tassazione",
                "regulatory_references": ["DL 104/2023", "L. 213/2023"],
                "confidence_score": 0.97,
                "trust_score": 0.91,
                "frequency": 23,
                "correction_importance": "high",
            },
            "cache_results": {"feedback_cached": True, "cache_ttl": 3600, "cache_size_bytes": 1024},
            "expert_metrics": {"total_contributions": 156, "accuracy_rate": 0.93, "avg_response_time_min": 12.5},
        }

        with (
            patch("app.orchestrators.platform.rag_step_log"),
            patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
        ):
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = await step_126__determine_action(ctx=complete_ctx)

            # Verify complete workflow result
            assert result["action_determined"] == "correction_queued"
            assert result["route_to_golden_candidate"] is True
            assert result["rag_step"] == 126
            assert result["next_step"] == 127

            # Verify decision metadata
            decision_metadata = result["decision_metadata"]
            assert decision_metadata["feedback_type"] == "INCORRECT"
            assert decision_metadata["has_expert_correction"] is True
            assert decision_metadata["expert_trust_score"] == 0.91
            assert decision_metadata["correction_importance"] == "high"

            # Verify golden candidate preparation
            candidate_prep = result["golden_candidate_data"]
            assert candidate_prep["priority_level"] == "high"
            assert candidate_prep["quality_score"] > 0.9


class TestStep126DetermineActionParity:
    """Parity tests to ensure behavioral consistency."""

    @pytest.mark.asyncio
    async def test_action_determination_logic_consistency(self):
        """Verify orchestrator uses same logic as ExpertFeedbackCollector._determine_action."""
        test_cases = [
            {"feedback_type": "CORRECT", "expert_answer": None, "expected_action": "feedback_acknowledged"},
            {
                "feedback_type": "INCOMPLETE",
                "expert_answer": "Enhanced answer",
                "expected_action": "answer_enhancement_queued",
            },
            {"feedback_type": "INCOMPLETE", "expert_answer": None, "expected_action": "improvement_suggestion_logged"},
            {
                "feedback_type": "INCORRECT",
                "expert_answer": "Corrected answer",
                "expected_action": "correction_queued",
            },
            {"feedback_type": "INCORRECT", "expert_answer": None, "expected_action": "critical_review_flagged"},
        ]

        for i, test_case in enumerate(test_cases):
            ctx = {
                "request_id": f"parity-test-{i}",
                "rag_step": 125,
                "expert_feedback": {
                    "feedback_id": f"feedback-parity-{i}",
                    "feedback_type": test_case["feedback_type"],
                    "expert_answer": test_case["expert_answer"],
                    "query_text": f"Test query {i}",
                    "expert_id": "expert-parity",
                },
            }

            with (
                patch("app.orchestrators.platform.rag_step_log"),
                patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
            ):
                mock_timer.return_value.__enter__ = MagicMock()
                mock_timer.return_value.__exit__ = MagicMock()

                result = await step_126__determine_action(ctx=ctx)

                # Verify consistent action determination
                assert result["action_determined"] == test_case["expected_action"], (
                    f"Test case {i}: expected {test_case['expected_action']}, got {result['action_determined']}"
                )

    @pytest.mark.asyncio
    async def test_routing_decision_consistency(self):
        """Verify routing decisions are consistent with business rules."""
        # Actions that should route to GoldenCandidate

        # Actions that should NOT route to GoldenCandidate

        all_test_cases = [
            ("INCORRECT", "Correction", "correction_queued", True),
            ("INCOMPLETE", "Enhancement", "answer_enhancement_queued", True),
            ("CORRECT", None, "feedback_acknowledged", False),
            ("INCOMPLETE", None, "improvement_suggestion_logged", False),
            ("INCORRECT", None, "critical_review_flagged", False),
        ]

        for feedback_type, expert_answer, expected_action, should_route in all_test_cases:
            ctx = {
                "request_id": f"routing-test-{feedback_type}",
                "rag_step": 125,
                "expert_feedback": {
                    "feedback_id": f"feedback-{feedback_type}",
                    "feedback_type": feedback_type,
                    "expert_answer": expert_answer,
                    "query_text": f"Test query for {feedback_type}",
                    "expert_id": "expert-routing-test",
                },
            }

            with (
                patch("app.orchestrators.platform.rag_step_log"),
                patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
            ):
                mock_timer.return_value.__enter__ = MagicMock()
                mock_timer.return_value.__exit__ = MagicMock()

                result = await step_126__determine_action(ctx=ctx)

                # Verify routing consistency
                assert result["action_determined"] == expected_action
                assert result["route_to_golden_candidate"] == should_route

                if should_route:
                    assert result["next_step"] == 127
                else:
                    assert "next_step" not in result or result.get("next_step") != 127
                    assert result["feedback_processing_complete"] is True


if __name__ == "__main__":
    pytest.main([__file__])
