"""
Tests for RAG STEP 97 — Provenance.log Ledger entry (RAG.docs.provenance.log.ledger.entry)

This process step logs provenance information to create an immutable audit trail.
Records document processing lineage for compliance and traceability.
"""

from unittest.mock import patch

import pytest


class TestRAGStep97Provenance:
    """Test suite for RAG STEP 97 - Provenance ledger logging."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_97_log_provenance_entry(self, mock_rag_log):
        """Test Step 97: Log provenance ledger entry."""
        from app.orchestrators.docs import step_97__provenance

        blob_ids = [
            {
                'blob_id': 'abc123',
                'filename': 'fattura.xml',
                'document_type': 'fattura_elettronica',
                'size': 1024
            }
        ]

        facts = [
            {
                'type': 'document_field',
                'field_name': 'numero',
                'value': '001',
                'source_file': 'fattura.xml'
            }
        ]

        ctx = {
            'blob_ids': blob_ids,
            'facts': facts,
            'document_count': 1,
            'request_id': 'test-97-provenance'
        }

        result = await step_97__provenance(messages=[], ctx=ctx)

        # Should log provenance successfully
        assert isinstance(result, dict)
        assert result['provenance_logged'] is True
        assert result['document_count'] == 1
        assert 'ledger_entries' in result
        assert len(result['ledger_entries']) > 0
        assert result['request_id'] == 'test-97-provenance'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 97
        assert completed_log['node_label'] == 'Provenance'
        assert completed_log['provenance_logged'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_97_ledger_metadata(self, mock_rag_log):
        """Test Step 97: Verify ledger entry metadata."""
        from app.orchestrators.docs import step_97__provenance

        blob_ids = [
            {
                'blob_id': 'def456',
                'filename': 'contract.pdf',
                'document_type': 'contratto'
            }
        ]

        facts = [{'type': 'test', 'value': 'data'}]

        ctx = {
            'blob_ids': blob_ids,
            'facts': facts,
            'document_count': 1,
            'request_id': 'test-97-metadata'
        }

        result = await step_97__provenance(messages=[], ctx=ctx)

        # Should include ledger metadata
        assert result['provenance_logged'] is True
        ledger_entry = result['ledger_entries'][0]
        assert 'timestamp' in ledger_entry
        assert 'request_id' in ledger_entry
        assert 'blob_id' in ledger_entry
        assert 'document_type' in ledger_entry

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_97_immutable_ledger(self, mock_rag_log):
        """Test Step 97: Verify immutable ledger characteristics."""
        from app.orchestrators.docs import step_97__provenance

        blob_ids = [{'blob_id': 'ghi789', 'filename': 'doc.pdf'}]
        facts = [{'type': 'field', 'value': 'test'}]

        ctx = {
            'blob_ids': blob_ids,
            'facts': facts,
            'document_count': 1,
            'request_id': 'test-97-immutable'
        }

        result = await step_97__provenance(messages=[], ctx=ctx)

        # Should have immutable ledger properties
        assert result['provenance_logged'] is True
        assert result.get('immutable') is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_97_routes_to_tool_results(self, mock_rag_log):
        """Test Step 97: Routes to Step 98 (ToToolResults)."""
        from app.orchestrators.docs import step_97__provenance

        blob_ids = [{'blob_id': 'jkl012', 'filename': 'test.pdf'}]
        facts = [{'type': 'test', 'value': 'data'}]

        ctx = {
            'blob_ids': blob_ids,
            'facts': facts,
            'document_count': 1,
            'request_id': 'test-97-route'
        }

        result = await step_97__provenance(messages=[], ctx=ctx)

        # Should route to Step 98
        assert result['next_step'] == 'to_tool_results'  # Routes to Step 98


class TestRAGStep97Parity:
    """Parity tests proving Step 97 preserves existing provenance logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_97_parity_multiple_docs(self, mock_rag_log):
        """Test Step 97: Parity with multiple document provenance."""
        from app.orchestrators.docs import step_97__provenance

        blob_ids = [
            {'blob_id': 'abc1', 'filename': 'doc1.pdf'},
            {'blob_id': 'abc2', 'filename': 'doc2.pdf'}
        ]
        facts = [
            {'type': 'field', 'value': 'data1'},
            {'type': 'field', 'value': 'data2'}
        ]

        ctx = {
            'blob_ids': blob_ids,
            'facts': facts,
            'document_count': 2,
            'request_id': 'test-parity'
        }

        result = await step_97__provenance(messages=[], ctx=ctx)

        # Should handle multiple documents
        assert result['provenance_logged'] is True
        assert result['document_count'] == 2
        assert len(result['ledger_entries']) == 2


class TestRAGStep97Integration:
    """Integration tests for Step 96 → Step 97 → Step 98 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_96_to_97_integration(self, mock_rag_log):
        """Test Step 96 (store) → Step 97 (provenance) integration."""
        from app.orchestrators.docs import step_96__store_blob, step_97__provenance

        # Step 96: Store blobs
        facts = [
            {
                'type': 'document_field',
                'field_name': 'numero',
                'value': '100',
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

        step_96_ctx = {
            'facts': facts,
            'parsed_docs': parsed_docs,
            'document_count': 1,
            'request_id': 'test-integration-96-97'
        }

        step_96_result = await step_96__store_blob(messages=[], ctx=step_96_ctx)

        # Should store successfully
        assert step_96_result['storage_completed'] is True
        assert step_96_result['next_step'] == 'provenance'

        # Step 97: Log provenance
        step_97_ctx = {
            'blob_ids': step_96_result['blob_ids'],
            'facts': facts,
            'document_count': step_96_result['document_count'],
            'request_id': step_96_result['request_id']
        }

        step_97_result = await step_97__provenance(messages=[], ctx=step_97_ctx)

        # Should log provenance successfully
        assert step_97_result['provenance_logged'] is True
        assert step_97_result['next_step'] == 'to_tool_results'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_97_to_98_flow(self, mock_rag_log):
        """Test Step 97 → Step 98 (to tool results) flow."""
        from app.orchestrators.docs import step_97__provenance

        blob_ids = [
            {
                'blob_id': 'xyz789',
                'filename': 'contract.pdf',
                'document_type': 'contratto'
            }
        ]
        facts = [
            {
                'type': 'document_field',
                'field_name': 'tipo_contratto',
                'value': 'appalto'
            }
        ]

        ctx = {
            'blob_ids': blob_ids,
            'facts': facts,
            'document_count': 1,
            'request_id': 'test-97-to-98'
        }

        result = await step_97__provenance(messages=[], ctx=ctx)

        # Should route to Step 98
        assert result['next_step'] == 'to_tool_results'
        assert result['provenance_logged'] is True

        # Context ready for Step 98
        assert 'ledger_entries' in result
        assert len(result['ledger_entries']) > 0
        assert 'facts' in ctx