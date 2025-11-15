"""
Tests for RAG Step 20 — Golden fast-path eligible? no doc or quick check safe
(RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe)

Test coverage:
- Unit tests: Fast path eligibility logic
- Integration tests: Step 19→20, Step 22→20, Step 20→24, Step 20→31
- Parity tests: Behavioral definition validation
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.orchestrators.golden import step_20__golden_fast_gate


class TestStep20GoldenFastGate:
    """Unit tests for Step 20 golden fast path eligibility check"""

    @pytest.fixture
    def context_from_step_19_no_attachments(self) -> dict[str, Any]:
        """Context from Step 19 when no attachments are present"""
        return {
            "rag_step": 19,
            "step_id": "RAG.preflight.attachments.present",
            "attachments_present": False,
            "query": "What are the Italian VAT rates?",
            "query_signature": "abc123def456",
            "canonical_facts": [{"type": "location", "value": "Italy"}, {"type": "topic", "value": "VAT rates"}],
            "confidence_scores": {
                "query_complexity": 0.3,  # Simple query
                "domain_specific": 0.8,  # Tax domain
                "golden_eligible": 0.7,  # Potentially golden eligible
            },
        }

    @pytest.fixture
    def context_from_step_22_no_doc_dependency(self) -> dict[str, Any]:
        """Context from Step 22 when query doesn't depend on documents"""
        return {
            "rag_step": 22,
            "step_id": "RAG.docs.doc.dependent.or.refers.to.doc",
            "doc_dependent": False,
            "attachments_present": True,
            "attachments": [{"name": "invoice.pdf", "processed": True}],
            "query": "What is the general VAT rate in Italy?",
            "query_signature": "xyz789ghi012",
            "canonical_facts": [
                {"type": "location", "value": "Italy"},
                {"type": "topic", "value": "VAT rate general"},
            ],
            "pre_ingest_results": {"doc_types": ["invoice"], "doc_relevant_to_query": False},
        }

    @pytest.fixture
    def context_complex_query(self) -> dict[str, Any]:
        """Context with complex query requiring full processing"""
        return {
            "rag_step": 19,
            "attachments_present": False,
            "query": "Can you analyze my specific tax situation with multiple income sources and deductions?",
            "query_signature": "complex123abc",
            "canonical_facts": [
                {"type": "topic", "value": "tax situation"},
                {"type": "qualifier", "value": "multiple income sources"},
                {"type": "qualifier", "value": "deductions"},
            ],
            "confidence_scores": {
                "query_complexity": 0.9,  # Complex query
                "domain_specific": 0.7,
                "golden_eligible": 0.2,  # Not golden eligible
            },
        }

    @pytest.mark.asyncio
    async def test_golden_fast_path_eligible_simple_query(self, context_from_step_19_no_attachments):
        """Test golden fast path is eligible for simple queries without attachments"""

        result = await step_20__golden_fast_gate(ctx=context_from_step_19_no_attachments)

        assert result["golden_fast_path_eligible"] is True
        assert result["eligibility_reason"] == "simple_query_no_attachments"
        assert result["next_step"] == 24
        assert result["next_step_id"] == "RAG.golden.goldenset.match.by.signature.or.semantic"
        assert result["query_signature"] == "abc123def456"
        assert result["confidence_scores"] == context_from_step_19_no_attachments["confidence_scores"]

    @pytest.mark.asyncio
    async def test_golden_fast_path_eligible_no_doc_dependency(self, context_from_step_22_no_doc_dependency):
        """Test golden fast path is eligible when query doesn't depend on documents"""

        result = await step_20__golden_fast_gate(ctx=context_from_step_22_no_doc_dependency)

        assert result["golden_fast_path_eligible"] is True
        assert result["eligibility_reason"] == "no_document_dependency"
        assert result["next_step"] == 24
        assert result["next_step_id"] == "RAG.golden.goldenset.match.by.signature.or.semantic"
        assert result["query_signature"] == "xyz789ghi012"
        # Should preserve attachment info even though not dependent
        assert result["attachments_present"] is True
        assert len(result["attachments"]) == 1

    @pytest.mark.asyncio
    async def test_golden_fast_path_not_eligible_complex_query(self, context_complex_query):
        """Test golden fast path is not eligible for complex queries"""

        result = await step_20__golden_fast_gate(ctx=context_complex_query)

        assert result["golden_fast_path_eligible"] is False
        assert result["eligibility_reason"] == "query_too_complex"
        assert result["next_step"] == 31
        assert result["next_step_id"] == "RAG.classify.domainactionclassifier.classify.rule.based.classification"
        assert result["query_complexity"] == 0.9
        assert "canonical_facts" in result  # Context preserved

    @pytest.mark.asyncio
    async def test_eligibility_check_with_thresholds(self):
        """Test eligibility check with various threshold combinations"""

        test_cases = [
            # (complexity, golden_eligible, expected_eligible)
            (0.2, 0.8, True),  # Simple query, high golden score
            (0.5, 0.5, True),  # Medium complexity, medium golden score
            (0.8, 0.9, False),  # Complex query despite high golden score
            (0.3, 0.3, False),  # Simple query but low golden score
        ]

        for complexity, golden_score, expected in test_cases:
            ctx = {
                "query": "test query",
                "query_signature": "test_sig",
                "confidence_scores": {"query_complexity": complexity, "golden_eligible": golden_score},
            }

            result = await step_20__golden_fast_gate(ctx=ctx)

            assert result["golden_fast_path_eligible"] == expected
            assert "eligibility_reason" in result
            if expected:
                assert result["next_step"] == 24
            else:
                assert result["next_step"] == 31

    @pytest.mark.asyncio
    async def test_missing_context_defaults_to_not_eligible(self):
        """Test handling of missing context data defaults to not eligible"""

        minimal_ctx = {"query": "test query"}

        result = await step_20__golden_fast_gate(ctx=minimal_ctx)

        assert result["golden_fast_path_eligible"] is False
        assert result["eligibility_reason"] == "missing_eligibility_data"
        assert result["next_step"] == 31
        assert "error" not in result  # Graceful handling

    @pytest.mark.asyncio
    async def test_preserve_context_from_both_paths(self):
        """Test context preservation from both Step 19 and Step 22 paths"""

        # From Step 19
        ctx_19 = {
            "rag_step": 19,
            "attachments_present": False,
            "query": "test",
            "query_signature": "sig1",
            "step_19_metadata": "preserved",
        }
        result_19 = await step_20__golden_fast_gate(ctx=ctx_19)
        assert "step_19_metadata" in result_19
        assert result_19["previous_step"] == 19

        # From Step 22
        ctx_22 = {
            "rag_step": 22,
            "doc_dependent": False,
            "query": "test",
            "query_signature": "sig2",
            "step_22_metadata": "preserved",
            "pre_ingest_results": {"processed": True},
        }
        result_22 = await step_20__golden_fast_gate(ctx=ctx_22)
        assert "step_22_metadata" in result_22
        assert "pre_ingest_results" in result_22
        assert result_22["previous_step"] == 22


class TestStep20IntegrationFlows:
    """Integration tests for Step 20 with neighboring steps"""

    @pytest.mark.asyncio
    async def test_step_19_to_20_no_attachments_flow(self):
        """Test flow from Step 19 (no attachments) to Step 20"""

        # Simulate Step 19 output when no attachments
        step_19_output = {
            "rag_step": 19,
            "step_id": "RAG.preflight.attachments.present",
            "attachments_present": False,
            "decision": "no_attachments",
            "route_to": "golden_fast_gate",
            "query": "What is the capital gains tax rate?",
            "query_signature": "cgt_query_sig",
            "canonical_facts": [{"type": "tax_type", "value": "capital gains"}],
        }

        result = await step_20__golden_fast_gate(ctx=step_19_output)

        assert result["previous_step"] == 19
        assert result["attachments_present"] is False
        assert "golden_fast_path_eligible" in result
        assert result["next_step"] in [24, 31]  # Valid next steps

    @pytest.mark.asyncio
    async def test_step_22_to_20_no_doc_dependency_flow(self):
        """Test flow from Step 22 (no doc dependency) to Step 20"""

        # Simulate Step 22 output when no doc dependency
        step_22_output = {
            "rag_step": 22,
            "step_id": "RAG.docs.doc.dependent.or.refers.to.doc",
            "doc_dependent": False,
            "decision": "no_dependency",
            "route_to": "golden_fast_gate",
            "query": "Standard VAT rate?",
            "query_signature": "vat_query_sig",
            "attachments": [{"name": "unrelated.pdf"}],
            "pre_ingest_results": {
                "doc_types": ["invoice"],
                "relevance_scores": [0.2],  # Low relevance
            },
        }

        result = await step_20__golden_fast_gate(ctx=step_22_output)

        assert result["previous_step"] == 22
        assert result["doc_dependent"] is False
        assert "pre_ingest_results" in result  # Context preserved
        assert "golden_fast_path_eligible" in result

    @pytest.mark.asyncio
    async def test_step_20_to_24_golden_lookup_flow(self):
        """Test flow from Step 20 to Step 24 (Golden Lookup) when eligible"""

        ctx = {
            "query": "What is the IVA rate?",
            "query_signature": "iva_sig_123",
            "confidence_scores": {"query_complexity": 0.2, "golden_eligible": 0.9},
        }

        result = await step_20__golden_fast_gate(ctx=ctx)

        assert result["golden_fast_path_eligible"] is True
        assert result["next_step"] == 24
        assert result["next_step_id"] == "RAG.golden.goldenset.match.by.signature.or.semantic"
        assert result["route_to"] == "GoldenLookup"
        # Data prepared for Step 24
        assert result["query_signature"] == "iva_sig_123"
        assert "golden_lookup_params" in result

    @pytest.mark.asyncio
    async def test_step_20_to_31_classify_domain_flow(self):
        """Test flow from Step 20 to Step 31 (Classify Domain) when not eligible"""

        ctx = {
            "query": "Analyze my complex multi-year tax situation with foreign income",
            "query_signature": "complex_sig_456",
            "confidence_scores": {"query_complexity": 0.85, "golden_eligible": 0.3},
        }

        result = await step_20__golden_fast_gate(ctx=ctx)

        assert result["golden_fast_path_eligible"] is False
        assert result["next_step"] == 31
        assert result["next_step_id"] == "RAG.classify.domainactionclassifier.classify.rule.based.classification"
        assert result["route_to"] == "ClassifyDomain"
        # Context prepared for classification
        assert "classification_context" in result


class TestStep20ParityAndBehavior:
    """Parity tests ensuring Step 20 meets behavioral definition of done"""

    @pytest.mark.asyncio
    async def test_behavioral_golden_fast_path_decision(self):
        """
        BEHAVIORAL TEST: Step 20 must make a binary decision about golden fast path eligibility
        based on query complexity and context, routing to either Step 24 or Step 31.
        """

        # Test eligible path
        eligible_ctx = {
            "query": "What is the VAT rate?",
            "query_signature": "vat_sig",
            "confidence_scores": {"query_complexity": 0.2, "golden_eligible": 0.8},
        }

        result = await step_20__golden_fast_gate(ctx=eligible_ctx)

        # Must make binary decision
        assert isinstance(result["golden_fast_path_eligible"], bool)
        assert result["golden_fast_path_eligible"] is True
        # Must route to Step 24
        assert result["next_step"] == 24
        assert result["route_to"] == "GoldenLookup"

        # Test not eligible path
        not_eligible_ctx = {
            "query": "Complex analysis needed",
            "query_signature": "complex_sig",
            "confidence_scores": {"query_complexity": 0.9, "golden_eligible": 0.2},
        }

        result = await step_20__golden_fast_gate(ctx=not_eligible_ctx)

        # Must make binary decision
        assert result["golden_fast_path_eligible"] is False
        # Must route to Step 31
        assert result["next_step"] == 31
        assert result["route_to"] == "ClassifyDomain"

    @pytest.mark.asyncio
    async def test_behavioral_mermaid_flow_compliance(self):
        """
        BEHAVIORAL TEST: Step 20 must comply with Mermaid flow:
        - Receives from Step 19 (AttachCheck→No) OR Step 22 (DocDependent→No)
        - Routes to Step 24 (GoldenLookup) OR Step 31 (ClassifyDomain)
        """

        # From Step 19 path
        from_19 = {"rag_step": 19, "attachments_present": False, "query": "test", "query_signature": "test_sig"}
        result = await step_20__golden_fast_gate(ctx=from_19)
        assert result["previous_step"] == 19
        assert result["next_step"] in [24, 31]

        # From Step 22 path
        from_22 = {"rag_step": 22, "doc_dependent": False, "query": "test", "query_signature": "test_sig"}
        result = await step_20__golden_fast_gate(ctx=from_22)
        assert result["previous_step"] == 22
        assert result["next_step"] in [24, 31]

    @pytest.mark.asyncio
    async def test_behavioral_context_preservation(self):
        """
        BEHAVIORAL TEST: Step 20 must preserve all context from previous steps
        while adding eligibility decision metadata.
        """

        original_ctx = {
            "rag_step": 19,
            "query": "Test query",
            "query_signature": "sig123",
            "canonical_facts": [{"type": "test", "value": "data"}],
            "attachments_present": False,
            "custom_metadata": {"key": "value"},
            "confidence_scores": {"query_complexity": 0.3, "golden_eligible": 0.7},
        }

        result = await step_20__golden_fast_gate(ctx=original_ctx)

        # All original context must be preserved
        assert result["query"] == original_ctx["query"]
        assert result["query_signature"] == original_ctx["query_signature"]
        assert result["canonical_facts"] == original_ctx["canonical_facts"]
        assert result["attachments_present"] == original_ctx["attachments_present"]
        assert result["custom_metadata"] == original_ctx["custom_metadata"]

        # New eligibility metadata must be added
        assert "golden_fast_path_eligible" in result
        assert "eligibility_reason" in result
        assert "next_step" in result
        assert "route_to" in result

    @pytest.mark.asyncio
    async def test_behavioral_structured_observability(self):
        """
        BEHAVIORAL TEST: Step 20 must implement structured observability
        with rag_step_log and rag_step_timer per MASTER_GUARDRAILS.
        """

        with (
            patch("app.orchestrators.golden.rag_step_log") as mock_log,
            patch("app.orchestrators.golden.rag_step_timer") as mock_timer,
        ):
            ctx = {
                "query": "test",
                "query_signature": "sig",
                "confidence_scores": {"query_complexity": 0.3, "golden_eligible": 0.7},
            }

            await step_20__golden_fast_gate(ctx=ctx)

            # Verify structured logging
            mock_log.assert_called()
            log_calls = mock_log.call_args_list

            # Check required log attributes
            start_log = log_calls[0][1]  # kwargs from first call
            assert start_log["step"] == 20
            assert start_log["step_id"] == "RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe"
            assert start_log["node_label"] == "GoldenFastGate"
            assert start_log["category"] == "golden"
            assert start_log["type"] == "process"

            # Verify timing
            mock_timer.assert_called_with(
                20,
                "RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe",
                "GoldenFastGate",
                request_id="unknown",
                stage="start",
            )
