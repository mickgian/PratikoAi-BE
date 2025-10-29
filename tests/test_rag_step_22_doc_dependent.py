"""
Tests for RAG STEP 22 — Doc-dependent or refers to doc? (RAG.docs.doc.dependent.or.refers.to.doc)

This decision step checks if the user query depends on or refers to the uploaded documents.
Routes to full document processing (Step 23/87) if yes, otherwise to golden set lookup (Step 24).
"""

from unittest.mock import patch

import pytest


class TestRAGStep22DocDependent:
    """Test suite for RAG STEP 22 - Doc-dependent decision."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_22_query_refers_to_doc(self, mock_rag_log):
        """Test Step 22: Query explicitly refers to document - routes to processing."""
        from app.orchestrators.docs import step_22__doc_dependent_check

        ctx = {
            'user_query': 'Analizza la fattura allegata e dimmi il totale',
            'extracted_docs': [
                {'filename': 'fattura.pdf', 'detected_type': 'pdf', 'potential_category': 'fattura_elettronica'}
            ],
            'document_count': 1,
            'request_id': 'test-22-refers'
        }

        result = await step_22__doc_dependent_check(messages=[], ctx=ctx)

        # Should route to document processing
        assert isinstance(result, dict)
        assert result['query_depends_on_doc'] is True
        assert result['next_step'] == 'require_doc_processing'  # Routes to Step 23
        assert result['request_id'] == 'test-22-refers'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 22
        assert completed_log['node_label'] == 'DocDependent'
        assert completed_log['query_depends_on_doc'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_22_query_independent(self, mock_rag_log):
        """Test Step 22: Query independent of documents - routes to golden set."""
        from app.orchestrators.docs import step_22__doc_dependent_check

        ctx = {
            'user_query': 'Quali sono le detrazioni fiscali per il 2024?',
            'extracted_docs': [
                {'filename': 'random.pdf', 'detected_type': 'pdf'}
            ],
            'document_count': 1,
            'request_id': 'test-22-independent'
        }

        result = await step_22__doc_dependent_check(messages=[], ctx=ctx)

        # Should route to golden set
        assert result['query_depends_on_doc'] is False
        assert result['next_step'] == 'golden_set_lookup'  # Routes to Step 24
        assert result['decision'] == 'independent'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_22_explicit_document_references(self, mock_rag_log):
        """Test Step 22: Detect explicit document references in query."""
        from app.orchestrators.docs import step_22__doc_dependent_check

        test_cases = [
            ('Analizza questo documento', True),
            ('Leggi il file allegato', True),
            ('Cosa dice la fattura?', True),
            ('Estrai i dati dal PDF', True),
            ('Controlla l\'allegato', True),
            ('Cos\'è l\'IVA?', False),  # General question
            ('Spiegami le detrazioni fiscali', False),  # General question
        ]

        for query, expected_depends in test_cases:
            mock_rag_log.reset_mock()

            ctx = {
                'user_query': query,
                'extracted_docs': [{'filename': 'doc.pdf', 'detected_type': 'pdf'}],
                'document_count': 1,
                'request_id': f'test-22-ref-{expected_depends}'
            }

            result = await step_22__doc_dependent_check(messages=[], ctx=ctx)
            assert result['query_depends_on_doc'] == expected_depends

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_22_no_documents(self, mock_rag_log):
        """Test Step 22: No documents attached - always independent."""
        from app.orchestrators.docs import step_22__doc_dependent_check

        ctx = {
            'user_query': 'Analizza questo documento',
            'extracted_docs': [],
            'document_count': 0,
            'request_id': 'test-22-no-docs'
        }

        result = await step_22__doc_dependent_check(messages=[], ctx=ctx)

        # No documents means can't be document-dependent
        assert result['query_depends_on_doc'] is False
        assert result['next_step'] == 'golden_set_lookup'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_22_filename_context(self, mock_rag_log):
        """Test Step 22: Use document filename as context."""
        from app.orchestrators.docs import step_22__doc_dependent_check

        ctx = {
            'user_query': 'Quanto devo pagare?',
            'extracted_docs': [
                {'filename': 'fattura_elettronica_2024.xml', 'detected_type': 'xml', 'potential_category': 'fattura_elettronica'}
            ],
            'document_count': 1,
            'request_id': 'test-22-filename'
        }

        result = await step_22__doc_dependent_check(messages=[], ctx=ctx)

        # Query about payment with invoice attached - likely dependent
        assert 'query_depends_on_doc' in result


class TestRAGStep22Parity:
    """Parity tests proving Step 22 preserves existing logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_22_parity_dependency_check(self, mock_rag_log):
        """Test Step 22: Parity with existing document dependency logic."""
        from app.orchestrators.docs import step_22__doc_dependent_check

        # Original logic: check for document references in query
        test_cases = [
            # (query, has_docs, expected_dependent)
            ('analizza il documento', True, True),
            ('cos\'è l\'IVA', True, False),
            ('leggi la fattura', True, True),
            ('domanda generica', False, False),
        ]

        for query, has_docs, expected in test_cases:
            mock_rag_log.reset_mock()

            docs = [{'filename': 'doc.pdf'}] if has_docs else []
            ctx = {
                'user_query': query,
                'extracted_docs': docs,
                'document_count': len(docs),
                'request_id': f'test-parity-{expected}'
            }

            result = await step_22__doc_dependent_check(messages=[], ctx=ctx)
            assert result['query_depends_on_doc'] == expected


class TestRAGStep22Integration:
    """Integration tests for Step 21 → Step 22 → Step 23/24 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_21_to_22_integration(self, mock_rag_log):
        """Test Step 21 (extract) → Step 22 (check dependency) integration."""
        from app.orchestrators.preflight import step_21__doc_pre_ingest
        from app.orchestrators.docs import step_22__doc_dependent_check

        # Step 21: Extract document info
        fingerprints = [
            {'hash': 'abc', 'filename': 'fattura_2024.pdf', 'size': 1024, 'mime_type': 'application/pdf'}
        ]

        step_21_ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-integration-21-22'
        }

        step_21_result = await step_21__doc_pre_ingest(messages=[], ctx=step_21_ctx)

        # Should extract and route to doc_dependent_check
        assert step_21_result['extraction_completed'] is True
        assert step_21_result['next_step'] == 'doc_dependent_check'

        # Step 22: Check if query depends on doc
        step_22_ctx = {
            'user_query': 'Analizza la fattura e dimmi il totale',
            'extracted_docs': step_21_result['extracted_docs'],
            'document_count': step_21_result['document_count'],
            'request_id': step_21_result['request_id']
        }

        step_22_result = await step_22__doc_dependent_check(messages=[], ctx=step_22_ctx)

        # Should detect dependency and route to processing
        assert step_22_result['query_depends_on_doc'] is True
        assert step_22_result['next_step'] == 'require_doc_processing'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_22_to_23_processing_flow(self, mock_rag_log):
        """Test Step 22 → Step 23 (require doc processing) flow."""
        from app.orchestrators.docs import step_22__doc_dependent_check

        ctx = {
            'user_query': 'Estrai i dati dalla fattura allegata',
            'extracted_docs': [
                {'filename': 'fattura.xml', 'detected_type': 'xml', 'potential_category': 'fattura_elettronica'}
            ],
            'document_count': 1,
            'request_id': 'test-22-to-23'
        }

        result = await step_22__doc_dependent_check(messages=[], ctx=ctx)

        # Should route to Step 23 document processing
        assert result['next_step'] == 'require_doc_processing'
        assert result['query_depends_on_doc'] is True

        # Context ready for Step 23
        assert 'extracted_docs' in ctx
        assert ctx['document_count'] > 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_22_to_24_golden_flow(self, mock_rag_log):
        """Test Step 22 → Step 24 (golden set) flow."""
        from app.orchestrators.docs import step_22__doc_dependent_check

        ctx = {
            'user_query': 'Quali sono le detrazioni fiscali disponibili?',
            'extracted_docs': [
                {'filename': 'some_doc.pdf', 'detected_type': 'pdf'}
            ],
            'document_count': 1,
            'request_id': 'test-22-to-24'
        }

        result = await step_22__doc_dependent_check(messages=[], ctx=ctx)

        # Should route to Step 24 golden set lookup
        assert result['next_step'] == 'golden_set_lookup'
        assert result['query_depends_on_doc'] is False