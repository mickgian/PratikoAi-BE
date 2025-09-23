"""
Tests for RAG STEP 89 — Document type? (RAG.docs.document.type)

This decision step routes classified documents to appropriate parsers based on their type:
- Fattura XML → Step 90 (FatturaParser)
- F24 → Step 91 (F24Parser)
- Contratto → Step 92 (ContractParser)
- Busta paga → Step 93 (PayslipParser)
- Generic/Other → Step 94 (GenericOCR)
"""

from unittest.mock import patch

import pytest


class TestRAGStep89DocType:
    """Test suite for RAG STEP 89 - Document type decision routing."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_route_fattura_xml(self, mock_rag_log):
        """Test Step 89: Route Fattura XML to FatturaParser."""
        from app.orchestrators.docs import step_89__doc_type

        classified_docs = [
            {
                'filename': 'IT123_FPA.xml',
                'document_type': 'fattura_elettronica',
                'content': b'<?xml><FatturaElettronica>',
                'mime_type': 'application/xml'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-89-fattura'
        }

        result = await step_89__doc_type(messages=[], ctx=ctx)

        # Should route to Step 90 (FatturaParser)
        assert isinstance(result, dict)
        assert result['routing_completed'] is True
        assert result['document_count'] == 1
        assert result['next_step'] == 'fattura_parser'  # Routes to Step 90
        assert result['document_type'] == 'fattura_elettronica'
        assert result['request_id'] == 'test-89-fattura'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 89
        assert completed_log['node_label'] == 'DocType'
        assert completed_log['routing_completed'] is True
        assert completed_log['document_type'] == 'fattura_elettronica'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_route_f24(self, mock_rag_log):
        """Test Step 89: Route F24 to F24Parser."""
        from app.orchestrators.docs import step_89__doc_type

        classified_docs = [
            {
                'filename': 'F24_2024.pdf',
                'document_type': 'f24',
                'content': b'%PDF F24 content',
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-89-f24'
        }

        result = await step_89__doc_type(messages=[], ctx=ctx)

        # Should route to Step 91 (F24Parser)
        assert result['routing_completed'] is True
        assert result['next_step'] == 'f24_parser'  # Routes to Step 91
        assert result['document_type'] == 'f24'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_route_contratto(self, mock_rag_log):
        """Test Step 89: Route Contratto to ContractParser."""
        from app.orchestrators.docs import step_89__doc_type

        classified_docs = [
            {
                'filename': 'contratto_lavoro.pdf',
                'document_type': 'contratto',
                'content': b'%PDF Contratto content',
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-89-contratto'
        }

        result = await step_89__doc_type(messages=[], ctx=ctx)

        # Should route to Step 92 (ContractParser)
        assert result['routing_completed'] is True
        assert result['next_step'] == 'contract_parser'  # Routes to Step 92
        assert result['document_type'] == 'contratto'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_route_busta_paga(self, mock_rag_log):
        """Test Step 89: Route Busta Paga to PayslipParser."""
        from app.orchestrators.docs import step_89__doc_type

        classified_docs = [
            {
                'filename': 'busta_paga.pdf',
                'document_type': 'busta_paga',
                'content': b'%PDF Payslip content',
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-89-payslip'
        }

        result = await step_89__doc_type(messages=[], ctx=ctx)

        # Should route to Step 93 (PayslipParser)
        assert result['routing_completed'] is True
        assert result['next_step'] == 'payslip_parser'  # Routes to Step 93
        assert result['document_type'] == 'busta_paga'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_route_generic(self, mock_rag_log):
        """Test Step 89: Route generic document to GenericOCR."""
        from app.orchestrators.docs import step_89__doc_type

        classified_docs = [
            {
                'filename': 'report.pdf',
                'document_type': 'generic',
                'content': b'%PDF Generic content',
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 1,
            'request_id': 'test-89-generic'
        }

        result = await step_89__doc_type(messages=[], ctx=ctx)

        # Should route to Step 94 (GenericOCR)
        assert result['routing_completed'] is True
        assert result['next_step'] == 'generic_ocr'  # Routes to Step 94
        assert result['document_type'] == 'generic'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_first_document_routing(self, mock_rag_log):
        """Test Step 89: Route based on first document when multiple present."""
        from app.orchestrators.docs import step_89__doc_type

        classified_docs = [
            {
                'filename': 'fattura.xml',
                'document_type': 'fattura_elettronica',
                'content': b'<?xml><FatturaElettronica>',
                'mime_type': 'application/xml'
            },
            {
                'filename': 'other.pdf',
                'document_type': 'generic',
                'content': b'%PDF content',
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'classified_docs': classified_docs,
            'document_count': 2,
            'request_id': 'test-89-first'
        }

        result = await step_89__doc_type(messages=[], ctx=ctx)

        # Should route based on first document
        assert result['routing_completed'] is True
        assert result['next_step'] == 'fattura_parser'
        assert result['document_type'] == 'fattura_elettronica'


class TestRAGStep89Parity:
    """Parity tests proving Step 89 preserves existing routing logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_parity_routing_map(self, mock_rag_log):
        """Test Step 89: Parity with expected routing map."""
        from app.orchestrators.docs import step_89__doc_type

        # All document types and their expected routes
        routing_map = [
            ('fattura_elettronica', 'fattura_parser'),
            ('f24', 'f24_parser'),
            ('contratto', 'contract_parser'),
            ('busta_paga', 'payslip_parser'),
            ('generic', 'generic_ocr'),
            ('unknown', 'generic_ocr'),  # Unknown types default to generic
        ]

        for doc_type, expected_route in routing_map:
            classified_docs = [
                {
                    'filename': f'test_{doc_type}.pdf',
                    'document_type': doc_type,
                    'content': b'test content',
                    'mime_type': 'application/pdf'
                }
            ]

            ctx = {
                'classified_docs': classified_docs,
                'document_count': 1,
                'request_id': f'test-parity-{doc_type}'
            }

            result = await step_89__doc_type(messages=[], ctx=ctx)

            assert result['next_step'] == expected_route, \
                f"Failed for document_type={doc_type}, expected {expected_route}, got {result['next_step']}"


class TestRAGStep89Integration:
    """Integration tests for Step 88 → Step 89 → Step 90/91/92/93/94 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_88_to_89_integration(self, mock_rag_log):
        """Test Step 88 (classify) → Step 89 (route) integration."""
        from app.orchestrators.docs import step_88__doc_classify, step_89__doc_type

        # Step 88: Classify document
        sanitized_docs = [
            {
                'filename': 'IT123_FPA.xml',
                'content': b'<?xml version="1.0"?><FatturaElettronica xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">',
                'mime_type': 'application/xml',
                'detected_type': 'xml',
                'potential_category': 'fattura_elettronica',
                'is_safe': True
            }
        ]

        step_88_ctx = {
            'sanitized_docs': sanitized_docs,
            'document_count': 1,
            'request_id': 'test-integration-88-89'
        }

        step_88_result = await step_88__doc_classify(messages=[], ctx=step_88_ctx)

        # Should classify and route to decision
        assert step_88_result['classification_completed'] is True
        assert step_88_result['next_step'] == 'doc_type_decision'

        # Step 89: Route based on classification
        step_89_ctx = {
            'classified_docs': step_88_result['classified_docs'],
            'document_count': step_88_result['document_count'],
            'request_id': step_88_result['request_id']
        }

        step_89_result = await step_89__doc_type(messages=[], ctx=step_89_ctx)

        # Should route to appropriate parser
        assert step_89_result['routing_completed'] is True
        assert step_89_result['next_step'] == 'fattura_parser'  # Routes to Step 90
        assert step_89_result['document_type'] == 'fattura_elettronica'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_89_routing_decision_paths(self, mock_rag_log):
        """Test Step 89: All routing decision paths."""
        from app.orchestrators.docs import step_89__doc_type

        # Test all 5 routing paths
        test_cases = [
            ('fattura_elettronica', 'fattura_parser', 90),
            ('f24', 'f24_parser', 91),
            ('contratto', 'contract_parser', 92),
            ('busta_paga', 'payslip_parser', 93),
            ('generic', 'generic_ocr', 94)
        ]

        for doc_type, expected_next, expected_step in test_cases:
            classified_docs = [
                {
                    'filename': f'{doc_type}.pdf',
                    'document_type': doc_type,
                    'content': b'content',
                    'mime_type': 'application/pdf'
                }
            ]

            ctx = {
                'classified_docs': classified_docs,
                'document_count': 1,
                'request_id': f'test-route-{doc_type}'
            }

            result = await step_89__doc_type(messages=[], ctx=ctx)

            # Verify routing
            assert result['next_step'] == expected_next, \
                f"Failed for {doc_type}: expected {expected_next}, got {result['next_step']}"
            assert result['document_type'] == doc_type