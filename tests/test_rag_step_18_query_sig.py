"""
Tests for RAG STEP 18 — QuerySignature.compute Hash from canonical facts (RAG.facts.querysignature.compute.hash.from.canonical.facts)

This process step computes a deterministic hash signature from canonicalized atomic facts.
The hash is used for caching, deduplication, and query matching.
"""

from unittest.mock import patch

import pytest


class TestRAGStep18QuerySig:
    """Test suite for RAG STEP 18 - Query signature computation."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_18_computes_query_signature(self, mock_rag_log):
        """Test Step 18: Computes deterministic hash from atomic facts."""
        from app.orchestrators.facts import step_18__query_sig

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare Step 16 output with canonicalized facts
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("Stipendio di €45.000 annui")

        ctx = {
            "atomic_facts": atomic_facts,
            "fact_count": atomic_facts.fact_count(),
            "canonicalization_valid": True,
            "request_id": "test-18-signature",
        }

        result = await step_18__query_sig(messages=[], ctx=ctx)

        # Should compute query signature
        assert "query_signature" in result
        assert isinstance(result["query_signature"], str)
        assert len(result["query_signature"]) == 64  # SHA256 hex digest

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 18
        assert completed_log["node_label"] == "QuerySig"
        assert "query_signature" in completed_log

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_18_identical_facts_same_signature(self, mock_rag_log):
        """Test Step 18: Identical facts produce identical signatures."""
        from app.orchestrators.facts import step_18__query_sig

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        query = "Dipendente con RAL €35.000"
        extractor = AtomicFactsExtractor()

        # Extract same facts twice
        facts_1 = extractor.extract(query)
        facts_2 = extractor.extract(query)

        ctx_1 = {"atomic_facts": facts_1, "request_id": "test-18-sig-1"}
        ctx_2 = {"atomic_facts": facts_2, "request_id": "test-18-sig-2"}

        result_1 = await step_18__query_sig(messages=[], ctx=ctx_1)
        result_2 = await step_18__query_sig(messages=[], ctx=ctx_2)

        # Same facts should produce same signature
        assert result_1["query_signature"] == result_2["query_signature"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_18_different_facts_different_signature(self, mock_rag_log):
        """Test Step 18: Different facts produce different signatures."""
        from app.orchestrators.facts import step_18__query_sig

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        extractor = AtomicFactsExtractor()

        # Extract different facts
        facts_1 = extractor.extract("Dipendente con RAL €35.000")
        facts_2 = extractor.extract("Dipendente con RAL €40.000")

        ctx_1 = {"atomic_facts": facts_1, "request_id": "test-18-diff-1"}
        ctx_2 = {"atomic_facts": facts_2, "request_id": "test-18-diff-2"}

        result_1 = await step_18__query_sig(messages=[], ctx=ctx_1)
        result_2 = await step_18__query_sig(messages=[], ctx=ctx_2)

        # Different facts should produce different signatures
        assert result_1["query_signature"] != result_2["query_signature"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_18_handles_empty_facts(self, mock_rag_log):
        """Test Step 18: Handles empty atomic facts gracefully."""
        from app.orchestrators.facts import step_18__query_sig

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        # Extract from empty query
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("")

        ctx = {"atomic_facts": atomic_facts, "fact_count": 0, "request_id": "test-18-empty"}

        result = await step_18__query_sig(messages=[], ctx=ctx)

        # Should still produce a signature (even if from empty facts)
        assert "query_signature" in result
        assert isinstance(result["query_signature"], str)
        assert len(result["query_signature"]) == 64

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_18_signature_deterministic(self, mock_rag_log):
        """Test Step 18: Signature is deterministic across multiple runs."""
        from app.orchestrators.facts import step_18__query_sig

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        query = "CCNL commercio, €1.500, Milano"
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract(query)

        # Run signature computation 3 times
        signatures = []
        for i in range(3):
            ctx = {"atomic_facts": atomic_facts, "request_id": f"test-18-deterministic-{i}"}
            result = await step_18__query_sig(messages=[], ctx=ctx)
            signatures.append(result["query_signature"])

        # All signatures should be identical
        assert len(set(signatures)) == 1, f"Got different signatures: {signatures}"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_18_signature_includes_all_fact_types(self, mock_rag_log):
        """Test Step 18: Signature changes when different fact types change."""
        from app.orchestrators.facts import step_18__query_sig

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        extractor = AtomicFactsExtractor()

        # Test with different fact type combinations
        queries = [
            "Dipendente €30.000",  # Only monetary
            "Dipendente a Milano",  # Only geographic
            "Dipendente €30.000 a Milano",  # Both
        ]

        signatures = []
        for query in queries:
            facts = extractor.extract(query)
            ctx = {"atomic_facts": facts, "request_id": f"test-{query}"}
            result = await step_18__query_sig(messages=[], ctx=ctx)
            signatures.append(result["query_signature"])

        # All should have different signatures
        assert len(set(signatures)) == len(signatures), (
            f"Expected {len(queries)} unique signatures, got {len(set(signatures))}"
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_18_routes_to_attach_check(self, mock_rag_log):
        """Test Step 18: Routes to AttachCheck (Step 19)."""
        from app.orchestrators.facts import step_18__query_sig

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare context
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("Fattura €1.000")

        ctx = {"atomic_facts": atomic_facts, "request_id": "test-18-route"}

        result = await step_18__query_sig(messages=[], ctx=ctx)

        # Should route to AttachCheck
        assert result["next_step"] == "attach_check"


class TestRAGStep18Integration:
    """Integration tests for Step 16 → Step 17 → Step 18 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_to_17_to_18_integration(self, mock_facts_log, mock_preflight_log):
        """Test Step 16 (CanonicalizeFacts) → Step 17 (AttachmentFingerprint) → Step 18 (QuerySig) integration."""
        from app.orchestrators.facts import step_16__canonicalize_facts, step_18__query_sig
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        # Extract facts
        query = "Quanto costa un dipendente con RAL €40.000?"
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract(query)

        # Step 16: Validate canonicalization
        step_16_ctx = {
            "atomic_facts": atomic_facts,
            "fact_count": atomic_facts.fact_count(),
            "request_id": "test-integration-16-17-18",
            "attachments": [],  # No attachments for this test
        }
        step_16_result = await step_16__canonicalize_facts(messages=[], ctx=step_16_ctx)

        # Step 17: Compute attachment fingerprints
        step_17_result = await step_17__attachment_fingerprint(messages=[], ctx=step_16_result)

        # Step 18: Compute query signature
        step_18_result = await step_18__query_sig(messages=[], ctx=step_17_result)

        # Should flow correctly through all three steps
        assert step_16_result["next_step"] == "attachment_fingerprint"
        assert step_16_result["canonicalization_valid"] is True

        assert step_17_result["next_step"] == "query_sig"
        assert step_17_result["hashes_computed"] is True
        assert step_17_result["attachment_count"] == 0

        assert step_18_result["next_step"] == "attach_check"
        assert "query_signature" in step_18_result

        # Should preserve all context throughout the chain
        assert step_18_result["atomic_facts"] == atomic_facts
        assert step_18_result["canonicalization_valid"] is True
        assert step_18_result["hashes_computed"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_18_context_preservation(self, mock_rag_log):
        """Test Step 18: Preserves context for next steps."""
        from app.orchestrators.facts import step_18__query_sig

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare context with extra fields
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("Dipendente €30.000 annui")

        ctx = {
            "atomic_facts": atomic_facts,
            "fact_count": atomic_facts.fact_count(),
            "canonicalization_valid": True,
            "request_id": "test-18-context",
            "user_message": "Dipendente €30.000 annui",
            "some_other_field": "preserved_value",
        }

        result = await step_18__query_sig(messages=[], ctx=ctx)

        # Should preserve context fields
        assert result["request_id"] == "test-18-context"
        assert result["user_message"] == "Dipendente €30.000 annui"
        assert result["some_other_field"] == "preserved_value"
        assert result["canonicalization_valid"] is True

        # Should add signature field
        assert "query_signature" in result
        assert isinstance(result["query_signature"], str)

        # Context ready for next step
        assert result["next_step"] == "attach_check"
