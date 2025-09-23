"""
Tests for RAG STEP 17 — AttachmentFingerprint.compute SHA-256 per attachment (RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment)

This process step computes SHA-256 hashes for each attachment to enable deduplication,
caching, and change detection.
"""

import hashlib
from unittest.mock import patch

import pytest


class TestRAGStep17AttachmentFingerprint:
    """Test suite for RAG STEP 17 - Compute attachment fingerprints."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_single_attachment_hash(self, mock_rag_log):
        """Test Step 17: Compute SHA-256 hash for single attachment."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        attachment = {
            'filename': 'contract.pdf',
            'content': b'PDF contract content here',
            'mime_type': 'application/pdf',
            'size': 1024
        }

        ctx = {
            'attachments': [attachment],
            'request_id': 'test-17-single'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Verify hash computation
        assert isinstance(result, dict)
        assert result['hashes_computed'] is True
        assert result['attachment_count'] == 1
        assert len(result['fingerprints']) == 1

        # Verify SHA-256 hash matches expected
        expected_hash = hashlib.sha256(attachment['content']).hexdigest()
        assert result['fingerprints'][0]['hash'] == expected_hash
        assert result['fingerprints'][0]['filename'] == 'contract.pdf'
        assert result['fingerprints'][0]['size'] == 1024

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 17
        assert completed_log['node_label'] == 'AttachmentFingerprint'
        assert completed_log['attachment_count'] == 1
        assert completed_log['hashes_computed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_multiple_attachments(self, mock_rag_log):
        """Test Step 17: Compute hashes for multiple attachments."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        attachments = [
            {
                'filename': 'invoice.pdf',
                'content': b'Invoice PDF content',
                'mime_type': 'application/pdf',
                'size': 2048
            },
            {
                'filename': 'receipt.jpg',
                'content': b'Receipt image data',
                'mime_type': 'image/jpeg',
                'size': 1500
            },
            {
                'filename': 'contract.docx',
                'content': b'Contract Word document',
                'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'size': 3072
            }
        ]

        ctx = {
            'attachments': attachments,
            'request_id': 'test-17-multiple'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Verify all hashes computed
        assert result['hashes_computed'] is True
        assert result['attachment_count'] == 3
        assert len(result['fingerprints']) == 3

        # Verify each hash
        for i, attachment in enumerate(attachments):
            expected_hash = hashlib.sha256(attachment['content']).hexdigest()
            assert result['fingerprints'][i]['hash'] == expected_hash
            assert result['fingerprints'][i]['filename'] == attachment['filename']
            assert result['fingerprints'][i]['size'] == attachment['size']

        # Verify unique hashes (no duplicates)
        hashes = [fp['hash'] for fp in result['fingerprints']]
        assert len(hashes) == len(set(hashes))

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_duplicate_content_detection(self, mock_rag_log):
        """Test Step 17: Detect duplicate content via same hash."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        same_content = b'Same content in both files'

        attachments = [
            {
                'filename': 'file1.txt',
                'content': same_content,
                'mime_type': 'text/plain',
                'size': 27
            },
            {
                'filename': 'file2.txt',
                'content': same_content,
                'mime_type': 'text/plain',
                'size': 27
            }
        ]

        ctx = {
            'attachments': attachments,
            'request_id': 'test-17-duplicate'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Same content should produce same hash
        assert result['attachment_count'] == 2
        assert result['fingerprints'][0]['hash'] == result['fingerprints'][1]['hash']
        assert result['has_duplicates'] is True
        assert result['duplicate_count'] == 1  # One duplicate pair

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_empty_content(self, mock_rag_log):
        """Test Step 17: Handle empty attachment content."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        attachment = {
            'filename': 'empty.txt',
            'content': b'',
            'mime_type': 'text/plain',
            'size': 0
        }

        ctx = {
            'attachments': [attachment],
            'request_id': 'test-17-empty'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Should compute hash even for empty content
        expected_hash = hashlib.sha256(b'').hexdigest()
        assert result['hashes_computed'] is True
        assert result['fingerprints'][0]['hash'] == expected_hash
        assert result['fingerprints'][0]['size'] == 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_large_file(self, mock_rag_log):
        """Test Step 17: Compute hash for large file."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        # Simulate 10MB file
        large_content = b'X' * (10 * 1024 * 1024)

        attachment = {
            'filename': 'large_file.pdf',
            'content': large_content,
            'mime_type': 'application/pdf',
            'size': len(large_content)
        }

        ctx = {
            'attachments': [attachment],
            'request_id': 'test-17-large'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Should handle large file
        expected_hash = hashlib.sha256(large_content).hexdigest()
        assert result['hashes_computed'] is True
        assert result['fingerprints'][0]['hash'] == expected_hash
        assert result['fingerprints'][0]['size'] == len(large_content)

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_no_attachments(self, mock_rag_log):
        """Test Step 17: Handle no attachments gracefully."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        ctx = {
            'attachments': [],
            'request_id': 'test-17-none'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Should handle empty list
        assert result['hashes_computed'] is True
        assert result['attachment_count'] == 0
        assert result['fingerprints'] == []
        assert result['has_duplicates'] is False


class TestRAGStep17Parity:
    """Parity tests proving Step 17 preserves existing hash logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_parity_hash_algorithm(self, mock_rag_log):
        """Test Step 17: Uses same SHA-256 algorithm as existing code."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        # Test against KnowledgeIntegrator._generate_content_hash pattern
        content = b'Test content for hash parity'

        # Original pattern from knowledge_integrator.py:505
        original_hash = hashlib.sha256(content).hexdigest()

        attachment = {
            'filename': 'test.txt',
            'content': content,
            'mime_type': 'text/plain',
            'size': len(content)
        }

        ctx = {
            'attachments': [attachment],
            'request_id': 'test-parity-hash'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Should produce identical hash
        assert result['fingerprints'][0]['hash'] == original_hash

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_parity_document_model(self, mock_rag_log):
        """Test Step 17: Hash format compatible with Document.file_hash."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        # Document model expects SHA-256 hex string (64 chars)
        content = b'Document content'

        attachment = {
            'filename': 'document.pdf',
            'content': content,
            'mime_type': 'application/pdf',
            'size': len(content)
        }

        ctx = {
            'attachments': [attachment],
            'request_id': 'test-parity-model'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Verify hash format matches Document.file_hash expectations
        hash_value = result['fingerprints'][0]['hash']
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256 hex is 64 chars
        assert all(c in '0123456789abcdef' for c in hash_value)


class TestRAGStep17Integration:
    """Integration tests for Step 17 in the document processing flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_routes_to_step_19(self, mock_rag_log):
        """Test Step 17: Routes to Step 19 (attachments present check)."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        attachments = [
            {'filename': 'doc.pdf', 'content': b'PDF content', 'mime_type': 'application/pdf', 'size': 100}
        ]

        ctx = {
            'attachments': attachments,
            'request_id': 'test-17-route'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Should route to Step 19
        assert result['hashes_computed'] is True
        assert result['next_step'] == 'attachments_present_check'  # Step 19

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_prepares_for_validation(self, mock_rag_log):
        """Test Step 17: Prepares fingerprints for Step 84 validation."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        attachments = [
            {
                'filename': 'test.pdf',
                'content': b'Test PDF',
                'mime_type': 'application/pdf',
                'size': 8
            }
        ]

        ctx = {
            'attachments': attachments,
            'request_id': 'test-17-validation-prep'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Should provide fingerprints for later validation
        assert 'fingerprints' in result
        assert result['attachment_count'] > 0

        # Fingerprints should be ready for Step 84
        fingerprint = result['fingerprints'][0]
        assert 'hash' in fingerprint
        assert 'filename' in fingerprint
        assert 'size' in fingerprint

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_hash_for_caching(self, mock_rag_log):
        """Test Step 17: Provides hashes for cache key generation."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint

        attachments = [
            {'filename': 'a.pdf', 'content': b'Content A', 'mime_type': 'application/pdf', 'size': 9},
            {'filename': 'b.pdf', 'content': b'Content B', 'mime_type': 'application/pdf', 'size': 9}
        ]

        ctx = {
            'attachments': attachments,
            'request_id': 'test-17-cache'
        }

        result = await step_17__attachment_fingerprint(messages=[], ctx=ctx)

        # Hashes should be usable for cache key construction
        hashes = [fp['hash'] for fp in result['fingerprints']]
        assert len(hashes) == 2
        assert all(isinstance(h, str) and len(h) == 64 for h in hashes)

        # Combined hash for cache key (sorted for consistency)
        combined_hash = hashlib.sha256(''.join(sorted(hashes)).encode()).hexdigest()
        assert len(combined_hash) == 64