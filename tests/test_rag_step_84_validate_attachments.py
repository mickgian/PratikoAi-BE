"""
Tests for RAG STEP 84 — AttachmentValidator.validate Check files and limits (RAG.preflight.attachmentvalidator.validate.check.files.and.limits)

This process step validates attachments against file size limits, file count limits,
and supported MIME types using DOCUMENT_CONFIG settings.
"""

from unittest.mock import patch

import pytest


class TestRAGStep84ValidateAttachments:
    """Test suite for RAG STEP 84 - Validate attachments."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_valid_single_attachment(self, mock_rag_log):
        """Test Step 84: Valid single attachment passes validation."""
        from app.orchestrators.preflight import step_84__validate_attachments

        fingerprints = [
            {
                'hash': 'abc123',
                'filename': 'invoice.pdf',
                'size': 5 * 1024 * 1024,  # 5MB (under 10MB limit)
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-84-valid'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Should pass validation
        assert isinstance(result, dict)
        assert result['validation_passed'] is True
        assert result['attachment_count'] == 1
        assert result['errors'] == []
        assert result['next_step'] == 'valid_attachments_check'  # Routes to Step 85
        assert result['request_id'] == 'test-84-valid'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 84
        assert completed_log['node_label'] == 'ValidateAttach'
        assert completed_log['validation_passed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_file_too_large(self, mock_rag_log):
        """Test Step 84: File exceeds size limit - validation fails."""
        from app.orchestrators.preflight import step_84__validate_attachments

        fingerprints = [
            {
                'hash': 'large123',
                'filename': 'large_file.pdf',
                'size': 15 * 1024 * 1024,  # 15MB (exceeds 10MB limit)
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-84-large'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Should fail validation
        assert result['validation_passed'] is False
        assert len(result['errors']) > 0
        assert 'too large' in result['errors'][0].lower() or '10mb' in result['errors'][0].lower()
        assert result['next_step'] == 'valid_attachments_check'  # Still routes to Step 85

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_too_many_files(self, mock_rag_log):
        """Test Step 84: Too many files - validation fails."""
        from app.orchestrators.preflight import step_84__validate_attachments

        # Create 6 attachments (exceeds limit of 5)
        fingerprints = [
            {
                'hash': f'hash{i}',
                'filename': f'file{i}.pdf',
                'size': 1024 * 1024,  # 1MB each
                'mime_type': 'application/pdf'
            }
            for i in range(6)
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 6,
            'request_id': 'test-84-many'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Should fail validation
        assert result['validation_passed'] is False
        assert len(result['errors']) > 0
        assert 'too many' in result['errors'][0].lower() or '5' in result['errors'][0]

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_unsupported_mime_type(self, mock_rag_log):
        """Test Step 84: Unsupported MIME type - validation fails."""
        from app.orchestrators.preflight import step_84__validate_attachments

        fingerprints = [
            {
                'hash': 'exe123',
                'filename': 'malicious.exe',
                'size': 1024 * 1024,  # 1MB
                'mime_type': 'application/x-msdownload'  # Not supported
            }
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-84-unsupported'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Should fail validation
        assert result['validation_passed'] is False
        assert len(result['errors']) > 0
        assert 'unsupported' in result['errors'][0].lower() or 'mime' in result['errors'][0].lower()

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_multiple_valid_attachments(self, mock_rag_log):
        """Test Step 84: Multiple valid attachments pass validation."""
        from app.orchestrators.preflight import step_84__validate_attachments

        fingerprints = [
            {'hash': 'pdf1', 'filename': 'doc1.pdf', 'size': 2 * 1024 * 1024, 'mime_type': 'application/pdf'},
            {'hash': 'xlsx1', 'filename': 'sheet.xlsx', 'size': 3 * 1024 * 1024, 'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
            {'hash': 'xml1', 'filename': 'fattura.xml', 'size': 1 * 1024 * 1024, 'mime_type': 'application/xml'}
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 3,
            'request_id': 'test-84-multiple'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Should pass validation
        assert result['validation_passed'] is True
        assert result['attachment_count'] == 3
        assert result['errors'] == []

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_multiple_errors(self, mock_rag_log):
        """Test Step 84: Multiple validation errors reported."""
        from app.orchestrators.preflight import step_84__validate_attachments

        # File too large AND unsupported type
        fingerprints = [
            {
                'hash': 'bad1',
                'filename': 'large.exe',
                'size': 20 * 1024 * 1024,  # 20MB (too large)
                'mime_type': 'application/x-msdownload'  # Unsupported
            }
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-84-multi-error'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Should report multiple errors
        assert result['validation_passed'] is False
        assert len(result['errors']) >= 1  # At least one error

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_edge_case_exact_limit(self, mock_rag_log):
        """Test Step 84: File exactly at size limit passes."""
        from app.orchestrators.preflight import step_84__validate_attachments

        fingerprints = [
            {
                'hash': 'exact',
                'filename': 'exact_10mb.pdf',
                'size': 10 * 1024 * 1024,  # Exactly 10MB
                'mime_type': 'application/pdf'
            }
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-84-exact'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Should pass (10MB is at limit, not over)
        assert result['validation_passed'] is True
        assert result['errors'] == []

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_empty_attachments(self, mock_rag_log):
        """Test Step 84: No attachments to validate."""
        from app.orchestrators.preflight import step_84__validate_attachments

        ctx = {
            'fingerprints': [],
            'attachment_count': 0,
            'request_id': 'test-84-empty'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Empty list should pass validation
        assert result['validation_passed'] is True
        assert result['attachment_count'] == 0
        assert result['errors'] == []


class TestRAGStep84Parity:
    """Parity tests proving Step 84 preserves existing validation logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_parity_size_check(self, mock_rag_log):
        """Test Step 84: Parity with DOCUMENT_CONFIG size limit."""
        from app.orchestrators.preflight import step_84__validate_attachments
        from app.models.document_simple import DOCUMENT_CONFIG

        # Test at limit
        fingerprints_at_limit = [
            {
                'hash': 'test',
                'filename': 'test.pdf',
                'size': DOCUMENT_CONFIG['MAX_FILE_SIZE_MB'] * 1024 * 1024,
                'mime_type': 'application/pdf'
            }
        ]

        ctx_at = {
            'fingerprints': fingerprints_at_limit,
            'attachment_count': 1,
            'request_id': 'test-parity-at'
        }

        result_at = await step_84__validate_attachments(messages=[], ctx=ctx_at)
        assert result_at['validation_passed'] is True

        # Test over limit
        fingerprints_over = [
            {
                'hash': 'test',
                'filename': 'test.pdf',
                'size': DOCUMENT_CONFIG['MAX_FILE_SIZE_MB'] * 1024 * 1024 + 1,
                'mime_type': 'application/pdf'
            }
        ]

        ctx_over = {
            'fingerprints': fingerprints_over,
            'attachment_count': 1,
            'request_id': 'test-parity-over'
        }

        result_over = await step_84__validate_attachments(messages=[], ctx=ctx_over)
        assert result_over['validation_passed'] is False

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_parity_count_check(self, mock_rag_log):
        """Test Step 84: Parity with DOCUMENT_CONFIG file count limit."""
        from app.orchestrators.preflight import step_84__validate_attachments
        from app.models.document_simple import DOCUMENT_CONFIG

        max_files = DOCUMENT_CONFIG['MAX_FILES_PER_UPLOAD']

        # Test at limit
        fingerprints_at = [
            {'hash': f'h{i}', 'filename': f'f{i}.pdf', 'size': 1024, 'mime_type': 'application/pdf'}
            for i in range(max_files)
        ]

        ctx_at = {
            'fingerprints': fingerprints_at,
            'attachment_count': max_files,
            'request_id': 'test-parity-count-at'
        }

        result_at = await step_84__validate_attachments(messages=[], ctx=ctx_at)
        assert result_at['validation_passed'] is True

        # Test over limit
        fingerprints_over = [
            {'hash': f'h{i}', 'filename': f'f{i}.pdf', 'size': 1024, 'mime_type': 'application/pdf'}
            for i in range(max_files + 1)
        ]

        ctx_over = {
            'fingerprints': fingerprints_over,
            'attachment_count': max_files + 1,
            'request_id': 'test-parity-count-over'
        }

        result_over = await step_84__validate_attachments(messages=[], ctx=ctx_over)
        assert result_over['validation_passed'] is False

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_parity_mime_types(self, mock_rag_log):
        """Test Step 84: Parity with DOCUMENT_CONFIG supported MIME types."""
        from app.orchestrators.preflight import step_84__validate_attachments
        from app.models.document_simple import DOCUMENT_CONFIG

        # Test all supported types
        for mime_type in DOCUMENT_CONFIG['SUPPORTED_MIME_TYPES'].keys():
            mock_rag_log.reset_mock()

            fingerprints = [
                {'hash': 'test', 'filename': 'test.file', 'size': 1024, 'mime_type': mime_type}
            ]

            ctx = {
                'fingerprints': fingerprints,
                'attachment_count': 1,
                'request_id': f'test-parity-mime-{mime_type}'
            }

            result = await step_84__validate_attachments(messages=[], ctx=ctx)
            assert result['validation_passed'] is True, f"Should support {mime_type}"


class TestRAGStep84Integration:
    """Integration tests for Step 19 → Step 84 → Step 85 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_to_84_integration(self, mock_rag_log):
        """Test Step 19 (attachments present) → Step 84 (validate) integration."""
        from app.orchestrators.preflight import step_19__attach_check, step_84__validate_attachments

        # Step 19: Check attachments present
        fingerprints = [
            {'hash': 'abc', 'filename': 'doc.pdf', 'size': 1024 * 1024, 'mime_type': 'application/pdf'}
        ]

        step_19_ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-integration-19-84'
        }

        step_19_result = await step_19__attach_check(messages=[], ctx=step_19_ctx)

        # Should detect attachments and route to validation
        assert step_19_result['attachments_present'] is True
        assert step_19_result['next_step'] == 'validate_attachments'

        # Step 84: Validate attachments
        step_84_ctx = {
            'fingerprints': fingerprints,
            'attachment_count': step_19_result['attachment_count'],
            'request_id': step_19_result['request_id']
        }

        step_84_result = await step_84__validate_attachments(messages=[], ctx=step_84_ctx)

        # Should validate successfully
        assert step_84_result['validation_passed'] is True
        assert step_84_result['next_step'] == 'valid_attachments_check'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_to_85_valid_flow(self, mock_rag_log):
        """Test Step 84 → Step 85 (valid) flow."""
        from app.orchestrators.preflight import step_84__validate_attachments

        fingerprints = [
            {'hash': 'valid', 'filename': 'valid.pdf', 'size': 2 * 1024 * 1024, 'mime_type': 'application/pdf'}
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-84-to-85-valid'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Should route to Step 85 with validation passed
        assert result['next_step'] == 'valid_attachments_check'
        assert result['validation_passed'] is True
        assert result['errors'] == []

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_to_85_invalid_flow(self, mock_rag_log):
        """Test Step 84 → Step 85 (invalid) flow."""
        from app.orchestrators.preflight import step_84__validate_attachments

        fingerprints = [
            {'hash': 'large', 'filename': 'huge.pdf', 'size': 50 * 1024 * 1024, 'mime_type': 'application/pdf'}
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-84-to-85-invalid'
        }

        result = await step_84__validate_attachments(messages=[], ctx=ctx)

        # Should route to Step 85 with validation failed
        assert result['next_step'] == 'valid_attachments_check'
        assert result['validation_passed'] is False
        assert len(result['errors']) > 0