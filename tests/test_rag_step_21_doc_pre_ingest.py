"""
Tests for RAG STEP 21 — DocPreIngest.quick_extract type sniff and key fields (RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields)

This process step performs quick document type detection and key field extraction
based on MIME type and basic metadata analysis.
"""

from unittest.mock import patch

import pytest


class TestRAGStep21DocPreIngest:
    """Test suite for RAG STEP 21 - Document pre-ingest quick extract."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_21_pdf_document(self, mock_rag_log):
        """Test Step 21: Quick extract from PDF document."""
        from app.orchestrators.preflight import step_21__doc_pre_ingest

        fingerprints = [
            {
                'hash': 'abc123',
                'filename': 'fattura_2024.pdf',
                'size': 2 * 1024 * 1024,
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-21-pdf'
        }

        result = await step_21__doc_pre_ingest(messages=[], ctx=ctx)

        # Verify extraction
        assert isinstance(result, dict)
        assert result['extraction_completed'] is True
        assert result['document_count'] == 1
        assert len(result['extracted_docs']) == 1

        doc = result['extracted_docs'][0]
        assert doc['detected_type'] == 'pdf'
        assert doc['filename'] == 'fattura_2024.pdf'
        assert doc['mime_type'] == 'application/pdf'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 21
        assert completed_log['node_label'] == 'QuickPreIngest'
        assert completed_log['extraction_completed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_21_excel_document(self, mock_rag_log):
        """Test Step 21: Quick extract from Excel document."""
        from app.orchestrators.preflight import step_21__doc_pre_ingest

        fingerprints = [
            {
                'hash': 'xlsx123',
                'filename': 'bilancio_2024.xlsx',
                'size': 3 * 1024 * 1024,
                'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-21-excel'
        }

        result = await step_21__doc_pre_ingest(messages=[], ctx=ctx)

        doc = result['extracted_docs'][0]
        assert doc['detected_type'] == 'xlsx'
        assert 'bilancio' in doc['filename']

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_21_xml_fattura(self, mock_rag_log):
        """Test Step 21: Detect XML fattura elettronica."""
        from app.orchestrators.preflight import step_21__doc_pre_ingest

        fingerprints = [
            {
                'hash': 'xml123',
                'filename': 'IT12345678901_FPA01.xml',
                'size': 512 * 1024,
                'mime_type': 'application/xml'
            }
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-21-xml'
        }

        result = await step_21__doc_pre_ingest(messages=[], ctx=ctx)

        doc = result['extracted_docs'][0]
        assert doc['detected_type'] == 'xml'
        # Should detect potential fattura from filename pattern
        assert 'potential_category' in doc

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_21_multiple_documents(self, mock_rag_log):
        """Test Step 21: Extract from multiple documents."""
        from app.orchestrators.preflight import step_21__doc_pre_ingest

        fingerprints = [
            {'hash': 'p1', 'filename': 'doc1.pdf', 'size': 1024, 'mime_type': 'application/pdf'},
            {'hash': 'x1', 'filename': 'sheet.xlsx', 'size': 2048, 'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
            {'hash': 'c1', 'filename': 'data.csv', 'size': 512, 'mime_type': 'text/csv'}
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 3,
            'request_id': 'test-21-multi'
        }

        result = await step_21__doc_pre_ingest(messages=[], ctx=ctx)

        assert result['extraction_completed'] is True
        assert result['document_count'] == 3
        assert len(result['extracted_docs']) == 3

        types = [doc['detected_type'] for doc in result['extracted_docs']]
        assert 'pdf' in types
        assert 'xlsx' in types
        assert 'csv' in types

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_21_key_field_hints(self, mock_rag_log):
        """Test Step 21: Extract key field hints from filename."""
        from app.orchestrators.preflight import step_21__doc_pre_ingest

        test_cases = [
            ('fattura_2024_01.pdf', 'fattura'),
            ('F24_pagamento.pdf', 'f24'),
            ('contratto_lavoro.pdf', 'contratto'),
            ('busta_paga_gennaio.pdf', 'busta_paga')
        ]

        for filename, expected_hint in test_cases:
            mock_rag_log.reset_mock()

            fingerprints = [
                {'hash': 'test', 'filename': filename, 'size': 1024, 'mime_type': 'application/pdf'}
            ]

            ctx = {
                'fingerprints': fingerprints,
                'attachment_count': 1,
                'request_id': f'test-21-hint-{expected_hint}'
            }

            result = await step_21__doc_pre_ingest(messages=[], ctx=ctx)

            doc = result['extracted_docs'][0]
            assert doc['filename'] == filename

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_21_routes_to_step_22(self, mock_rag_log):
        """Test Step 21: Routes to Step 22 (doc-dependent check)."""
        from app.orchestrators.preflight import step_21__doc_pre_ingest

        fingerprints = [
            {'hash': 'test', 'filename': 'test.pdf', 'size': 1024, 'mime_type': 'application/pdf'}
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-21-route'
        }

        result = await step_21__doc_pre_ingest(messages=[], ctx=ctx)

        # Should route to Step 22
        assert result['next_step'] == 'doc_dependent_check'


class TestRAGStep21Parity:
    """Parity tests proving Step 21 preserves existing logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_21_parity_mime_type_detection(self, mock_rag_log):
        """Test Step 21: Parity with DOCUMENT_CONFIG MIME types."""
        from app.orchestrators.preflight import step_21__doc_pre_ingest
        from app.models.document_simple import DOCUMENT_CONFIG

        for mime_type, doc_type in DOCUMENT_CONFIG['SUPPORTED_MIME_TYPES'].items():
            mock_rag_log.reset_mock()

            fingerprints = [
                {'hash': 'test', 'filename': f'test.{doc_type.value}', 'size': 1024, 'mime_type': mime_type}
            ]

            ctx = {
                'fingerprints': fingerprints,
                'attachment_count': 1,
                'request_id': f'test-parity-{doc_type.value}'
            }

            result = await step_21__doc_pre_ingest(messages=[], ctx=ctx)

            # Should detect type from MIME
            assert result['extraction_completed'] is True
            doc = result['extracted_docs'][0]
            assert doc['mime_type'] == mime_type


class TestRAGStep21Integration:
    """Integration tests for Step 85 → Step 21 → Step 22 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_to_21_integration(self, mock_rag_log):
        """Test Step 85 (valid) → Step 21 (extract) integration."""
        from app.orchestrators.preflight import step_85__valid_attachments_check, step_21__doc_pre_ingest

        # Step 85: Valid attachments
        step_85_ctx = {
            'validation_passed': True,
            'errors': [],
            'attachment_count': 1,
            'fingerprints': [
                {'hash': 'abc', 'filename': 'invoice.pdf', 'size': 1024, 'mime_type': 'application/pdf'}
            ],
            'request_id': 'test-integration-85-21'
        }

        step_85_result = await step_85__valid_attachments_check(messages=[], ctx=step_85_ctx)

        # Should route to doc_pre_ingest
        assert step_85_result['attachments_valid'] is True
        assert step_85_result['next_step'] == 'doc_pre_ingest'

        # Step 21: Extract document info
        step_21_ctx = {
            'fingerprints': step_85_ctx['fingerprints'],
            'attachment_count': step_85_result['attachment_count'],
            'request_id': step_85_result['request_id']
        }

        step_21_result = await step_21__doc_pre_ingest(messages=[], ctx=step_21_ctx)

        # Should extract successfully
        assert step_21_result['extraction_completed'] is True
        assert step_21_result['next_step'] == 'doc_dependent_check'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_21_prepares_for_step_22(self, mock_rag_log):
        """Test Step 21: Prepares extracted docs for Step 22 decision."""
        from app.orchestrators.preflight import step_21__doc_pre_ingest

        fingerprints = [
            {'hash': 'doc1', 'filename': 'contract.pdf', 'size': 2048, 'mime_type': 'application/pdf'}
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-21-prep-22'
        }

        result = await step_21__doc_pre_ingest(messages=[], ctx=ctx)

        # Should provide extracted_docs for Step 22
        assert 'extracted_docs' in result
        assert result['document_count'] > 0
        assert result['next_step'] == 'doc_dependent_check'