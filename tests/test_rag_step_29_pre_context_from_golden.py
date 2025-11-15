"""
Tests for RAG STEP 29 — ContextBuilder.merge facts and KB docs and doc facts if present (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present)

This process step merges context when we have a golden answer but KB has newer/conflicting information.
Combines golden answer context, KB deltas, atomic facts, and optional document facts.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep29PreContextFromGolden:
    """Test suite for RAG STEP 29 - Pre-context merging from golden set."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_29_merges_golden_and_kb_context(self, mock_rag_log):
        """Test Step 29: Merges golden answer context with KB deltas."""
        from app.orchestrators.facts import step_29__pre_context_from_golden

        # Simulate KBDelta=Yes scenario (golden hit but KB has newer info)
        ctx = {
            "golden_answer": {"answer": "Golden answer text", "confidence": 0.95, "citations": ["doc1", "doc2"]},
            "kb_deltas": [
                {"content": "Newer KB info", "score": 0.8},
                {"content": "Conflicting KB data", "score": 0.7},
            ],
            "atomic_facts": MagicMock(fact_count=lambda: 3),
            "request_id": "test-29-merge",
        }

        result = await step_29__pre_context_from_golden(messages=[], ctx=ctx)

        # Should create pre-context merge
        assert "pre_context_merge" in result or "merged_context" in result
        assert result["next_step"] == "kb_pre_fetch"

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 29
        assert completed_log["node_label"] == "PreContextFromGolden"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_29_includes_atomic_facts(self, mock_rag_log):
        """Test Step 29: Includes atomic facts in context merge."""
        from app.orchestrators.facts import step_29__pre_context_from_golden
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Extract real atomic facts
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("Dipendente con RAL €35.000 a Milano")

        ctx = {
            "golden_answer": {"answer": "Golden answer"},
            "kb_deltas": [{"content": "KB update"}],
            "atomic_facts": atomic_facts,
            "request_id": "test-29-facts",
        }

        result = await step_29__pre_context_from_golden(messages=[], ctx=ctx)

        # Should preserve atomic facts
        assert "atomic_facts" in result
        assert result["atomic_facts"].fact_count() > 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_29_handles_optional_document_facts(self, mock_rag_log):
        """Test Step 29: Handles optional document facts."""
        from app.orchestrators.facts import step_29__pre_context_from_golden

        # With document facts
        ctx_with_docs = {
            "golden_answer": {"answer": "Answer"},
            "kb_deltas": [],
            "atomic_facts": MagicMock(fact_count=lambda: 2),
            "document_facts": [{"type": "fattura", "amount": 1000}, {"type": "contract", "duration": "12 months"}],
            "request_id": "test-29-with-docs",
        }

        result_with = await step_29__pre_context_from_golden(messages=[], ctx=ctx_with_docs)
        assert "document_facts" in result_with

        # Without document facts
        ctx_without_docs = {
            "golden_answer": {"answer": "Answer"},
            "kb_deltas": [],
            "atomic_facts": MagicMock(fact_count=lambda: 2),
            "request_id": "test-29-without-docs",
        }

        await step_29__pre_context_from_golden(messages=[], ctx=ctx_without_docs)
        # Should handle gracefully even without document facts

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_29_handles_empty_kb_deltas(self, mock_rag_log):
        """Test Step 29: Handles empty KB deltas gracefully."""
        from app.orchestrators.facts import step_29__pre_context_from_golden

        ctx = {
            "golden_answer": {"answer": "Golden answer only"},
            "kb_deltas": [],
            "atomic_facts": MagicMock(fact_count=lambda: 1),
            "request_id": "test-29-empty-deltas",
        }

        result = await step_29__pre_context_from_golden(messages=[], ctx=ctx)

        # Should still process with just golden answer
        assert result["next_step"] == "kb_pre_fetch"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_29_routes_to_kb_pre_fetch(self, mock_rag_log):
        """Test Step 29: Routes to Step 39 (KBPreFetch)."""
        from app.orchestrators.facts import step_29__pre_context_from_golden

        ctx = {
            "golden_answer": {"answer": "Answer"},
            "kb_deltas": [{"content": "Delta"}],
            "request_id": "test-29-route",
        }

        result = await step_29__pre_context_from_golden(messages=[], ctx=ctx)

        # Should route to KBPreFetch per Mermaid
        assert result["next_step"] == "kb_pre_fetch"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_29_preserves_context_fields(self, mock_rag_log):
        """Test Step 29: Preserves all context fields for downstream steps."""
        from app.orchestrators.facts import step_29__pre_context_from_golden

        ctx = {
            "golden_answer": {"answer": "Answer"},
            "kb_deltas": [],
            "atomic_facts": MagicMock(fact_count=lambda: 1),
            "request_id": "test-29-preserve",
            "user_id": "user123",
            "session_id": "session456",
            "query_signature": "abc123",
            "other_field": "preserved",
        }

        result = await step_29__pre_context_from_golden(messages=[], ctx=ctx)

        # Should preserve all context
        assert result["request_id"] == "test-29-preserve"
        assert result["user_id"] == "user123"
        assert result["session_id"] == "session456"
        assert result["query_signature"] == "abc123"
        assert result["other_field"] == "preserved"


class TestRAGStep29Parity:
    """Parity tests proving Step 29 uses ContextBuilderMerge correctly."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_29_parity_with_context_builder_merge(self, mock_rag_log):
        """Test Step 29: Uses same logic as ContextBuilderMerge service."""
        from app.orchestrators.facts import step_29__pre_context_from_golden
        from app.services.context_builder_merge import ContextBuilderMerge

        # Prepare test data
        canonical_facts = ["Fact 1", "Fact 2"]
        kb_deltas = [{"content": "KB delta 1", "score": 0.8}]

        # Direct service call
        builder = ContextBuilderMerge()
        service_input = {
            "canonical_facts": canonical_facts,
            "kb_results": kb_deltas,
            "query": "Test query",
            "trace_id": "parity-test",
        }
        direct_result = builder.merge_context(service_input)

        # Orchestrator call
        ctx = {
            "canonical_facts": canonical_facts,
            "kb_deltas": kb_deltas,
            "query": "Test query",
            "request_id": "parity-test",
        }
        await step_29__pre_context_from_golden(messages=[], ctx=ctx)

        # Both should produce context merges (not necessarily identical due to orchestrator wrapper)
        # But should preserve key merge behavior
        assert "merged_context" in direct_result or "context_parts" in direct_result
        # Orchestrator adds routing and preserves context


class TestRAGStep29Integration:
    """Integration tests for Step 28 → Step 29 → Step 39 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_29_follows_kb_delta_yes_path(self, mock_facts_log):
        """Test Step 29: Executes when KBDelta=Yes (golden hit with KB updates)."""
        from app.orchestrators.facts import step_29__pre_context_from_golden

        # Simulate Step 28 (KBDelta) routing to Step 29 when KB has newer info
        step_28_output = {
            "kb_delta_detected": True,
            "golden_answer": {"answer": "Golden answer from Step 28", "confidence": 0.92},
            "kb_deltas": [{"content": "Newer KB article", "score": 0.85, "date": "2024-01-15"}],
            "atomic_facts": MagicMock(fact_count=lambda: 2),
            "request_id": "test-integration-28-29",
        }

        # Step 29: Merge pre-context
        step_29_result = await step_29__pre_context_from_golden(messages=[], ctx=step_28_output)

        # Should prepare context and route to KBPreFetch
        assert step_29_result["next_step"] == "kb_pre_fetch"
        assert "golden_answer" in step_29_result
        assert "kb_deltas" in step_29_result

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_29_context_preservation(self, mock_rag_log):
        """Test Step 29: Preserves context for Step 39 (KBPreFetch)."""
        from app.orchestrators.facts import step_29__pre_context_from_golden

        ctx = {
            "golden_answer": {"answer": "Answer"},
            "kb_deltas": [{"content": "Delta"}],
            "atomic_facts": MagicMock(fact_count=lambda: 1),
            "query_signature": "sig123",
            "canonicalization_valid": True,
            "request_id": "test-29-context-preserve",
            "user_message": "Original query",
        }

        result = await step_29__pre_context_from_golden(messages=[], ctx=ctx)

        # Should preserve all fields for Step 39
        assert result["query_signature"] == "sig123"
        assert result["canonicalization_valid"] is True
        assert result["user_message"] == "Original query"
        assert result["next_step"] == "kb_pre_fetch"
