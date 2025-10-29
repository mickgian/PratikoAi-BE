"""
Tests for RAG STEP 85 — Valid attachments? (RAG.preflight.valid.attachments)

This decision step checks validation results from Step 84.
Routes to document pre-ingest (Step 21) if valid, otherwise returns error (Step 86).
"""

from unittest.mock import patch

import pytest


class TestRAGStep85ValidAttachments:
    """Test suite for RAG STEP 85 - Valid attachments decision."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_attachments_valid(self, mock_rag_log):
        """Test Step 85: Valid attachments - routes to pre-ingest."""
        from app.orchestrators.preflight import step_85__valid_attachments_check

        ctx = {
            'validation_passed': True,
            'attachment_count': 2,
            'errors': [],
            'request_id': 'test-85-valid'
        }

        result = await step_85__valid_attachments_check(messages=[], ctx=ctx)

        # Should route to Step 21 (doc pre-ingest)
        assert isinstance(result, dict)
        assert result['attachments_valid'] is True
        assert result['attachment_count'] == 2
        assert result['next_step'] == 'doc_pre_ingest'  # Routes to Step 21
        assert result['request_id'] == 'test-85-valid'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 85
        assert completed_log['node_label'] == 'AttachOK'
        assert completed_log['attachments_valid'] is True
        assert completed_log['decision'] == 'valid'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_attachments_invalid(self, mock_rag_log):
        """Test Step 85: Invalid attachments - routes to error."""
        from app.orchestrators.preflight import step_85__valid_attachments_check

        ctx = {
            'validation_passed': False,
            'attachment_count': 1,
            'errors': ['File too large. Maximum 10MB, got 15.0MB'],
            'request_id': 'test-85-invalid'
        }

        result = await step_85__valid_attachments_check(messages=[], ctx=ctx)

        # Should route to Step 86 (tool error)
        assert result['attachments_valid'] is False
        assert result['next_step'] == 'tool_error'  # Routes to Step 86
        assert result['error_count'] == 1
        assert 'too large' in result['errors'][0].lower()

        # Verify logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        completed_log = completed_logs[0][1]
        assert completed_log['attachments_valid'] is False
        assert completed_log['decision'] == 'invalid'
        assert completed_log['error_count'] == 1

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_multiple_errors(self, mock_rag_log):
        """Test Step 85: Multiple validation errors reported."""
        from app.orchestrators.preflight import step_85__valid_attachments_check

        errors = [
            'File too large. Maximum 10MB, got 15.0MB',
            'Unsupported MIME type application/x-msdownload',
            'Too many files. Maximum 5 files allowed, got 6'
        ]

        ctx = {
            'validation_passed': False,
            'attachment_count': 6,
            'errors': errors,
            'request_id': 'test-85-multi-error'
        }

        result = await step_85__valid_attachments_check(messages=[], ctx=ctx)

        # Should route to error with all errors preserved
        assert result['attachments_valid'] is False
        assert result['error_count'] == 3
        assert result['errors'] == errors
        assert result['next_step'] == 'tool_error'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_empty_errors_list_valid(self, mock_rag_log):
        """Test Step 85: Empty errors list means valid."""
        from app.orchestrators.preflight import step_85__valid_attachments_check

        ctx = {
            'validation_passed': True,
            'attachment_count': 1,
            'errors': [],
            'request_id': 'test-85-empty-errors'
        }

        result = await step_85__valid_attachments_check(messages=[], ctx=ctx)

        # Empty errors = valid attachments
        assert result['attachments_valid'] is True
        assert result['next_step'] == 'doc_pre_ingest'
        assert result['error_count'] == 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_missing_validation_field(self, mock_rag_log):
        """Test Step 85: Handle missing validation_passed field."""
        from app.orchestrators.preflight import step_85__valid_attachments_check

        ctx = {
            'attachment_count': 1,
            'errors': [],
            'request_id': 'test-85-missing'
        }

        result = await step_85__valid_attachments_check(messages=[], ctx=ctx)

        # Should default to checking errors list
        assert result['attachments_valid'] is True  # No errors means valid
        assert result['next_step'] == 'doc_pre_ingest'


class TestRAGStep85Parity:
    """Parity tests proving Step 85 preserves existing validation logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_parity_validation_check(self, mock_rag_log):
        """Test Step 85: Parity with existing validation result checking."""
        from app.orchestrators.preflight import step_85__valid_attachments_check

        # Original logic: if validation_passed == True, proceed; else error
        test_cases = [
            (True, [], 'doc_pre_ingest', True),   # Passed, no errors
            (False, ['Error 1'], 'tool_error', False),  # Failed, has errors
            (False, ['E1', 'E2'], 'tool_error', False),  # Failed, multiple errors
        ]

        for validation_passed, errors, expected_next, expected_valid in test_cases:
            mock_rag_log.reset_mock()

            ctx = {
                'validation_passed': validation_passed,
                'errors': errors,
                'attachment_count': 1,
                'request_id': f'test-parity-{validation_passed}'
            }

            result = await step_85__valid_attachments_check(messages=[], ctx=ctx)

            # Verify decision matches expected
            assert result['attachments_valid'] == expected_valid
            assert result['next_step'] == expected_next
            assert result['error_count'] == len(errors)

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_parity_routing_logic(self, mock_rag_log):
        """Test Step 85: Parity for routing based on validation."""
        from app.orchestrators.preflight import step_85__valid_attachments_check

        # Valid: route to doc pre-ingest
        ctx_valid = {
            'validation_passed': True,
            'errors': [],
            'attachment_count': 1,
            'request_id': 'test-parity-valid'
        }

        result_valid = await step_85__valid_attachments_check(messages=[], ctx=ctx_valid)
        assert result_valid['next_step'] == 'doc_pre_ingest'

        # Invalid: route to tool error
        ctx_invalid = {
            'validation_passed': False,
            'errors': ['Validation error'],
            'attachment_count': 1,
            'request_id': 'test-parity-invalid'
        }

        result_invalid = await step_85__valid_attachments_check(messages=[], ctx=ctx_invalid)
        assert result_invalid['next_step'] == 'tool_error'


class TestRAGStep85Integration:
    """Integration tests for Step 84 → Step 85 → Step 21/86 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_84_to_85_integration(self, mock_rag_log):
        """Test Step 84 (validate) → Step 85 (check) integration."""
        from app.orchestrators.preflight import step_84__validate_attachments, step_85__valid_attachments_check

        # Step 84: Validate attachments
        fingerprints = [
            {'hash': 'abc', 'filename': 'doc.pdf', 'size': 2 * 1024 * 1024, 'mime_type': 'application/pdf'}
        ]

        step_84_ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-integration-84-85'
        }

        step_84_result = await step_84__validate_attachments(messages=[], ctx=step_84_ctx)

        # Should validate successfully and route to check
        assert step_84_result['validation_passed'] is True
        assert step_84_result['next_step'] == 'valid_attachments_check'

        # Step 85: Check validation result
        step_85_ctx = {
            'validation_passed': step_84_result['validation_passed'],
            'errors': step_84_result['errors'],
            'attachment_count': step_84_result['attachment_count'],
            'request_id': step_84_result['request_id']
        }

        step_85_result = await step_85__valid_attachments_check(messages=[], ctx=step_85_ctx)

        # Should confirm valid and route to pre-ingest
        assert step_85_result['attachments_valid'] is True
        assert step_85_result['next_step'] == 'doc_pre_ingest'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_to_21_valid_flow(self, mock_rag_log):
        """Test Step 85 → Step 21 (doc pre-ingest) flow with valid attachments."""
        from app.orchestrators.preflight import step_85__valid_attachments_check

        ctx = {
            'validation_passed': True,
            'errors': [],
            'attachment_count': 2,
            'request_id': 'test-85-to-21'
        }

        result = await step_85__valid_attachments_check(messages=[], ctx=ctx)

        # Should route to Step 21 doc pre-ingest
        assert result['next_step'] == 'doc_pre_ingest'
        assert result['attachments_valid'] is True

        # Context should be ready for Step 21
        assert 'attachment_count' in ctx

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_85_to_86_invalid_flow(self, mock_rag_log):
        """Test Step 85 → Step 86 (tool error) flow with invalid attachments."""
        from app.orchestrators.preflight import step_85__valid_attachments_check

        ctx = {
            'validation_passed': False,
            'errors': ['File too large'],
            'attachment_count': 1,
            'request_id': 'test-85-to-86'
        }

        result = await step_85__valid_attachments_check(messages=[], ctx=ctx)

        # Should route to Step 86 tool error
        assert result['next_step'] == 'tool_error'
        assert result['attachments_valid'] is False

        # Error details should be ready for Step 86
        assert 'errors' in ctx
        assert len(ctx['errors']) > 0