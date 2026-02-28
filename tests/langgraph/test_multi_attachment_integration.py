"""TDD Integration Tests for Multi-Attachment Context Bug.

DEV-007: Verify BOTH payslips appear in merged_context sent to LLM.

ROOT CAUSE: Token budget exhaustion in ContextBuilderMerge
- Default budget: 3500 tokens
- document_facts weight: 0.2 (only 700 tokens effective)
- Single payslip: ~1500-2500 tokens
- Result: Payslip 8 consumes budget → Payslip 9 TRUNCATED

Written BEFORE the fix to ensure TDD approach.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestMultiAttachmentContextIntegration:
    """Integration tests verifying multiple attachments appear in LLM context."""

    @pytest.mark.asyncio
    async def test_both_current_attachments_appear_in_merged_context(self):
        """CRITICAL: Both Payslip 8 AND Payslip 9 content MUST appear in merged_context.

        This is THE critical integration test for the multi-attachment bug.
        """
        from app.services.context_builder_merge import ContextBuilderMerge

        builder = ContextBuilderMerge()

        # Given: Multiple document_facts from different payslips
        document_facts = [
            "DOCUMENTO: Payslip 8 - Agosto 2025\nPAYSLIP_8_UNIQUE_CONTENT_AGOSTO\nPeriodo: 01/08/2025 - 31/08/2025",
            "DOCUMENTO: Payslip 9 - Settembre 2025\nPAYSLIP_9_UNIQUE_CONTENT_SETTEMBRE\nPeriodo: 01/09/2025 - 30/09/2025",
        ]

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": document_facts,
            "query": "E queste?",
            "query_composition": "pure_doc",  # User is asking about documents only
            "max_context_tokens": 8000,  # Ensure enough budget
        }

        # When: ContextBuilderMerge processes the context
        result = builder.merge_context(context_data)
        merged_context = result.get("merged_context", "")

        # Then: BOTH document facts MUST be in the context
        assert "PAYSLIP_8_UNIQUE_CONTENT_AGOSTO" in merged_context, (
            f"Payslip 8 content missing from merged_context!\nGot: {merged_context[:500]}..."
        )
        assert "PAYSLIP_9_UNIQUE_CONTENT_SETTEMBRE" in merged_context, (
            f"Payslip 9 content missing from merged_context!\nGot: {merged_context[:500]}..."
        )

    @pytest.mark.asyncio
    async def test_pure_doc_composition_increases_document_priority(self):
        """When query_composition is 'pure_doc', document_facts should get higher priority."""
        from app.services.context_builder_merge import (
            ContextBuilderMerge,
            get_composition_priority_weights,
        )

        # Given: pure_doc composition
        weights = get_composition_priority_weights("pure_doc")

        # Then: document_facts should have high weight (at least 0.5)
        assert weights["document_facts"] >= 0.5, (
            f"pure_doc should prioritize document_facts! Got weight: {weights['document_facts']}"
        )

    @pytest.mark.asyncio
    async def test_multiple_documents_get_adequate_token_budget(self):
        """Multiple documents should get enough token budget to include all content."""
        from app.services.context_builder_merge import ContextBuilderMerge

        builder = ContextBuilderMerge()

        # Given: Two large document facts (~1500 tokens each)
        large_doc_1 = "DOCUMENT_1_START " + "word " * 500 + " DOCUMENT_1_END"  # ~500 words ≈ ~700 tokens
        large_doc_2 = "DOCUMENT_2_START " + "word " * 500 + " DOCUMENT_2_END"

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": [large_doc_1, large_doc_2],
            "query": "Analizza questi documenti",
            "query_composition": "pure_doc",
        }

        # When
        result = builder.merge_context(context_data)
        merged_context = result.get("merged_context", "")

        # Then: BOTH documents should be present
        assert "DOCUMENT_1_START" in merged_context and "DOCUMENT_1_END" in merged_context, (
            "Document 1 should be fully included"
        )
        assert "DOCUMENT_2_START" in merged_context and "DOCUMENT_2_END" in merged_context, (
            "Document 2 should be fully included"
        )


class TestContextBuilderBudgetScaling:
    """Test that token budget scales appropriately for multiple documents."""

    def test_budget_increases_for_multiple_document_facts(self):
        """Token budget should increase when multiple document_facts are present."""
        from app.services.context_builder_merge import ContextBuilderMerge

        builder = ContextBuilderMerge()

        # Given: Multiple document facts
        document_facts = [
            "Document 1 content...",
            "Document 2 content...",
            "Document 3 content...",
        ]

        # When: Calculating budget (this tests the FIX)
        # The fix should add additional budget for multiple documents
        base_budget = builder.default_max_tokens  # 3500

        # Then: Budget should be higher than base when multiple docs present
        # After fix: Each additional doc should add ~2000 tokens
        expected_min_budget = base_budget + 2000  # At least one increase for doc 2

        # This test will FAIL before the fix is implemented
        # because calculate_optimal_budget doesn't consider document_facts count
        assert builder.max_budget_limit >= expected_min_budget, (
            f"Max budget {builder.max_budget_limit} should accommodate multiple documents"
        )


class TestStep40DocumentFactsIntegration:
    """Integration tests for Step 40 -> ContextBuilder flow."""

    @pytest.mark.asyncio
    async def test_step40_converts_attachments_to_doc_facts(self):
        """Step 40 should convert attachments to document_facts and pass to ContextBuilder.

        Note: This is a unit test for the conversion logic. Full integration
        requires actual attachment processing infrastructure.
        """
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        # Given: Attachments with extracted_text
        attachments = [
            {
                "filename": "Payslip 8 - Agosto 2025.pdf",
                "extracted_text": "PAYSLIP_8_AUGUST_DATA Nome: Giannone Michele",
                "message_index": 1,
            },
            {
                "filename": "Payslip 9 - Settembre 2025.pdf",
                "extracted_text": "PAYSLIP_9_SEPTEMBER_DATA Nome: Giannone Michele",
                "message_index": 1,
            },
        ]

        # When: Converting attachments to doc_facts
        doc_facts, pii_map = _convert_attachments_to_doc_facts(attachments, current_message_index=1)

        # Then: ALL attachments should become doc_facts
        assert len(doc_facts) == 2, f"Should have 2 doc_facts, got {len(doc_facts)}"

        # Verify both payslips are represented in doc_facts
        all_doc_facts_text = " ".join(doc_facts)
        # Note: The content may be anonymized, so check for filename presence
        assert "Payslip 8" in all_doc_facts_text or "PAYSLIP_8" in all_doc_facts_text, (
            "Payslip 8 should be in doc_facts"
        )
        assert "Payslip 9" in all_doc_facts_text or "PAYSLIP_9" in all_doc_facts_text, (
            "Payslip 9 should be in doc_facts"
        )


class TestMultiAttachmentRegressionScenarios:
    """Regression tests for specific user scenarios."""

    @pytest.mark.asyncio
    async def test_turn2_multiple_payslips_both_analyzed(self):
        """Turn 2: Upload Payslip 8 + Payslip 9, BOTH must appear in context.

        Regression test for: User uploads Payslip 8+9 in Turn 2, but only Payslip 8 analyzed.
        """
        from app.services.context_builder_merge import ContextBuilderMerge

        builder = ContextBuilderMerge()

        # Given: Exact scenario from user bug report
        # Turn 2 has two payslips, user asks "E queste?"
        document_facts = [
            # Payslip 8 content (as it would be extracted)
            """DOCUMENTO ALLEGATO: Payslip 8 - Agosto 2025.pdf

            Cedolino di pagamento per il mese di agosto 2025.
            Nome: Giannone Michele (MICGIA)
            Indirizzo: Via dei ciclamini 32, 96018 Pachino, Italy
            Data di pagamento: 31/08/2025
            Periodo di riferimento: 01/08/2025 - 31/08/2025
            Stipendio lordo: 50,000.00 €
            Totale netto: 5,000.00 €

            UNIQUE_MARKER_PAYSLIP_8_AGOSTO""",
            # Payslip 9 content
            """DOCUMENTO ALLEGATO: Payslip 9 - Settembre 2025.pdf

            Cedolino di pagamento per il mese di settembre 2025.
            Nome: Giannone Michele (MICGIA)
            Indirizzo: Via dei ciclamini 32, 96018 Pachino, Italy
            Data di pagamento: 30/09/2025
            Periodo di riferimento: 01/09/2025 - 30/09/2025
            Stipendio lordo: 50,000.00 €
            Totale netto: 5,000.00 €

            UNIQUE_MARKER_PAYSLIP_9_SETTEMBRE""",
        ]

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": document_facts,
            "query": "E queste?",
            "query_composition": "pure_doc",
        }

        # When
        result = builder.merge_context(context_data)
        merged_context = result.get("merged_context", "")

        # Then: BOTH payslips MUST be in context
        assert "UNIQUE_MARKER_PAYSLIP_8_AGOSTO" in merged_context, (
            f"Payslip 8 (August) must be in context! Bug: Only first document included.\n"
            f"Context preview: {merged_context[:300]}..."
        )
        assert "UNIQUE_MARKER_PAYSLIP_9_SETTEMBRE" in merged_context, (
            f"Payslip 9 (September) must be in context! Bug: Second document truncated.\n"
            f"Context preview: {merged_context[:300]}..."
        )
