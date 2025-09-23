"""
Tests for RAG STEP 95 — Extractor.extract Structured fields (RAG.facts.extractor.extract.structured.fields)

This process step extracts structured facts from parsed documents.
Converts document-specific fields into normalized atomic facts for downstream processing.
"""

from unittest.mock import patch

import pytest


class TestRAGStep95ExtractDocFacts:
    """Test suite for RAG STEP 95 - Document facts extraction."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    async def test_step_95_extract_from_fattura(self, mock_rag_log):
        """Test Step 95: Extract facts from Fattura document."""
        from app.orchestrators.facts import step_95__extract_doc_facts

        parsed_docs = [
            {
                'filename': 'fattura.xml',
                'document_type': 'fattura_elettronica',
                'parsed_successfully': True,
                'extracted_fields': {
                    'numero': '001',
                    'data': '2024-01-15',
                    'importo': '1220.00',
                    'tipo_documento': 'TD01'
                }
            }
        ]

        ctx = {
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-95-fattura'
        }

        result = await step_95__extract_doc_facts(messages=[], ctx=ctx)

        # Should extract facts successfully
        assert isinstance(result, dict)
        assert result['extraction_completed'] is True
        assert result['document_count'] == 1
        assert 'facts' in result
        assert len(result['facts']) > 0
        assert result['request_id'] == 'test-95-fattura'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 95
        assert completed_log['node_label'] == 'ExtractDocFacts'
        assert completed_log['extraction_completed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    async def test_step_95_extract_from_f24(self, mock_rag_log):
        """Test Step 95: Extract facts from F24 document."""
        from app.orchestrators.facts import step_95__extract_doc_facts

        parsed_docs = [
            {
                'filename': 'f24.pdf',
                'document_type': 'f24',
                'parsed_successfully': True,
                'extracted_fields': {
                    'codice_tributo': '1040',
                    'importo': '2500.00',
                    'anno': '2024',
                    'periodo': '03/2024'
                }
            }
        ]

        ctx = {
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-95-f24'
        }

        result = await step_95__extract_doc_facts(messages=[], ctx=ctx)

        # Should extract facts
        assert result['extraction_completed'] is True
        assert 'facts' in result
        facts = result['facts']
        assert any('codice_tributo' in str(f) for f in facts)
        assert any('2500.00' in str(f) for f in facts)

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    async def test_step_95_extract_from_contract(self, mock_rag_log):
        """Test Step 95: Extract facts from contract document."""
        from app.orchestrators.facts import step_95__extract_doc_facts

        parsed_docs = [
            {
                'filename': 'contratto.pdf',
                'document_type': 'contratto',
                'parsed_successfully': True,
                'extracted_fields': {
                    'tipo_contratto': 'locazione',
                    'corrispettivo': '1.200.00',
                    'durata': '4+4 anni',
                    'decorrenza': '01/01/2024'
                }
            }
        ]

        ctx = {
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-95-contract'
        }

        result = await step_95__extract_doc_facts(messages=[], ctx=ctx)

        # Should extract facts
        assert result['extraction_completed'] is True
        assert 'facts' in result
        facts = result['facts']
        assert any('locazione' in str(f) for f in facts)

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    async def test_step_95_extract_from_payslip(self, mock_rag_log):
        """Test Step 95: Extract facts from payslip document."""
        from app.orchestrators.facts import step_95__extract_doc_facts

        parsed_docs = [
            {
                'filename': 'busta_paga.pdf',
                'document_type': 'busta_paga',
                'parsed_successfully': True,
                'extracted_fields': {
                    'dipendente': 'Mario Rossi',
                    'periodo': 'Gennaio 2024',
                    'retribuzione_lorda': '2.500.00',
                    'netto': '1.770.00'
                }
            }
        ]

        ctx = {
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-95-payslip'
        }

        result = await step_95__extract_doc_facts(messages=[], ctx=ctx)

        # Should extract facts
        assert result['extraction_completed'] is True
        assert 'facts' in result
        facts = result['facts']
        assert any('2.500.00' in str(f) for f in facts)

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    async def test_step_95_routes_to_store_blob(self, mock_rag_log):
        """Test Step 95: Routes to Step 96 (StoreBlob)."""
        from app.orchestrators.facts import step_95__extract_doc_facts

        parsed_docs = [
            {
                'filename': 'doc.pdf',
                'document_type': 'generic',
                'parsed_successfully': True,
                'extracted_text': 'Document content'
            }
        ]

        ctx = {
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-95-route'
        }

        result = await step_95__extract_doc_facts(messages=[], ctx=ctx)

        # Should route to Step 96
        assert result['next_step'] == 'store_blob'  # Routes to Step 96


class TestRAGStep95Parity:
    """Parity tests proving Step 95 preserves existing extraction logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    async def test_step_95_parity_multiple_docs(self, mock_rag_log):
        """Test Step 95: Parity with multiple document extraction."""
        from app.orchestrators.facts import step_95__extract_doc_facts

        parsed_docs = [
            {
                'filename': 'fattura1.xml',
                'document_type': 'fattura_elettronica',
                'parsed_successfully': True,
                'extracted_fields': {'numero': '001', 'importo': '1000.00'}
            },
            {
                'filename': 'fattura2.xml',
                'document_type': 'fattura_elettronica',
                'parsed_successfully': True,
                'extracted_fields': {'numero': '002', 'importo': '2000.00'}
            }
        ]

        ctx = {
            'parsed_docs': parsed_docs,
            'document_count': 2,
            'request_id': 'test-parity'
        }

        result = await step_95__extract_doc_facts(messages=[], ctx=ctx)

        # Should handle multiple documents
        assert result['extraction_completed'] is True
        assert result['document_count'] == 2


class TestRAGStep95Integration:
    """Integration tests for Step 90-94 → Step 95 → Step 96 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    async def test_step_90_to_95_integration(self, mock_rag_log):
        """Test Step 90 (Fattura) → Step 95 (extract) integration."""
        from app.orchestrators.docs import step_90__fattura_parser
        from app.orchestrators.facts import step_95__extract_doc_facts

        # Step 90: Parse Fattura
        classified_docs = [
            {
                'filename': 'fattura.xml',
                'document_type': 'fattura_elettronica',
                'content': b'<?xml version="1.0"?><p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"><FatturaElettronicaBody><DatiGenerali><DatiGeneraliDocumento><Numero>100</Numero><ImportoTotaleDocumento>5000.00</ImportoTotaleDocumento></DatiGeneraliDocumento></DatiGenerali></FatturaElettronicaBody></p:FatturaElettronica>',
                'mime_type': 'application/xml'
            }
        ]

        step_90_ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-integration-90-95'
        }

        step_90_result = await step_90__fattura_parser(messages=[], ctx=step_90_ctx)

        # Should parse successfully
        assert step_90_result['parsing_completed'] is True
        assert step_90_result['next_step'] == 'extract_doc_facts'

        # Step 95: Extract facts
        step_95_ctx = {
            'parsed_docs': step_90_result['parsed_docs'],
            'document_count': step_90_result['document_count'],
            'request_id': step_90_result['request_id']
        }

        step_95_result = await step_95__extract_doc_facts(messages=[], ctx=step_95_ctx)

        # Should extract successfully
        assert step_95_result['extraction_completed'] is True
        assert step_95_result['next_step'] == 'store_blob'

    @pytest.mark.asyncio
    @patch('app.orchestrators.facts.rag_step_log')
    async def test_step_95_to_96_flow(self, mock_rag_log):
        """Test Step 95 → Step 96 (store blob) flow."""
        from app.orchestrators.facts import step_95__extract_doc_facts

        parsed_docs = [
            {
                'filename': 'contract.pdf',
                'document_type': 'contratto',
                'parsed_successfully': True,
                'extracted_fields': {
                    'tipo_contratto': 'appalto',
                    'corrispettivo': '1.500.000.00'
                }
            }
        ]

        ctx = {
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-95-to-96'
        }

        result = await step_95__extract_doc_facts(messages=[], ctx=ctx)

        # Should route to Step 96
        assert result['next_step'] == 'store_blob'
        assert result['extraction_completed'] is True

        # Context ready for Step 96
        assert 'facts' in result
        assert len(result['facts']) > 0