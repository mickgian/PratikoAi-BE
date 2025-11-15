"""
Tests for RAG STEP 90 — FatturaParser.parse_xsd XSD validation (RAG.docs.fatturaparser.parse.xsd.xsd.validation)

This process step parses and validates Italian electronic invoices (Fattura Elettronica) XML files.
Validates against XSD schema and extracts key invoice data for downstream processing.
"""

from unittest.mock import patch

import pytest


class TestRAGStep90FatturaParser:
    """Test suite for RAG STEP 90 - Fattura XML parser."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_90_parse_fattura_xml(self, mock_rag_log):
        """Test Step 90: Parse valid Fattura Elettronica XML."""
        from app.orchestrators.docs import step_90__fattura_parser

        # Simplified Fattura XML structure
        fattura_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
    <FatturaElettronicaHeader>
        <DatiTrasmissione>
            <IdTrasmittente>
                <IdPaese>IT</IdPaese>
                <IdCodice>12345678901</IdCodice>
            </IdTrasmittente>
        </DatiTrasmissione>
        <CedentePrestatore>
            <DatiAnagrafici>
                <Anagrafica>
                    <Denominazione>Acme Corp</Denominazione>
                </Anagrafica>
            </DatiAnagrafici>
        </CedentePrestatore>
    </FatturaElettronicaHeader>
    <FatturaElettronicaBody>
        <DatiGenerali>
            <DatiGeneraliDocumento>
                <TipoDocumento>TD01</TipoDocumento>
                <Numero>001</Numero>
                <Data>2024-01-15</Data>
                <ImportoTotaleDocumento>1220.00</ImportoTotaleDocumento>
            </DatiGeneraliDocumento>
        </DatiGenerali>
    </FatturaElettronicaBody>
</p:FatturaElettronica>"""

        classified_docs = [
            {
                "filename": "IT12345678901_001.xml",
                "document_type": "fattura_elettronica",
                "content": fattura_xml,
                "mime_type": "application/xml",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-90-fattura"}

        result = await step_90__fattura_parser(messages=[], ctx=ctx)

        # Should parse successfully
        assert isinstance(result, dict)
        assert result["parsing_completed"] is True
        assert result["document_count"] == 1
        assert result["parsed_docs"][0]["parsed_successfully"] is True
        assert result["request_id"] == "test-90-fattura"

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 90
        assert completed_log["node_label"] == "FatturaParser"
        assert completed_log["parsing_completed"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_90_extract_fattura_fields(self, mock_rag_log):
        """Test Step 90: Extract key fields from Fattura XML."""
        from app.orchestrators.docs import step_90__fattura_parser

        fattura_xml = b"""<?xml version="1.0"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
    <FatturaElettronicaBody>
        <DatiGenerali>
            <DatiGeneraliDocumento>
                <TipoDocumento>TD01</TipoDocumento>
                <Numero>123</Numero>
                <Data>2024-06-15</Data>
                <ImportoTotaleDocumento>5000.00</ImportoTotaleDocumento>
            </DatiGeneraliDocumento>
        </DatiGenerali>
    </FatturaElettronicaBody>
</p:FatturaElettronica>"""

        classified_docs = [
            {
                "filename": "fattura_123.xml",
                "document_type": "fattura_elettronica",
                "content": fattura_xml,
                "mime_type": "application/xml",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-90-extract"}

        result = await step_90__fattura_parser(messages=[], ctx=ctx)

        # Should extract key fields
        assert result["parsing_completed"] is True
        parsed_doc = result["parsed_docs"][0]
        assert "extracted_fields" in parsed_doc
        fields = parsed_doc["extracted_fields"]
        assert fields.get("numero") == "123"
        assert fields.get("data") == "2024-06-15"
        assert fields.get("importo") == "5000.00"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_90_invalid_xml(self, mock_rag_log):
        """Test Step 90: Handle invalid XML gracefully."""
        from app.orchestrators.docs import step_90__fattura_parser

        classified_docs = [
            {
                "filename": "invalid.xml",
                "document_type": "fattura_elettronica",
                "content": b"<invalid>not valid fattura xml</invalid>",
                "mime_type": "application/xml",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-90-invalid"}

        result = await step_90__fattura_parser(messages=[], ctx=ctx)

        # Should handle error gracefully
        assert result["parsing_completed"] is True
        parsed_doc = result["parsed_docs"][0]
        assert parsed_doc["parsed_successfully"] is False
        assert "error" in parsed_doc

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_90_routes_to_extract_facts(self, mock_rag_log):
        """Test Step 90: Routes to Step 95 (ExtractDocFacts)."""
        from app.orchestrators.docs import step_90__fattura_parser

        fattura_xml = b'<?xml version="1.0"?><p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"></p:FatturaElettronica>'

        classified_docs = [
            {
                "filename": "fattura.xml",
                "document_type": "fattura_elettronica",
                "content": fattura_xml,
                "mime_type": "application/xml",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-90-route"}

        result = await step_90__fattura_parser(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result["next_step"] == "extract_doc_facts"  # Routes to Step 95


class TestRAGStep90Parity:
    """Parity tests proving Step 90 preserves existing Fattura parsing logic."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_90_parity_xml_namespace(self, mock_rag_log):
        """Test Step 90: Parity with Fattura XML namespace handling."""
        from app.orchestrators.docs import step_90__fattura_parser

        # Standard Fattura namespace from invoice_service.py
        fattura_xml = b"""<?xml version="1.0"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <FatturaElettronicaBody>
        <DatiGenerali>
            <DatiGeneraliDocumento>
                <Numero>100</Numero>
            </DatiGeneraliDocumento>
        </DatiGenerali>
    </FatturaElettronicaBody>
</p:FatturaElettronica>"""

        classified_docs = [
            {
                "filename": "fattura.xml",
                "document_type": "fattura_elettronica",
                "content": fattura_xml,
                "mime_type": "application/xml",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-parity"}

        result = await step_90__fattura_parser(messages=[], ctx=ctx)

        # Should handle namespace correctly
        assert result["parsing_completed"] is True
        assert result["parsed_docs"][0]["parsed_successfully"] is True


class TestRAGStep90Integration:
    """Integration tests for Step 89 → Step 90 → Step 95 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_89_to_90_integration(self, mock_rag_log):
        """Test Step 89 (route) → Step 90 (parse) integration."""
        from app.orchestrators.docs import step_89__doc_type, step_90__fattura_parser

        # Step 89: Route Fattura document
        classified_docs = [
            {
                "filename": "IT123_FPA.xml",
                "document_type": "fattura_elettronica",
                "content": b'<?xml version="1.0"?><p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"><FatturaElettronicaBody><DatiGenerali><DatiGeneraliDocumento><Numero>001</Numero></DatiGeneraliDocumento></DatiGenerali></FatturaElettronicaBody></p:FatturaElettronica>',
                "mime_type": "application/xml",
            }
        ]

        step_89_ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-integration-89-90"}

        step_89_result = await step_89__doc_type(messages=[], ctx=step_89_ctx)

        # Should route to fattura_parser
        assert step_89_result["routing_completed"] is True
        assert step_89_result["next_step"] == "fattura_parser"

        # Step 90: Parse Fattura XML
        step_90_ctx = {
            "classified_docs": step_89_result["classified_docs"],
            "document_count": step_89_result["document_count"],
            "request_id": step_89_result["request_id"],
        }

        step_90_result = await step_90__fattura_parser(messages=[], ctx=step_90_ctx)

        # Should parse successfully
        assert step_90_result["parsing_completed"] is True
        assert step_90_result["next_step"] == "extract_doc_facts"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_90_to_95_flow(self, mock_rag_log):
        """Test Step 90 → Step 95 (extract facts) flow."""
        from app.orchestrators.docs import step_90__fattura_parser

        fattura_xml = b'<?xml version="1.0"?><p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"><FatturaElettronicaBody><DatiGenerali><DatiGeneraliDocumento><Numero>999</Numero><ImportoTotaleDocumento>10000.00</ImportoTotaleDocumento></DatiGeneraliDocumento></DatiGenerali></FatturaElettronicaBody></p:FatturaElettronica>'

        classified_docs = [
            {
                "filename": "fattura_999.xml",
                "document_type": "fattura_elettronica",
                "content": fattura_xml,
                "mime_type": "application/xml",
            }
        ]

        ctx = {"classified_docs": classified_docs, "document_count": 1, "request_id": "test-90-to-95"}

        result = await step_90__fattura_parser(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result["next_step"] == "extract_doc_facts"
        assert result["parsing_completed"] is True

        # Context ready for Step 95
        assert "parsed_docs" in result
        assert len(result["parsed_docs"]) > 0
        assert result["parsed_docs"][0]["parsed_successfully"] is True
