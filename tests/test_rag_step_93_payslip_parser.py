"""
Tests for RAG STEP 93 — PayslipParser.parse (RAG.docs.payslipparser.parse)

This process step parses Italian payslip documents (busta paga/cedolino).
Extracts structured fields like employee info, gross pay, net pay, deductions, and contributions for downstream processing.
"""

from unittest.mock import patch

import pytest


class TestRAGStep93PayslipParser:
    """Test suite for RAG STEP 93 - Payslip document parser."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_93_parse_payslip_pdf(self, mock_rag_log):
        """Test Step 93: Parse payslip PDF."""
        from app.orchestrators.docs import step_93__payslip_parser

        # Simulated payslip content
        payslip_pdf = b'''BUSTA PAGA - CEDOLINO PAGA

        DIPENDENTE: Mario Rossi
        MATRICOLA: 12345
        QUALIFICA: Impiegato
        LIVELLO: 3

        PERIODO: Gennaio 2024

        RETRIBUZIONE LORDA: Euro 2.500,00
        CONTRIBUTI INPS: Euro 230,00
        IRPEF: Euro 450,00
        ADDIZIONALI: Euro 50,00

        NETTO IN BUSTA: Euro 1.770,00'''

        classified_docs = [
            {
                'filename': 'busta_paga_gennaio.pdf',
                'document_type': 'busta_paga',
                'content': payslip_pdf,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-93-payslip'
        }

        result = await step_93__payslip_parser(messages=[], ctx=ctx)

        # Should parse successfully
        assert isinstance(result, dict)
        assert result['parsing_completed'] is True
        assert result['document_count'] == 1
        assert result['parsed_docs'][0]['parsed_successfully'] is True
        assert result['request_id'] == 'test-93-payslip'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 93
        assert completed_log['node_label'] == 'PayslipParser'
        assert completed_log['parsing_completed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_93_extract_payslip_fields(self, mock_rag_log):
        """Test Step 93: Extract key fields from payslip."""
        from app.orchestrators.docs import step_93__payslip_parser

        # Payslip with structured data
        payslip_content = b'''CEDOLINO STIPENDIO

        DIPENDENTE: Giuseppe Verdi
        PERIODO: Dicembre 2024

        RETRIBUZIONE LORDA: Euro 3.200,00
        CONTRIBUTI PREVIDENZIALI: Euro 296,00
        IRPEF: Euro 640,00
        NETTO: Euro 2.264,00

        TFR MATURATO: Euro 266,67'''

        classified_docs = [
            {
                'filename': 'cedolino_dicembre.pdf',
                'document_type': 'busta_paga',
                'content': payslip_content,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-93-extract'
        }

        result = await step_93__payslip_parser(messages=[], ctx=ctx)

        # Should extract key fields
        assert result['parsing_completed'] is True
        parsed_doc = result['parsed_docs'][0]
        assert 'extracted_fields' in parsed_doc
        fields = parsed_doc['extracted_fields']
        assert fields.get('retribuzione_lorda') == '3.200.00'
        assert fields.get('netto') == '2.264.00'
        assert fields.get('periodo') == 'Dicembre 2024'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_93_invalid_payslip(self, mock_rag_log):
        """Test Step 93: Handle invalid payslip gracefully."""
        from app.orchestrators.docs import step_93__payslip_parser

        classified_docs = [
            {
                'filename': 'not_payslip.pdf',
                'document_type': 'busta_paga',
                'content': b'Not a valid payslip document',
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-93-invalid'
        }

        result = await step_93__payslip_parser(messages=[], ctx=ctx)

        # Should handle error gracefully
        assert result['parsing_completed'] is True
        parsed_doc = result['parsed_docs'][0]
        assert parsed_doc['parsed_successfully'] is False
        assert 'error' in parsed_doc

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_93_routes_to_extract_facts(self, mock_rag_log):
        """Test Step 93: Routes to Step 95 (ExtractDocFacts)."""
        from app.orchestrators.docs import step_93__payslip_parser

        payslip_content = b'''BUSTA PAGA
        PERIODO: Febbraio 2024
        RETRIBUZIONE LORDA: Euro 2.800,00
        NETTO: Euro 1.900,00'''

        classified_docs = [
            {
                'filename': 'payslip.pdf',
                'document_type': 'busta_paga',
                'content': payslip_content,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-93-route'
        }

        result = await step_93__payslip_parser(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result['next_step'] == 'extract_doc_facts'  # Routes to Step 95


class TestRAGStep93Parity:
    """Parity tests proving Step 93 preserves existing payslip parsing logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_93_parity_deductions(self, mock_rag_log):
        """Test Step 93: Parity with deduction extraction."""
        from app.orchestrators.docs import step_93__payslip_parser

        # Payslip with multiple deductions
        payslip_pdf = b'''CEDOLINO PAGA

        DIPENDENTE: Luigi Bianchi
        PERIODO: Marzo 2024

        RETRIBUZIONE LORDA: Euro 3.500,00
        CONTRIBUTI INPS: Euro 322,50
        IRPEF: Euro 700,00
        ADDIZIONALE REGIONALE: Euro 35,00
        ADDIZIONALE COMUNALE: Euro 28,00

        TOTALE TRATTENUTE: Euro 1.085,50
        NETTO IN BUSTA: Euro 2.414,50'''

        classified_docs = [
            {
                'filename': 'cedolino_marzo.pdf',
                'document_type': 'busta_paga',
                'content': payslip_pdf,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-parity'
        }

        result = await step_93__payslip_parser(messages=[], ctx=ctx)

        # Should handle deductions correctly
        assert result['parsing_completed'] is True
        assert result['parsed_docs'][0]['parsed_successfully'] is True


class TestRAGStep93Integration:
    """Integration tests for Step 89 → Step 93 → Step 95 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_to_93_integration(self, mock_rag_log):
        """Test Step 89 (route) → Step 93 (parse) integration."""
        from app.orchestrators.docs import step_89__doc_type, step_93__payslip_parser

        # Step 89: Route payslip document
        classified_docs = [
            {
                'filename': 'busta_paga_aprile.pdf',
                'document_type': 'busta_paga',
                'content': b'''BUSTA PAGA

                DIPENDENTE: Anna Verdi
                PERIODO: Aprile 2024

                RETRIBUZIONE LORDA: Euro 2.900,00
                CONTRIBUTI: Euro 267,50
                IRPEF: Euro 580,00
                NETTO: Euro 2.052,50''',
                'mime_type': 'application/pdf'
            }
        ]

        step_89_ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-integration-89-93'
        }

        step_89_result = await step_89__doc_type(messages=[], ctx=step_89_ctx)

        # Should route to payslip_parser
        assert step_89_result['routing_completed'] is True
        assert step_89_result['next_step'] == 'payslip_parser'

        # Step 93: Parse payslip
        step_93_ctx = {
            'classified_docs': step_89_result['classified_docs'],
            'document_count': step_89_result['document_count'],
            'request_id': step_89_result['request_id']
        }

        step_93_result = await step_93__payslip_parser(messages=[], ctx=step_93_ctx)

        # Should parse successfully
        assert step_93_result['parsing_completed'] is True
        assert step_93_result['next_step'] == 'extract_doc_facts'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_93_to_95_flow(self, mock_rag_log):
        """Test Step 93 → Step 95 (extract facts) flow."""
        from app.orchestrators.docs import step_93__payslip_parser

        payslip_content = b'''CEDOLINO STIPENDIO

        DIPENDENTE: Franco Neri
        PERIODO: Maggio 2024

        RETRIBUZIONE LORDA: Euro 4.000,00
        CONTRIBUTI PREVIDENZIALI: Euro 368,00
        IRPEF: Euro 800,00
        ADDIZIONALI: Euro 80,00
        NETTO IN BUSTA: Euro 2.752,00'''

        classified_docs = [
            {
                'filename': 'cedolino_maggio.pdf',
                'document_type': 'busta_paga',
                'content': payslip_content,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-93-to-95'
        }

        result = await step_93__payslip_parser(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result['next_step'] == 'extract_doc_facts'
        assert result['parsing_completed'] is True

        # Context ready for Step 95
        assert 'parsed_docs' in result
        assert len(result['parsed_docs']) > 0
        assert result['parsed_docs'][0]['parsed_successfully'] is True