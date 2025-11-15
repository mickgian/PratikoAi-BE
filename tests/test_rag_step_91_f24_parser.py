"""
Tests for RAG STEP 91 — F24Parser.parse_ocr Layout aware OCR (RAG.docs.f24parser.parse.ocr.layout.aware.ocr)

This process step parses Italian F24 tax payment forms using layout-aware OCR.
Extracts structured fields like tax codes, amounts, and payment periods for downstream processing.
"""

from unittest.mock import patch

import pytest


class TestRAGStep91F24Parser:
    """Test suite for RAG STEP 91 - F24 tax form parser."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_91_parse_f24_pdf(self, mock_rag_log):
        """Test Step 91: Parse F24 PDF with OCR."""
        from app.orchestrators.docs import step_91__f24_parser

        # Simulated F24 PDF content (binary marker)
        f24_pdf = b"%PDF-1.4\nF24 TAX FORM\nCodice Tributo: 4001\nImporto: 1500.00\nPeriodo: 01/2024\n%%EOF"

        classified_docs = [
            {
                "filename": "f24_gennaio_2024.pdf",
                "document_type": "f24",
                "content": f24_pdf,
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-91-f24"}

        result = await step_91__f24_parser(messages=[], ctx=ctx)

        # Should parse successfully
        assert isinstance(result, dict)
        assert result["parsing_completed"] is True
        assert result["document_count"] == 1
        assert result["parsed_docs"][0]["parsed_successfully"] is True
        assert result["request_id"] == "test-91-f24"

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 91
        assert completed_log["node_label"] == "F24Parser"
        assert completed_log["parsing_completed"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_91_extract_f24_fields(self, mock_rag_log):
        """Test Step 91: Extract key fields from F24 form."""
        from app.orchestrators.docs import step_91__f24_parser

        # F24 with structured tax data
        f24_content = b"""F24 MODULO
        CODICE TRIBUTO: 1040
        RATEAZIONE: 0101
        ANNO RIFERIMENTO: 2024
        IMPORTO A DEBITO: 2500.00
        PERIODO: 03/2024"""

        classified_docs = [
            {
                "filename": "f24_marzo.pdf",
                "document_type": "f24",
                "content": f24_content,
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-91-extract"}

        result = await step_91__f24_parser(messages=[], ctx=ctx)

        # Should extract key fields
        assert result["parsing_completed"] is True
        parsed_doc = result["parsed_docs"][0]
        assert "extracted_fields" in parsed_doc
        fields = parsed_doc["extracted_fields"]
        assert fields.get("codice_tributo") == "1040"
        assert fields.get("importo") == "2500.00"
        assert fields.get("anno") == "2024"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_91_invalid_f24(self, mock_rag_log):
        """Test Step 91: Handle invalid F24 gracefully."""
        from app.orchestrators.docs import step_91__f24_parser

        classified_docs = [
            {
                "filename": "not_f24.pdf",
                "document_type": "f24",
                "content": b"%PDF-1.4\nNot a valid F24 form\n%%EOF",
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-91-invalid"}

        result = await step_91__f24_parser(messages=[], ctx=ctx)

        # Should handle error gracefully
        assert result["parsing_completed"] is True
        parsed_doc = result["parsed_docs"][0]
        assert parsed_doc["parsed_successfully"] is False
        assert "error" in parsed_doc

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_91_routes_to_extract_facts(self, mock_rag_log):
        """Test Step 91: Routes to Step 95 (ExtractDocFacts)."""
        from app.orchestrators.docs import step_91__f24_parser

        f24_content = b"F24 FORM\nCODICE: 4001\nIMPORTO: 1000.00"

        classified_docs = [
            {"filename": "f24.pdf", "document_type": "f24", "content": f24_content, "mime_type": "application/pdf"}
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-91-route"}

        result = await step_91__f24_parser(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result["next_step"] == "extract_doc_facts"  # Routes to Step 95


class TestRAGStep91Parity:
    """Parity tests proving Step 91 preserves existing F24 parsing logic."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_91_parity_ocr_layout(self, mock_rag_log):
        """Test Step 91: Parity with layout-aware OCR."""
        from app.orchestrators.docs import step_91__f24_parser

        # F24 with layout structure
        f24_pdf = b"""%PDF-1.4
        SEZIONE ERARIO
        CODICE TRIBUTO    RATEAZIONE    ANNO    IMPORTO
        1001              0101          2024    5000.00
        %%EOF"""

        classified_docs = [
            {"filename": "f24_layout.pdf", "document_type": "f24", "content": f24_pdf, "mime_type": "application/pdf"}
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-parity"}

        result = await step_91__f24_parser(messages=[], ctx=ctx)

        # Should handle layout correctly
        assert result["parsing_completed"] is True
        assert result["parsed_docs"][0]["parsed_successfully"] is True


class TestRAGStep91Integration:
    """Integration tests for Step 89 → Step 91 → Step 95 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_89_to_91_integration(self, mock_rag_log):
        """Test Step 89 (route) → Step 91 (parse) integration."""
        from app.orchestrators.docs import step_89__doc_type, step_91__f24_parser

        # Step 89: Route F24 document
        classified_docs = [
            {
                "filename": "F24_2024.pdf",
                "document_type": "f24",
                "content": b"F24 FORM\nCODICE: 1040\nIMPORTO: 3000.00\nANNO: 2024",
                "mime_type": "application/pdf",
            }
        ]

        step_89_ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-integration-89-91"}

        step_89_result = await step_89__doc_type(messages=[], ctx=step_89_ctx)

        # Should route to f24_parser
        assert step_89_result["routing_completed"] is True
        assert step_89_result["next_step"] == "f24_parser"

        # Step 91: Parse F24
        step_91_ctx = {
            "classified_docs": step_89_result["classified_docs"],
            "document_count": step_89_result["document_count"],
            "request_id": step_89_result["request_id"],
        }

        step_91_result = await step_91__f24_parser(messages=[], ctx=step_91_ctx)

        # Should parse successfully
        assert step_91_result["parsing_completed"] is True
        assert step_91_result["next_step"] == "extract_doc_facts"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_91_to_95_flow(self, mock_rag_log):
        """Test Step 91 → Step 95 (extract facts) flow."""
        from app.orchestrators.docs import step_91__f24_parser

        f24_content = b"""F24 TAX PAYMENT
        CODICE TRIBUTO: 4001
        IMPORTO: 15000.00
        ANNO RIFERIMENTO: 2024
        PERIODO: 12/2024"""

        classified_docs = [
            {
                "filename": "f24_dicembre.pdf",
                "document_type": "f24",
                "content": f24_content,
                "mime_type": "application/pdf",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-91-to-95"}

        result = await step_91__f24_parser(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result["next_step"] == "extract_doc_facts"
        assert result["parsing_completed"] is True

        # Context ready for Step 95
        assert "parsed_docs" in result
        assert len(result["parsed_docs"]) > 0
        assert result["parsed_docs"][0]["parsed_successfully"] is True
