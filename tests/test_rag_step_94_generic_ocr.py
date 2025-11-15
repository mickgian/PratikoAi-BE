"""
Tests for RAG STEP 94 — GenericOCR.parse_with_layout (RAG.docs.genericocr.parse.with.layout)

This process step performs layout-aware OCR on generic documents that don't match specific parsers.
Extracts text content while preserving document structure for downstream processing.
"""

from unittest.mock import patch

import pytest


class TestRAGStep94GenericOCR:
    """Test suite for RAG STEP 94 - Generic OCR parser."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_94_parse_generic_pdf(self, mock_rag_log):
        """Test Step 94: Parse generic PDF with OCR."""
        from app.orchestrators.docs import step_94__generic_ocr

        # Simulated generic document content
        generic_pdf = b"""%PDF-1.4
        DOCUMENTO GENERICO

        Oggetto: Comunicazione importante
        Data: 15 Marzo 2024

        Testo del documento:
        Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

        Cordiali saluti,
        Amministrazione
        %%EOF"""

        classified_docs = [
            {
                "filename": "documento_generico.pdf",
                "document_type": "generic",
                "content": generic_pdf,
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-94-generic"}

        result = await step_94__generic_ocr(messages=[], ctx=ctx)

        # Should parse successfully
        assert isinstance(result, dict)
        assert result["parsing_completed"] is True
        assert result["document_count"] == 1
        assert result["parsed_docs"][0]["parsed_successfully"] is True
        assert result["request_id"] == "test-94-generic"

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 94
        assert completed_log["node_label"] == "GenericOCR"
        assert completed_log["parsing_completed"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_94_extract_text_content(self, mock_rag_log):
        """Test Step 94: Extract text content from generic document."""
        from app.orchestrators.docs import step_94__generic_ocr

        # Generic document with text
        generic_content = b"""COMUNICAZIONE

        Spett.le Cliente,

        Con la presente si comunica che...

        Data: 20/04/2024
        Protocollo: ABC123"""

        classified_docs = [
            {
                "filename": "comunicazione.pdf",
                "document_type": "generic",
                "content": generic_content,
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-94-extract"}

        result = await step_94__generic_ocr(messages=[], ctx=ctx)

        # Should extract text
        assert result["parsing_completed"] is True
        parsed_doc = result["parsed_docs"][0]
        assert "extracted_text" in parsed_doc
        text = parsed_doc["extracted_text"]
        assert "COMUNICAZIONE" in text
        assert "Protocollo: ABC123" in text

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_94_empty_document(self, mock_rag_log):
        """Test Step 94: Handle empty document gracefully."""
        from app.orchestrators.docs import step_94__generic_ocr

        classified_docs = [
            {
                "filename": "empty.pdf",
                "document_type": "generic",
                "content": b"%PDF-1.4\n%%EOF",
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-94-empty"}

        result = await step_94__generic_ocr(messages=[], ctx=ctx)

        # Should handle gracefully
        assert result["parsing_completed"] is True
        parsed_doc = result["parsed_docs"][0]
        assert parsed_doc["parsed_successfully"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_94_routes_to_extract_facts(self, mock_rag_log):
        """Test Step 94: Routes to Step 95 (ExtractDocFacts)."""
        from app.orchestrators.docs import step_94__generic_ocr

        generic_content = b"""DOCUMENTO
        Contenuto generico del documento
        Data: 01/05/2024"""

        classified_docs = [
            {
                "filename": "doc.pdf",
                "document_type": "generic",
                "content": generic_content,
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-94-route"}

        result = await step_94__generic_ocr(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result["next_step"] == "extract_doc_facts"  # Routes to Step 95


class TestRAGStep94Parity:
    """Parity tests proving Step 94 preserves existing OCR logic."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_94_parity_layout_preservation(self, mock_rag_log):
        """Test Step 94: Parity with layout-aware OCR."""
        from app.orchestrators.docs import step_94__generic_ocr

        # Document with layout structure
        generic_pdf = b"""MODULO

        Sezione A: Dati anagrafici
        Nome: Mario Rossi

        Sezione B: Indirizzo
        Via Roma 123, Milano"""

        classified_docs = [
            {
                "filename": "modulo.pdf",
                "document_type": "generic",
                "content": generic_pdf,
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-parity"}

        result = await step_94__generic_ocr(messages=[], ctx=ctx)

        # Should preserve layout
        assert result["parsing_completed"] is True
        assert result["parsed_docs"][0]["parsed_successfully"] is True


class TestRAGStep94Integration:
    """Integration tests for Step 89 → Step 94 → Step 95 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_89_to_94_integration(self, mock_rag_log):
        """Test Step 89 (route) → Step 94 (parse) integration."""
        from app.orchestrators.docs import step_89__doc_type, step_94__generic_ocr

        # Step 89: Route generic document
        classified_docs = [
            {
                "filename": "lettera.pdf",
                "document_type": "generic",
                "content": b"""LETTERA

                Egregio Sig. Rossi,

                Con la presente...

                Distinti saluti""",
                "mime_type": "application/pdf",
            }
        ]

        step_89_ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-integration-89-94"}

        step_89_result = await step_89__doc_type(messages=[], ctx=step_89_ctx)

        # Should route to generic_ocr
        assert step_89_result["routing_completed"] is True
        assert step_89_result["next_step"] == "generic_ocr"

        # Step 94: Parse with OCR
        step_94_ctx = {
            "classified_docs": step_89_result["classified_docs"],
            "document_count": step_89_result["document_count"],
            "request_id": step_89_result["request_id"],
        }

        step_94_result = await step_94__generic_ocr(messages=[], ctx=step_94_ctx)

        # Should parse successfully
        assert step_94_result["parsing_completed"] is True
        assert step_94_result["next_step"] == "extract_doc_facts"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_94_to_95_flow(self, mock_rag_log):
        """Test Step 94 → Step 95 (extract facts) flow."""
        from app.orchestrators.docs import step_94__generic_ocr

        generic_content = b"""CERTIFICATO

        Si certifica che il Sig. Giuseppe Verdi
        ha partecipato al corso di formazione
        dal 10/01/2024 al 15/03/2024

        Durata: 40 ore
        Esito: Positivo"""

        classified_docs = [
            {
                "filename": "certificato.pdf",
                "document_type": "generic",
                "content": generic_content,
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-94-to-95"}

        result = await step_94__generic_ocr(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result["next_step"] == "extract_doc_facts"
        assert result["parsing_completed"] is True

        # Context ready for Step 95
        assert "parsed_docs" in result
        assert len(result["parsed_docs"]) > 0
        assert result["parsed_docs"][0]["parsed_successfully"] is True
