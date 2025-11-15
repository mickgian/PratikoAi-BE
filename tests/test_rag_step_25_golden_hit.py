"""
Tests for RAG STEP 25 — High confidence match? score at least 0.90
(RAG.golden.high.confidence.match.score.at.least.0.90)

This decision step evaluates the confidence score of a Golden Set match from Step 24.
Routes to KB context check (Step 26) if score >= 0.90, otherwise routes to ClassifyDomain (Step 30).
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep25GoldenHit:
    """Test suite for RAG STEP 25 - Golden Set confidence evaluation."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_25_high_confidence_routes_to_kb_check(self, mock_rag_log):
        """Test Step 25: High confidence match (>=0.90) routes to KB context check."""
        from app.orchestrators.golden import step_25__golden_hit

        ctx = {
            "golden_match": {
                "faq_id": "faq_001",
                "question": "Quali sono le detrazioni fiscali 2024?",
                "answer": "Le detrazioni fiscali per il 2024 includono...",
                "similarity_score": 0.95,
            },
            "match_found": True,
            "similarity_score": 0.95,
            "match_type": "semantic",
            "request_id": "test-25-high",
        }

        result = await step_25__golden_hit(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result["high_confidence_match"] is True
        assert result["confidence_threshold"] == 0.90
        assert result["similarity_score"] == 0.95
        assert result["next_step"] == "kb_context_check"  # Routes to Step 26
        assert "golden_match" in result
        assert result["request_id"] == "test-25-high"

        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 25
        assert completed_log["node_label"] == "GoldenHit"
        assert completed_log["high_confidence_match"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_25_low_confidence_routes_to_classify(self, mock_rag_log):
        """Test Step 25: Low confidence match (<0.90) routes to ClassifyDomain."""
        from app.orchestrators.golden import step_25__golden_hit

        ctx = {
            "golden_match": {
                "faq_id": "faq_002",
                "question": "Come funziona la pensione?",
                "answer": "La pensione...",
                "similarity_score": 0.75,
            },
            "match_found": True,
            "similarity_score": 0.75,
            "match_type": "semantic",
            "request_id": "test-25-low",
        }

        result = await step_25__golden_hit(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result["high_confidence_match"] is False
        assert result["confidence_threshold"] == 0.90
        assert result["similarity_score"] == 0.75
        assert result["next_step"] == "classify_domain"  # Routes to Step 30
        assert result["request_id"] == "test-25-low"

        assert mock_rag_log.call_count >= 2

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_25_exact_threshold_is_high_confidence(self, mock_rag_log):
        """Test Step 25: Exact threshold (0.90) counts as high confidence."""
        from app.orchestrators.golden import step_25__golden_hit

        ctx = {
            "golden_match": {"faq_id": "faq_003", "similarity_score": 0.90},
            "match_found": True,
            "similarity_score": 0.90,
            "request_id": "test-25-threshold",
        }

        result = await step_25__golden_hit(messages=[], ctx=ctx)

        assert result["high_confidence_match"] is True
        assert result["similarity_score"] == 0.90
        assert result["next_step"] == "kb_context_check"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_25_no_match_routes_to_classify(self, mock_rag_log):
        """Test Step 25: No match found routes to ClassifyDomain."""
        from app.orchestrators.golden import step_25__golden_hit

        ctx = {"golden_match": None, "match_found": False, "similarity_score": 0.0, "request_id": "test-25-no-match"}

        result = await step_25__golden_hit(messages=[], ctx=ctx)

        assert result["high_confidence_match"] is False
        assert result["similarity_score"] == 0.0
        assert result["next_step"] == "classify_domain"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_25_preserves_context(self, mock_rag_log):
        """Test Step 25: Preserves all context from previous steps."""
        from app.orchestrators.golden import step_25__golden_hit

        ctx = {
            "user_query": "Detrazioni fiscali?",
            "canonical_facts": ["detrazioni", "fiscali"],
            "query_signature": "abc123",
            "golden_match": {"faq_id": "faq_001", "similarity_score": 0.92},
            "match_found": True,
            "similarity_score": 0.92,
            "match_type": "signature",
            "search_method": "hash_lookup",
            "request_id": "test-25-context",
        }

        result = await step_25__golden_hit(messages=[], ctx=ctx)

        assert result["user_query"] == "Detrazioni fiscali?"
        assert result["canonical_facts"] == ["detrazioni", "fiscali"]
        assert result["query_signature"] == "abc123"
        assert result["match_type"] == "signature"
        assert result["search_method"] == "hash_lookup"
        assert result["high_confidence_match"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_25_includes_decision_metadata(self, mock_rag_log):
        """Test Step 25: Includes decision metadata for observability."""
        from app.orchestrators.golden import step_25__golden_hit

        ctx = {
            "golden_match": {"faq_id": "faq_001", "similarity_score": 0.88},
            "similarity_score": 0.88,
            "request_id": "test-25-metadata",
        }

        result = await step_25__golden_hit(messages=[], ctx=ctx)

        assert "decision_metadata" in result
        metadata = result["decision_metadata"]
        assert metadata["confidence_threshold"] == 0.90
        assert metadata["similarity_score"] == 0.88
        assert metadata["high_confidence"] is False
        assert metadata["decision_type"] == "threshold_comparison"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_25_logs_decision_details(self, mock_rag_log):
        """Test Step 25: Logs decision details for debugging."""
        from app.orchestrators.golden import step_25__golden_hit

        ctx = {
            "golden_match": {"faq_id": "faq_001", "similarity_score": 0.93},
            "match_found": True,
            "similarity_score": 0.93,
            "request_id": "test-25-logging",
        }

        await step_25__golden_hit(messages=[], ctx=ctx)

        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        log = completed_logs[0][1]
        assert log["high_confidence_match"] is True
        assert log["similarity_score"] == 0.93
        assert log["confidence_threshold"] == 0.90
        assert log["next_step"] == "kb_context_check"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_25_handles_missing_score(self, mock_rag_log):
        """Test Step 25: Handles missing similarity score gracefully."""
        from app.orchestrators.golden import step_25__golden_hit

        ctx = {"golden_match": None, "request_id": "test-25-missing"}

        result = await step_25__golden_hit(messages=[], ctx=ctx)

        assert result["high_confidence_match"] is False
        assert result["similarity_score"] == 0.0
        assert result["next_step"] == "classify_domain"


class TestRAGStep25Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_25_parity_threshold_logic(self):
        """Test Step 25: Threshold comparison logic matches expected behavior."""
        from app.orchestrators.golden import step_25__golden_hit

        test_cases = [
            (0.95, True, "kb_context_check"),
            (0.90, True, "kb_context_check"),
            (0.89, False, "classify_domain"),
            (0.75, False, "classify_domain"),
            (0.0, False, "classify_domain"),
            (None, False, "classify_domain"),
        ]

        for score, expected_high_conf, expected_route in test_cases:
            has_match = score is not None and score >= 0.5
            ctx = {
                "similarity_score": score if score is not None else 0.0,
                "golden_match": {"faq_id": "test"} if has_match else None,
                "match_found": has_match,
                "request_id": f"parity-{score}",
            }

            result = await step_25__golden_hit(messages=[], ctx=ctx)

            assert (
                result["high_confidence_match"] == expected_high_conf
            ), f"Score {score}: expected high_confidence={expected_high_conf}, got {result['high_confidence_match']}"
            assert (
                result["next_step"] == expected_route
            ), f"Score {score}: expected route={expected_route}, got {result['next_step']}"


class TestRAGStep25Integration:
    """Integration tests - prove Step 24 → 25 → 26/30 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_to_25_high_confidence_integration(self, mock_preflight_log, mock_golden_log):
        """Test Step 24 → 25 integration: High confidence match flows to KB check."""
        from app.orchestrators.golden import step_25__golden_hit
        from app.orchestrators.preflight import step_24__golden_lookup

        initial_ctx = {
            "user_query": "Quali sono le detrazioni fiscali per dipendenti?",
            "query_signature": "sig123",
            "request_id": "integration-24-25-high",
        }

        step_24_result = await step_24__golden_lookup(messages=[], ctx=initial_ctx)

        assert "golden_match" in step_24_result
        assert step_24_result["next_step"] == "golden_hit_check"

        step_25_result = await step_25__golden_hit(messages=[], ctx=step_24_result)

        if step_25_result.get("similarity_score", 0) >= 0.90:
            assert step_25_result["high_confidence_match"] is True
            assert step_25_result["next_step"] == "kb_context_check"
        else:
            assert step_25_result["high_confidence_match"] is False
            assert step_25_result["next_step"] == "classify_domain"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_to_25_low_confidence_integration(self, mock_preflight_log, mock_golden_log):
        """Test Step 24 → 25 integration: Low confidence match flows to ClassifyDomain."""
        from app.orchestrators.golden import step_25__golden_hit
        from app.orchestrators.preflight import step_24__golden_lookup

        initial_ctx = {
            "user_query": "Query sconosciuta nomatch xyz",
            "query_signature": None,
            "request_id": "integration-24-25-low",
        }

        step_24_result = await step_24__golden_lookup(messages=[], ctx=initial_ctx)

        assert step_24_result["next_step"] == "golden_hit_check"

        step_25_result = await step_25__golden_hit(messages=[], ctx=step_24_result)

        assert step_25_result["high_confidence_match"] is False
        assert step_25_result["next_step"] == "classify_domain"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_25_prepares_for_step_26(self, mock_rag_log):
        """Test Step 25: Prepares context correctly for Step 26 (KB context check)."""
        from app.orchestrators.golden import step_25__golden_hit

        ctx = {
            "user_query": "Detrazioni 2024",
            "golden_match": {
                "faq_id": "faq_001",
                "question": "Detrazioni fiscali 2024?",
                "answer": "Le detrazioni includono...",
                "similarity_score": 0.94,
                "updated_at": "2024-01-15T10:00:00Z",
            },
            "match_found": True,
            "similarity_score": 0.94,
            "canonical_facts": ["detrazioni", "2024"],
            "request_id": "test-25-to-26",
        }

        result = await step_25__golden_hit(messages=[], ctx=ctx)

        assert result["high_confidence_match"] is True
        assert result["next_step"] == "kb_context_check"
        assert "golden_match" in result
        assert result["golden_match"]["faq_id"] == "faq_001"
        assert result["canonical_facts"] == ["detrazioni", "2024"]
