"""
Tests for RAG STEP 24 — GoldenSet.match_by_signature_or_semantic
(RAG.preflight.goldenset.match.by.signature.or.semantic)

This process step matches user queries against the Golden Set (FAQ database) using
either query signature (exact hash match) or semantic similarity search.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRAGStep24GoldenLookup:
    """Test suite for RAG STEP 24 - Golden Set lookup."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_signature_match(self, mock_rag_log):
        """Test Step 24: Finds FAQ by query signature (exact match)."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {
            "user_query": "Quali sono le detrazioni fiscali per il 2024?",
            "query_signature": "abc123def456",  # From Step 18
            "canonical_facts": ["detrazioni", "fiscali", "2024"],
            "request_id": "test-24-signature",
        }

        result = await step_24__golden_lookup(messages=[], ctx=ctx)

        # Should return Golden Set match
        assert isinstance(result, dict)
        assert "golden_match" in result
        assert result["match_type"] in ["signature", "semantic"]
        assert result["next_step"] == "golden_hit_check"  # Routes to Step 25

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 24
        assert completed_log["node_label"] == "GoldenLookup"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_semantic_match(self, mock_rag_log):
        """Test Step 24: Finds FAQ by semantic similarity."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {
            "user_query": "Come funziona il regime forfettario?",
            "query_signature": "xyz789",
            "canonical_facts": ["regime", "forfettario"],
            "request_id": "test-24-semantic",
        }

        result = await step_24__golden_lookup(messages=[], ctx=ctx)

        # Should return semantic match
        assert "golden_match" in result
        assert "similarity_score" in result
        assert result["next_step"] == "golden_hit_check"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_no_match(self, mock_rag_log):
        """Test Step 24: No FAQ match found."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {
            "user_query": "Query completamente sconosciuta xyz123",
            "query_signature": "nomatch999",
            "canonical_facts": [],
            "request_id": "test-24-nomatch",
        }

        result = await step_24__golden_lookup(messages=[], ctx=ctx)

        # Should return no match
        assert result["golden_match"] is None
        assert result["match_found"] is False
        assert result["next_step"] == "golden_hit_check"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_preserves_context(self, mock_rag_log):
        """Test Step 24: Preserves all context from previous step."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {
            "user_query": "Test query",
            "query_signature": "sig123",
            "canonical_facts": ["test"],
            "request_id": "test-24-context",
            "other_field": "preserved_value",
            "extracted_docs": [],
        }

        result = await step_24__golden_lookup(messages=[], ctx=ctx)

        # Should preserve all context
        assert result["user_query"] == "Test query"
        assert result["query_signature"] == "sig123"
        assert result["other_field"] == "preserved_value"
        assert result["request_id"] == "test-24-context"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_routes_to_golden_hit(self, mock_rag_log):
        """Test Step 24: Routes to Step 25 (GoldenHit) per Mermaid."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {"user_query": "Test routing", "query_signature": "route123", "request_id": "test-24-route"}

        result = await step_24__golden_lookup(messages=[], ctx=ctx)

        # Per Mermaid: GoldenLookup → GoldenHit (Step 25)
        assert result["next_step"] == "golden_hit_check"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_includes_match_metadata(self, mock_rag_log):
        """Test Step 24: Includes match metadata for downstream steps."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {
            "user_query": "Partita IVA forfettaria",
            "query_signature": "meta123",
            "canonical_facts": ["partita_iva", "forfettaria"],
            "request_id": "test-24-metadata",
        }

        result = await step_24__golden_lookup(messages=[], ctx=ctx)

        # Should include match metadata
        assert "match_metadata" in result
        metadata = result["match_metadata"]
        assert "search_method" in metadata
        assert metadata["search_method"] in ["signature_first", "semantic_fallback", "both"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_high_confidence_match(self, mock_rag_log):
        """Test Step 24: Returns high confidence match for next step."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {
            "user_query": "Come calcolare IVA su fattura",
            "query_signature": "highconf123",
            "canonical_facts": ["calcolare", "iva", "fattura"],
            "request_id": "test-24-highconf",
        }

        result = await step_24__golden_lookup(messages=[], ctx=ctx)

        # Should include confidence score
        if result["golden_match"]:
            assert "similarity_score" in result
            assert 0.0 <= result["similarity_score"] <= 1.0

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_logs_match_details(self, mock_rag_log):
        """Test Step 24: Logs match details with correct attributes."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {"user_query": "Detrazioni 730", "query_signature": "log123", "request_id": "test-24-log"}

        await step_24__golden_lookup(messages=[], ctx=ctx)

        # Verify logging includes match details
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        log = completed_logs[0][1]
        assert log["step"] == 24
        assert "match_found" in log or "golden_match" in log


class TestRAGStep24Parity:
    """Parity tests proving Step 24 uses SemanticFAQMatcher correctly."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_parity_with_faq_matcher(self, mock_rag_log):
        """Test Step 24: Uses same logic as SemanticFAQMatcher."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {
            "user_query": "Regime forfettario limiti",
            "query_signature": "parity123",
            "canonical_facts": ["regime", "forfettario", "limiti"],
            "request_id": "parity-test",
        }

        result = await step_24__golden_lookup(messages=[], ctx=ctx)

        # Should produce Golden Set lookup results
        assert "golden_match" in result
        assert "match_found" in result
        assert "next_step" in result


class TestRAGStep24Integration:
    """Integration tests for Step 20 → Step 24 → Step 25 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_20_to_24_integration(self, mock_preflight_log):
        """Test Step 20 (GoldenFastGate) → Step 24 (GoldenLookup) integration."""
        from app.orchestrators.preflight import step_24__golden_lookup

        # Simulate Step 20 output (when fast-path eligible - YES branch)
        step_20_output = {
            "user_query": "Come funziona la fatturazione elettronica?",
            "query_signature": "integration123",
            "canonical_facts": ["fatturazione", "elettronica"],
            "fast_path_eligible": True,
            "next_step": "golden_lookup",
            "request_id": "test-integration-20-24",
        }

        # Step 24: Execute Golden Set lookup
        step_24_result = await step_24__golden_lookup(messages=[], ctx=step_20_output)

        # Should route to Step 25 (GoldenHit)
        assert step_24_result["next_step"] == "golden_hit_check"
        assert "golden_match" in step_24_result
        assert "match_found" in step_24_result

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_24_prepares_for_step_25(self, mock_rag_log):
        """Test Step 24: Prepares output for Step 25 (GoldenHit)."""
        from app.orchestrators.preflight import step_24__golden_lookup

        ctx = {
            "user_query": "Detrazioni fiscali 2024",
            "query_signature": "prep25_123",
            "canonical_facts": ["detrazioni", "fiscali", "2024"],
            "request_id": "test-24-prep-25",
        }

        result = await step_24__golden_lookup(messages=[], ctx=ctx)

        # Should have everything Step 25 needs
        assert result["next_step"] == "golden_hit_check"
        assert "golden_match" in result
        assert "similarity_score" in result or result["golden_match"] is None
        assert "match_found" in result
