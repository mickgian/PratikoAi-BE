"""
Tests for RAG STEP 23 — PlannerHint.require_doc_ingest_first ingest then Golden and KB
(RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb)

This process step sets planning hints when documents need to be ingested before proceeding
with Golden Set and KB queries. It coordinates the document-first workflow.
"""

from unittest.mock import patch

import pytest


class TestRAGStep23RequireDocIngest:
    """Test suite for RAG STEP 23 - Require document ingest planner hint."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_23_sets_doc_ingest_priority(self, mock_rag_log):
        """Test Step 23: Sets document ingest as priority before Golden/KB."""
        from app.orchestrators.golden import step_23__require_doc_ingest

        ctx = {
            "user_query": "Analizza la fattura e dimmi il totale IVA",
            "query_depends_on_doc": True,
            "extracted_docs": [{"filename": "fattura.pdf", "potential_category": "fattura_elettronica"}],
            "document_count": 1,
            "request_id": "test-23-priority",
        }

        result = await step_23__require_doc_ingest(messages=[], ctx=ctx)

        # Should set planning hints
        assert isinstance(result, dict)
        assert result["requires_doc_ingest_first"] is True
        assert result["planning_hint"] == "doc_ingest_before_golden_kb"
        assert result["next_step"] == "classify_domain"  # Routes to Step 31

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 23
        assert completed_log["node_label"] == "RequireDocIngest"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_23_preserves_context(self, mock_rag_log):
        """Test Step 23: Preserves all context from previous step."""
        from app.orchestrators.golden import step_23__require_doc_ingest

        ctx = {
            "user_query": "Verifica il contratto allegato",
            "query_depends_on_doc": True,
            "extracted_docs": [{"filename": "contratto.pdf"}],
            "document_count": 1,
            "request_id": "test-23-context",
            "other_field": "preserved_value",
            "query_signature": "abc123",
        }

        result = await step_23__require_doc_ingest(messages=[], ctx=ctx)

        # Should preserve all context
        assert result["user_query"] == "Verifica il contratto allegato"
        assert result["query_depends_on_doc"] is True
        assert result["other_field"] == "preserved_value"
        assert result["query_signature"] == "abc123"
        assert result["request_id"] == "test-23-context"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_23_routes_to_classification(self, mock_rag_log):
        """Test Step 23: Routes to Step 31 (ClassifyDomain) per Mermaid."""
        from app.orchestrators.golden import step_23__require_doc_ingest

        ctx = {
            "user_query": "Leggi il documento",
            "query_depends_on_doc": True,
            "extracted_docs": [{"filename": "doc.pdf"}],
            "request_id": "test-23-route",
        }

        result = await step_23__require_doc_ingest(messages=[], ctx=ctx)

        # Per Mermaid: RequireDocIngest → ClassifyDomain (Step 31)
        assert result["next_step"] == "classify_domain"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_23_includes_processing_metadata(self, mock_rag_log):
        """Test Step 23: Includes processing metadata for downstream steps."""
        from app.orchestrators.golden import step_23__require_doc_ingest

        ctx = {
            "user_query": "Controlla la busta paga",
            "query_depends_on_doc": True,
            "extracted_docs": [{"filename": "payslip.pdf", "potential_category": "payslip"}],
            "document_count": 1,
            "request_id": "test-23-metadata",
        }

        result = await step_23__require_doc_ingest(messages=[], ctx=ctx)

        # Should include processing metadata
        assert "processing_metadata" in result
        metadata = result["processing_metadata"]
        assert metadata["requires_doc_ingest"] is True
        assert metadata["workflow"] == "doc_first_then_golden_kb"
        assert metadata["document_count"] == 1

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_23_handles_multiple_documents(self, mock_rag_log):
        """Test Step 23: Handles multiple document references."""
        from app.orchestrators.golden import step_23__require_doc_ingest

        ctx = {
            "user_query": "Confronta i due contratti",
            "query_depends_on_doc": True,
            "extracted_docs": [{"filename": "contratto1.pdf"}, {"filename": "contratto2.pdf"}],
            "document_count": 2,
            "request_id": "test-23-multi",
        }

        result = await step_23__require_doc_ingest(messages=[], ctx=ctx)

        assert result["requires_doc_ingest_first"] is True
        assert result["processing_metadata"]["document_count"] == 2

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_23_sets_workflow_priority(self, mock_rag_log):
        """Test Step 23: Sets correct workflow priority flags."""
        from app.orchestrators.golden import step_23__require_doc_ingest

        ctx = {
            "user_query": "Estrai dati dalla fattura",
            "query_depends_on_doc": True,
            "extracted_docs": [{"filename": "invoice.pdf"}],
            "request_id": "test-23-priority-flags",
        }

        result = await step_23__require_doc_ingest(messages=[], ctx=ctx)

        # Should set priority flags for orchestration
        assert result["requires_doc_ingest_first"] is True
        assert result["defer_golden_lookup"] is True
        assert result["defer_kb_search"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_23_logs_planner_hint(self, mock_rag_log):
        """Test Step 23: Logs planner hint with correct attributes."""
        from app.orchestrators.golden import step_23__require_doc_ingest

        ctx = {
            "user_query": "Verifica la fattura",
            "query_depends_on_doc": True,
            "extracted_docs": [{"filename": "fattura.xml"}],
            "request_id": "test-23-log",
        }

        await step_23__require_doc_ingest(messages=[], ctx=ctx)

        # Verify logging includes planner hint
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        log = completed_logs[0][1]
        assert log["step"] == 23
        assert log["planning_hint"] == "doc_ingest_before_golden_kb"


class TestRAGStep23Parity:
    """Parity tests proving Step 23 coordination logic is correct."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_23_parity_workflow_flags(self, mock_rag_log):
        """Test Step 23: Workflow flags match expected behavior."""
        from app.orchestrators.golden import step_23__require_doc_ingest

        ctx = {
            "user_query": "Leggi il documento allegato",
            "query_depends_on_doc": True,
            "extracted_docs": [{"filename": "doc.pdf"}],
            "request_id": "parity-test",
        }

        result = await step_23__require_doc_ingest(messages=[], ctx=ctx)

        # Verify parity: planning flags are set correctly
        assert result["requires_doc_ingest_first"] is True
        assert result["defer_golden_lookup"] is True
        assert result["defer_kb_search"] is True
        assert result["planning_hint"] == "doc_ingest_before_golden_kb"


class TestRAGStep23Integration:
    """Integration tests for Step 22 → Step 23 → Step 31 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_22_to_23_integration(self, mock_golden_log):
        """Test Step 22 (DocDependent) → Step 23 (RequireDocIngest) integration."""
        from app.orchestrators.docs import step_22__doc_dependent_check
        from app.orchestrators.golden import step_23__require_doc_ingest

        # Step 22: Document dependency check (YES branch)
        step_22_ctx = {
            "user_query": "Analizza la fattura allegata",
            "extracted_docs": [{"filename": "fattura.pdf"}],
            "document_count": 1,
            "request_id": "integration-22-23",
        }

        step_22_result = await step_22__doc_dependent_check(messages=[], ctx=step_22_ctx)

        # Verify Step 22 routes to Step 23
        assert step_22_result["query_depends_on_doc"] is True
        assert step_22_result["next_step"] == "require_doc_processing"

        # Step 23: Set planner hint
        step_23_result = await step_23__require_doc_ingest(messages=[], ctx=step_22_result)

        # Should route to classification with doc-first flags
        assert step_23_result["requires_doc_ingest_first"] is True
        assert step_23_result["next_step"] == "classify_domain"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_23_prepares_for_step_31(self, mock_rag_log):
        """Test Step 23: Prepares output for Step 31 (ClassifyDomain)."""
        from app.orchestrators.golden import step_23__require_doc_ingest

        ctx = {
            "user_query": "Estrai dati dal contratto",
            "query_depends_on_doc": True,
            "extracted_docs": [{"filename": "contract.pdf"}],
            "request_id": "test-23-prep-31",
        }

        result = await step_23__require_doc_ingest(messages=[], ctx=ctx)

        # Should have everything Step 31 needs
        assert result["next_step"] == "classify_domain"
        assert result["user_query"] == "Estrai dati dal contratto"
        assert result["requires_doc_ingest_first"] is True
        assert "processing_metadata" in result
