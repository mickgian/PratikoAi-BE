"""
Tests for RAG STEP 96 — BlobStore.put Encrypted TTL storage (RAG.docs.blobstore.put.encrypted.ttl.storage)

This process step stores document blobs with encryption and TTL (time-to-live).
Ensures secure temporary storage of processed documents for provenance tracking.
"""

from unittest.mock import patch

import pytest


class TestRAGStep96StoreBlob:
    """Test suite for RAG STEP 96 - Blob storage with encryption and TTL."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_96_store_document_blob(self, mock_rag_log):
        """Test Step 96: Store document blob with encryption."""
        from app.orchestrators.docs import step_96__store_blob

        facts = [
            {
                'type': 'document_field',
                'field_name': 'numero',
                'value': '001',
                'document_type': 'fattura_elettronica',
                'source_file': 'fattura.xml'
            }
        ]

        parsed_docs = [
            {
                'filename': 'fattura.xml',
                'document_type': 'fattura_elettronica',
                'content': b'<?xml version="1.0"?><data>test</data>',
                'parsed_successfully': True
            }
        ]

        ctx = {
            'facts': facts,
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-96-store'
        }

        result = await step_96__store_blob(messages=[], ctx=ctx)

        # Should store successfully
        assert isinstance(result, dict)
        assert result['storage_completed'] is True
        assert result['document_count'] == 1
        assert 'blob_ids' in result
        assert len(result['blob_ids']) > 0
        assert result['request_id'] == 'test-96-store'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 96
        assert completed_log['node_label'] == 'StoreBlob'
        assert completed_log['storage_completed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_96_ttl_configuration(self, mock_rag_log):
        """Test Step 96: Verify TTL is configured for stored blobs."""
        from app.orchestrators.docs import step_96__store_blob

        facts = [{'type': 'test', 'value': 'data'}]
        parsed_docs = [
            {
                'filename': 'test.pdf',
                'document_type': 'generic',
                'content': b'test content',
                'parsed_successfully': True
            }
        ]

        ctx = {
            'facts': facts,
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-96-ttl'
        }

        result = await step_96__store_blob(messages=[], ctx=ctx)

        # Should include TTL metadata
        assert result['storage_completed'] is True
        assert 'ttl_seconds' in result
        assert result['ttl_seconds'] > 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_96_encryption_metadata(self, mock_rag_log):
        """Test Step 96: Verify encryption is applied."""
        from app.orchestrators.docs import step_96__store_blob

        facts = [{'type': 'sensitive', 'value': 'data'}]
        parsed_docs = [
            {
                'filename': 'sensitive.pdf',
                'document_type': 'contratto',
                'content': b'sensitive content',
                'parsed_successfully': True
            }
        ]

        ctx = {
            'facts': facts,
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-96-encrypt'
        }

        result = await step_96__store_blob(messages=[], ctx=ctx)

        # Should include encryption metadata
        assert result['storage_completed'] is True
        assert result.get('encrypted') is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_96_routes_to_provenance(self, mock_rag_log):
        """Test Step 96: Routes to Step 97 (Provenance)."""
        from app.orchestrators.docs import step_96__store_blob

        facts = [{'type': 'field', 'value': 'test'}]
        parsed_docs = [
            {
                'filename': 'doc.pdf',
                'document_type': 'generic',
                'content': b'content',
                'parsed_successfully': True
            }
        ]

        ctx = {
            'facts': facts,
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-96-route'
        }

        result = await step_96__store_blob(messages=[], ctx=ctx)

        # Should route to Step 97
        assert result['next_step'] == 'provenance'  # Routes to Step 97


class TestRAGStep96Parity:
    """Parity tests proving Step 96 preserves existing storage logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_96_parity_multiple_docs(self, mock_rag_log):
        """Test Step 96: Parity with multiple document storage."""
        from app.orchestrators.docs import step_96__store_blob

        facts = [
            {'type': 'field', 'value': 'data1'},
            {'type': 'field', 'value': 'data2'}
        ]
        parsed_docs = [
            {
                'filename': 'doc1.pdf',
                'document_type': 'generic',
                'content': b'content1',
                'parsed_successfully': True
            },
            {
                'filename': 'doc2.pdf',
                'document_type': 'generic',
                'content': b'content2',
                'parsed_successfully': True
            }
        ]

        ctx = {
            'facts': facts,
            'parsed_docs': parsed_docs,
            'document_count': 2,
            'request_id': 'test-parity'
        }

        result = await step_96__store_blob(messages=[], ctx=ctx)

        # Should handle multiple documents
        assert result['storage_completed'] is True
        assert result['document_count'] == 2
        assert len(result['blob_ids']) == 2


class TestRAGStep96Integration:
    """Integration tests for Step 95 → Step 96 → Step 97 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    @patch('app.orchestrators.facts.rag_step_log')
    async def test_step_95_to_96_integration(self, mock_facts_log, mock_docs_log):
        """Test Step 95 (extract) → Step 96 (store) integration."""
        from app.orchestrators.facts import step_95__extract_doc_facts
        from app.orchestrators.docs import step_96__store_blob

        # Step 95: Extract facts
        parsed_docs = [
            {
                'filename': 'fattura.xml',
                'document_type': 'fattura_elettronica',
                'content': b'<?xml version="1.0"?><data>test</data>',
                'parsed_successfully': True,
                'extracted_fields': {
                    'numero': '100',
                    'importo': '5000.00'
                }
            }
        ]

        step_95_ctx = {
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-integration-95-96'
        }

        step_95_result = await step_95__extract_doc_facts(messages=[], ctx=step_95_ctx)

        # Should extract successfully
        assert step_95_result['extraction_completed'] is True
        assert step_95_result['next_step'] == 'store_blob'

        # Step 96: Store blobs
        step_96_ctx = {
            'facts': step_95_result['facts'],
            'parsed_docs': parsed_docs,
            'document_count': step_95_result['document_count'],
            'request_id': step_95_result['request_id']
        }

        step_96_result = await step_96__store_blob(messages=[], ctx=step_96_ctx)

        # Should store successfully
        assert step_96_result['storage_completed'] is True
        assert step_96_result['next_step'] == 'provenance'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_96_to_97_flow(self, mock_rag_log):
        """Test Step 96 → Step 97 (provenance) flow."""
        from app.orchestrators.docs import step_96__store_blob

        facts = [
            {'type': 'document_field', 'field_name': 'importo', 'value': '1500000.00'}
        ]
        parsed_docs = [
            {
                'filename': 'contract.pdf',
                'document_type': 'contratto',
                'content': b'contract content',
                'parsed_successfully': True
            }
        ]

        ctx = {
            'facts': facts,
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-96-to-97'
        }

        result = await step_96__store_blob(messages=[], ctx=ctx)

        # Should route to Step 97
        assert result['next_step'] == 'provenance'
        assert result['storage_completed'] is True

        # Context ready for Step 97
        assert 'blob_ids' in result
        assert len(result['blob_ids']) > 0