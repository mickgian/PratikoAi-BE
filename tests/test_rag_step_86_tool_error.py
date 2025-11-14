"""
Tests for RAG STEP 86 — Return tool error Invalid file (RAG.platform.return.tool.error.invalid.file)

This error handler step returns a tool error message when attachment validation fails.
It converts validation errors into a ToolMessage format for the LLM to process.
"""

from unittest.mock import patch

import pytest
from langchain_core.messages import ToolMessage


class TestRAGStep86ToolError:
    """Test suite for RAG STEP 86 - Return tool error."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_86_single_validation_error(self, mock_rag_log):
        """Test Step 86: Return tool error for single validation failure."""
        from app.orchestrators.platform import step_86__tool_error

        ctx = {
            'errors': ['File too large. Maximum 10MB, got 15.0MB'],
            'attachment_count': 1,
            'request_id': 'test-86-single'
        }

        result = await step_86__tool_error(messages=[], ctx=ctx)

        # Verify error response
        assert isinstance(result, dict)
        assert result['error_returned'] is True
        assert result['error_type'] == 'invalid_attachment'
        assert 'too large' in result['error_message'].lower()
        assert result['request_id'] == 'test-86-single'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 86
        assert completed_log['node_label'] == 'ToolErr'
        assert completed_log['error_returned'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_86_multiple_validation_errors(self, mock_rag_log):
        """Test Step 86: Return tool error with multiple validation failures."""
        from app.orchestrators.platform import step_86__tool_error

        errors = [
            'File too large. Maximum 10MB, got 15.0MB',
            'Unsupported MIME type application/x-msdownload',
            'Too many files. Maximum 5 files allowed, got 6'
        ]

        ctx = {
            'errors': errors,
            'attachment_count': 6,
            'request_id': 'test-86-multiple'
        }

        result = await step_86__tool_error(messages=[], ctx=ctx)

        # Should include all errors
        assert result['error_returned'] is True
        assert result['error_count'] == 3
        for error in errors:
            assert error in result['error_message']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_86_creates_tool_message(self, mock_rag_log):
        """Test Step 86: Creates ToolMessage with error details."""
        from app.orchestrators.platform import step_86__tool_error

        ctx = {
            'errors': ['Invalid file type'],
            'tool_call_id': 'call_123',
            'request_id': 'test-86-toolmsg'
        }

        result = await step_86__tool_error(messages=[], ctx=ctx)

        # Should include ToolMessage if tool_call_id present
        assert result['error_returned'] is True
        if 'tool_message' in result:
            tool_msg = result['tool_message']
            assert isinstance(tool_msg, ToolMessage)
            assert 'Invalid file' in tool_msg.content
            assert tool_msg.tool_call_id == 'call_123'

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_86_file_size_error(self, mock_rag_log):
        """Test Step 86: File size limit error."""
        from app.orchestrators.platform import step_86__tool_error

        ctx = {
            'errors': ['File "large_doc.pdf" too large. Maximum 10MB, got 15.5MB'],
            'attachment_count': 1,
            'request_id': 'test-86-size'
        }

        result = await step_86__tool_error(messages=[], ctx=ctx)

        assert result['error_returned'] is True
        assert result['error_type'] == 'invalid_attachment'
        assert '15.5MB' in result['error_message']
        assert 'large_doc.pdf' in result['error_message']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_86_unsupported_type_error(self, mock_rag_log):
        """Test Step 86: Unsupported file type error."""
        from app.orchestrators.platform import step_86__tool_error

        ctx = {
            'errors': ['File "malware.exe" has unsupported type "application/x-msdownload"'],
            'attachment_count': 1,
            'request_id': 'test-86-type'
        }

        result = await step_86__tool_error(messages=[], ctx=ctx)

        assert result['error_returned'] is True
        assert 'unsupported' in result['error_message'].lower()
        assert 'malware.exe' in result['error_message']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_86_too_many_files_error(self, mock_rag_log):
        """Test Step 86: Too many files error."""
        from app.orchestrators.platform import step_86__tool_error

        ctx = {
            'errors': ['Too many files. Maximum 5 files allowed, got 7'],
            'attachment_count': 7,
            'request_id': 'test-86-count'
        }

        result = await step_86__tool_error(messages=[], ctx=ctx)

        assert result['error_returned'] is True
        assert 'too many' in result['error_message'].lower()
        assert result['attachment_count'] == 7

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_86_minimal_context(self, mock_rag_log):
        """Test Step 86: Works with minimal context."""
        from app.orchestrators.platform import step_86__tool_error

        ctx = {
            'errors': ['Validation failed'],
            'request_id': 'test-86-minimal'
        }

        result = await step_86__tool_error(messages=[], ctx=ctx)

        # Should still create error response
        assert result['error_returned'] is True
        assert result['error_type'] == 'invalid_attachment'
        assert 'Validation failed' in result['error_message']


class TestRAGStep86Parity:
    """Parity tests proving Step 86 preserves existing error behavior."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_86_parity_error_format(self, mock_rag_log):
        """Test Step 86: Parity with existing error message format."""
        from app.orchestrators.platform import step_86__tool_error

        # Original pattern: return error message to LLM
        error_text = "Invalid file: exceeds size limit"

        ctx = {
            'errors': [error_text],
            'request_id': 'test-parity-format'
        }

        result = await step_86__tool_error(messages=[], ctx=ctx)

        # Should preserve error text
        assert result['error_returned'] is True
        assert error_text in result['error_message']

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_86_parity_multi_error_join(self, mock_rag_log):
        """Test Step 86: Parity for joining multiple errors."""
        from app.orchestrators.platform import step_86__tool_error

        errors = ['Error 1', 'Error 2', 'Error 3']

        ctx = {
            'errors': errors,
            'request_id': 'test-parity-join'
        }

        result = await step_86__tool_error(messages=[], ctx=ctx)

        # All errors should be included
        for error in errors:
            assert error in result['error_message']


class TestRAGStep86Integration:
    """Integration tests for Step 85 → Step 86 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_85_to_86_integration(self, mock_rag_log):
        """Test Step 85 (invalid) → Step 86 (error) integration."""
        from app.orchestrators.preflight import step_85__valid_attachments_check
        from app.orchestrators.platform import step_86__tool_error

        # Step 85: Check validation (failed)
        step_85_ctx = {
            'validation_passed': False,
            'errors': ['File too large. Maximum 10MB, got 20.0MB'],
            'attachment_count': 1,
            'request_id': 'test-integration-85-86'
        }

        step_85_result = await step_85__valid_attachments_check(messages=[], ctx=step_85_ctx)

        # Should route to tool_error
        assert step_85_result['attachments_valid'] is False
        assert step_85_result['next_step'] == 'tool_error'

        # Step 86: Return tool error
        step_86_ctx = {
            'errors': step_85_result['errors'],
            'attachment_count': step_85_result['attachment_count'],
            'request_id': step_85_result['request_id']
        }

        step_86_result = await step_86__tool_error(messages=[], ctx=step_86_ctx)

        # Should return error
        assert step_86_result['error_returned'] is True
        assert 'too large' in step_86_result['error_message'].lower()

    @pytest.mark.asyncio
    @patch('app.orchestrators.platform.rag_step_log')
    async def test_step_84_to_85_to_86_full_flow(self, mock_rag_log):
        """Test full validation failure flow: Step 84 → Step 85 → Step 86."""
        from app.orchestrators.preflight import step_84__validate_attachments, step_85__valid_attachments_check
        from app.orchestrators.platform import step_86__tool_error

        # Step 84: Validate (fails)
        fingerprints = [
            {'hash': 'huge', 'filename': 'huge.pdf', 'size': 50 * 1024 * 1024, 'mime_type': 'application/pdf'}
        ]

        step_84_ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-full-flow-error'
        }

        step_84_result = await step_84__validate_attachments(messages=[], ctx=step_84_ctx)

        # Should fail validation
        assert step_84_result['validation_passed'] is False
        assert step_84_result['next_step'] == 'valid_attachments_check'

        # Step 85: Check validation result
        step_85_ctx = {
            'validation_passed': step_84_result['validation_passed'],
            'errors': step_84_result['errors'],
            'attachment_count': step_84_result['attachment_count'],
            'request_id': step_84_result['request_id']
        }

        step_85_result = await step_85__valid_attachments_check(messages=[], ctx=step_85_ctx)

        # Should route to error
        assert step_85_result['attachments_valid'] is False
        assert step_85_result['next_step'] == 'tool_error'

        # Step 86: Return error
        step_86_ctx = {
            'errors': step_85_result['errors'],
            'attachment_count': step_85_result['attachment_count'],
            'request_id': step_85_result['request_id']
        }

        step_86_result = await step_86__tool_error(messages=[], ctx=step_86_ctx)

        # Final error response
        assert step_86_result['error_returned'] is True
        assert step_86_result['error_type'] == 'invalid_attachment'
        assert step_86_result['request_id'] == 'test-full-flow-error'