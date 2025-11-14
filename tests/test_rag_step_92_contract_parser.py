"""
Tests for RAG STEP 92 — ContractParser.parse (RAG.docs.contractparser.parse)

This process step parses Italian contract documents (contratto).
Extracts structured fields like parties, object, price, duration, and key clauses for downstream processing.
"""

from unittest.mock import patch

import pytest


class TestRAGStep92ContractParser:
    """Test suite for RAG STEP 92 - Contract document parser."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_92_parse_contract_pdf(self, mock_rag_log):
        """Test Step 92: Parse contract PDF."""
        from app.orchestrators.docs import step_92__contract_parser

        # Simulated contract content
        contract_pdf = b'''CONTRATTO DI LOCAZIONE

        Tra le parti:
        LOCATORE: Mario Rossi, CF: RSSMRA80A01H501U
        LOCATARIO: Giuseppe Verdi, CF: VRDGSP85B02F205Z

        OGGETTO: Immobile sito in Via Roma 123, Milano
        CANONE: Euro 1.200,00 mensili
        DURATA: 4+4 anni
        DECORRENZA: 01/01/2024

        Clausole particolari:
        - Divieto di sublocazione
        - Oneri condominiali a carico del conduttore'''

        classified_docs = [
            {
                'filename': 'contratto_locazione.pdf',
                'document_type': 'contratto',
                'content': contract_pdf,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-92-contract'
        }

        result = await step_92__contract_parser(messages=[], ctx=ctx)

        # Should parse successfully
        assert isinstance(result, dict)
        assert result['parsing_completed'] is True
        assert result['document_count'] == 1
        assert result['parsed_docs'][0]['parsed_successfully'] is True
        assert result['request_id'] == 'test-92-contract'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 92
        assert completed_log['node_label'] == 'ContractParser'
        assert completed_log['parsing_completed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_92_extract_contract_fields(self, mock_rag_log):
        """Test Step 92: Extract key fields from contract."""
        from app.orchestrators.docs import step_92__contract_parser

        # Contract with structured data
        contract_content = b'''CONTRATTO DI PRESTAZIONE SERVIZI

        COMMITTENTE: Acme S.p.A., P.IVA 12345678901
        PRESTATORE: Studio Legale Bianchi

        OGGETTO: Servizi di consulenza legale
        CORRISPETTIVO: Euro 5.000,00
        DURATA: 12 mesi
        DECORRENZA: 15/03/2024

        TIPO CONTRATTO: prestazione_servizi'''

        classified_docs = [
            {
                'filename': 'contratto_servizi.pdf',
                'document_type': 'contratto',
                'content': contract_content,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-92-extract'
        }

        result = await step_92__contract_parser(messages=[], ctx=ctx)

        # Should extract key fields
        assert result['parsing_completed'] is True
        parsed_doc = result['parsed_docs'][0]
        assert 'extracted_fields' in parsed_doc
        fields = parsed_doc['extracted_fields']
        assert fields.get('tipo_contratto') == 'prestazione_servizi'
        assert fields.get('corrispettivo') == '5.000.00'
        assert fields.get('durata') == '12 mesi'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_92_invalid_contract(self, mock_rag_log):
        """Test Step 92: Handle invalid contract gracefully."""
        from app.orchestrators.docs import step_92__contract_parser

        classified_docs = [
            {
                'filename': 'not_contract.pdf',
                'document_type': 'contratto',
                'content': b'Not a valid contract document',
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-92-invalid'
        }

        result = await step_92__contract_parser(messages=[], ctx=ctx)

        # Should handle error gracefully
        assert result['parsing_completed'] is True
        parsed_doc = result['parsed_docs'][0]
        assert parsed_doc['parsed_successfully'] is False
        assert 'error' in parsed_doc

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_92_routes_to_extract_facts(self, mock_rag_log):
        """Test Step 92: Routes to Step 95 (ExtractDocFacts)."""
        from app.orchestrators.docs import step_92__contract_parser

        contract_content = b'''CONTRATTO
        TIPO: locazione
        OGGETTO: Immobile
        CANONE: Euro 800,00'''

        classified_docs = [
            {
                'filename': 'contratto.pdf',
                'document_type': 'contratto',
                'content': contract_content,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-92-route'
        }

        result = await step_92__contract_parser(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result['next_step'] == 'extract_doc_facts'  # Routes to Step 95


class TestRAGStep92Parity:
    """Parity tests proving Step 92 preserves existing contract parsing logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_92_parity_contract_types(self, mock_rag_log):
        """Test Step 92: Parity with contract type detection."""
        from app.orchestrators.docs import step_92__contract_parser

        # Contract with multiple type indicators
        contract_pdf = b'''CONTRATTO DI COMPRAVENDITA

        VENDITORE: Mario Rossi
        ACQUIRENTE: Luigi Bianchi

        OGGETTO: Appartamento Via Dante 45
        PREZZO: Euro 250.000,00'''

        classified_docs = [
            {
                'filename': 'contratto_vendita.pdf',
                'document_type': 'contratto',
                'content': contract_pdf,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-parity'
        }

        result = await step_92__contract_parser(messages=[], ctx=ctx)

        # Should handle contract type correctly
        assert result['parsing_completed'] is True
        assert result['parsed_docs'][0]['parsed_successfully'] is True


class TestRAGStep92Integration:
    """Integration tests for Step 89 → Step 92 → Step 95 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_to_92_integration(self, mock_rag_log):
        """Test Step 89 (route) → Step 92 (parse) integration."""
        from app.orchestrators.docs import step_89__doc_type, step_92__contract_parser

        # Step 89: Route contract document
        classified_docs = [
            {
                'filename': 'contratto_lavoro.pdf',
                'document_type': 'contratto',
                'content': b'''CONTRATTO DI LAVORO SUBORDINATO

                DATORE: Azienda XYZ S.r.l.
                LAVORATORE: Paolo Verdi

                OGGETTO: Assunzione a tempo indeterminato
                RETRIBUZIONE: Euro 2.500,00 mensili
                DECORRENZA: 01/04/2024''',
                'mime_type': 'application/pdf'
            }
        ]

        step_89_ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-integration-89-92'
        }

        step_89_result = await step_89__doc_type(messages=[], ctx=step_89_ctx)

        # Should route to contract_parser
        assert step_89_result['routing_completed'] is True
        assert step_89_result['next_step'] == 'contract_parser'

        # Step 92: Parse contract
        step_92_ctx = {
            'classified_docs': step_89_result['classified_docs'],
            'document_count': step_89_result['document_count'],
            'request_id': step_89_result['request_id']
        }

        step_92_result = await step_92__contract_parser(messages=[], ctx=step_92_ctx)

        # Should parse successfully
        assert step_92_result['parsing_completed'] is True
        assert step_92_result['next_step'] == 'extract_doc_facts'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_92_to_95_flow(self, mock_rag_log):
        """Test Step 92 → Step 95 (extract facts) flow."""
        from app.orchestrators.docs import step_92__contract_parser

        contract_content = b'''CONTRATTO DI APPALTO

        COMMITTENTE: Comune di Milano
        APPALTATORE: Impresa Costruzioni ABC

        OGGETTO: Realizzazione opera pubblica
        IMPORTO: Euro 1.500.000,00
        DURATA: 18 mesi
        DECORRENZA: 01/05/2024'''

        classified_docs = [
            {
                'filename': 'contratto_appalto.pdf',
                'document_type': 'contratto',
                'content': contract_content,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-92-to-95'
        }

        result = await step_92__contract_parser(messages=[], ctx=ctx)

        # Should route to Step 95
        assert result['next_step'] == 'extract_doc_facts'
        assert result['parsing_completed'] is True

        # Context ready for Step 95
        assert 'parsed_docs' in result
        assert len(result['parsed_docs']) > 0
        assert result['parsed_docs'][0]['parsed_successfully'] is True