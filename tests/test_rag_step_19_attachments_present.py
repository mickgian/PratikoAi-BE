"""
Tests for RAG STEP 19 — Attachments present? (RAG.preflight.attachments.present)

This decision step checks whether attachments are present in the request.
Routes to document validation (Step 84) if attachments exist, otherwise continues
to golden set matching (Step 24).
"""

from unittest.mock import patch

import pytest


class TestRAGStep19AttachmentsPresent:
    """Test suite for RAG STEP 19 - Attachments present decision."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_attachments_present(self, mock_rag_log):
        """Test Step 19: Attachments present - routes to validation."""
        from app.orchestrators.preflight import step_19__attach_check

        fingerprints = [
            {'hash': 'abc123', 'filename': 'doc.pdf', 'size': 1024}
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-19-present'
        }

        result = await step_19__attach_check(messages=[], ctx=ctx)

        # Should route to Step 84 (validation)
        assert isinstance(result, dict)
        assert result['attachments_present'] is True
        assert result['attachment_count'] == 1
        assert result['next_step'] == 'validate_attachments'  # Routes to Step 84
        assert result['request_id'] == 'test-19-present'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 19
        assert completed_log['node_label'] == 'AttachCheck'
        assert completed_log['attachments_present'] is True
        assert completed_log['decision'] == 'present'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_no_attachments(self, mock_rag_log):
        """Test Step 19: No attachments - routes to golden set."""
        from app.orchestrators.preflight import step_19__attach_check

        ctx = {
            'fingerprints': [],
            'attachment_count': 0,
            'request_id': 'test-19-none'
        }

        result = await step_19__attach_check(messages=[], ctx=ctx)

        # Should route to Step 24 (golden set)
        assert result['attachments_present'] is False
        assert result['attachment_count'] == 0
        assert result['next_step'] == 'golden_set_lookup'  # Routes to Step 24
        assert result['request_id'] == 'test-19-none'

        # Verify logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        completed_log = completed_logs[0][1]
        assert completed_log['attachments_present'] is False
        assert completed_log['decision'] == 'absent'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_multiple_attachments(self, mock_rag_log):
        """Test Step 19: Multiple attachments present."""
        from app.orchestrators.preflight import step_19__attach_check

        fingerprints = [
            {'hash': 'hash1', 'filename': 'file1.pdf', 'size': 100},
            {'hash': 'hash2', 'filename': 'file2.pdf', 'size': 200},
            {'hash': 'hash3', 'filename': 'file3.pdf', 'size': 300}
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 3,
            'request_id': 'test-19-multiple'
        }

        result = await step_19__attach_check(messages=[], ctx=ctx)

        # Should route to validation
        assert result['attachments_present'] is True
        assert result['attachment_count'] == 3
        assert result['next_step'] == 'validate_attachments'

        # Verify count in logs
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        completed_log = completed_logs[0][1]
        assert completed_log['attachment_count'] == 3

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_empty_fingerprints_list(self, mock_rag_log):
        """Test Step 19: Empty fingerprints list (no attachments)."""
        from app.orchestrators.preflight import step_19__attach_check

        ctx = {
            'fingerprints': [],
            'attachment_count': 0,
            'request_id': 'test-19-empty'
        }

        result = await step_19__attach_check(messages=[], ctx=ctx)

        # Should treat as no attachments
        assert result['attachments_present'] is False
        assert result['next_step'] == 'golden_set_lookup'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_missing_fingerprints_field(self, mock_rag_log):
        """Test Step 19: Handle missing fingerprints field."""
        from app.orchestrators.preflight import step_19__attach_check

        ctx = {
            'attachment_count': 0,
            'request_id': 'test-19-missing'
        }

        result = await step_19__attach_check(messages=[], ctx=ctx)

        # Should default to no attachments
        assert result['attachments_present'] is False
        assert result['next_step'] == 'golden_set_lookup'


class TestRAGStep19Parity:
    """Parity tests proving Step 19 preserves existing logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_parity_presence_check(self, mock_rag_log):
        """Test Step 19: Parity with existing attachment presence logic."""
        from app.orchestrators.preflight import step_19__attach_check

        # Original logic: check if attachments list is not empty
        test_cases = [
            ([], False),           # Empty list = no attachments
            ([{'hash': 'x'}], True),  # One item = attachments present
            ([{'hash': 'x'}, {'hash': 'y'}], True)  # Multiple = attachments present
        ]

        for fingerprints, expected_present in test_cases:
            mock_rag_log.reset_mock()

            ctx = {
                'fingerprints': fingerprints,
                'attachment_count': len(fingerprints),
                'request_id': f'test-parity-{len(fingerprints)}'
            }

            result = await step_19__attach_check(messages=[], ctx=ctx)

            # Verify decision matches expected
            assert result['attachments_present'] == expected_present
            assert result['attachment_count'] == len(fingerprints)

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_parity_routing_logic(self, mock_rag_log):
        """Test Step 19: Parity for routing based on attachment presence."""
        from app.orchestrators.preflight import step_19__attach_check

        # With attachments: route to validation
        ctx_with = {
            'fingerprints': [{'hash': 'abc'}],
            'attachment_count': 1,
            'request_id': 'test-parity-with'
        }

        result_with = await step_19__attach_check(messages=[], ctx=ctx_with)
        assert result_with['next_step'] == 'validate_attachments'

        # Without attachments: route to golden set
        ctx_without = {
            'fingerprints': [],
            'attachment_count': 0,
            'request_id': 'test-parity-without'
        }

        result_without = await step_19__attach_check(messages=[], ctx=ctx_without)
        assert result_without['next_step'] == 'golden_set_lookup'


class TestRAGStep19Integration:
    """Integration tests for Step 17 → Step 19 → Step 84/24 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_17_to_19_integration(self, mock_rag_log):
        """Test Step 17 (fingerprint) → Step 19 (check) integration."""
        from app.orchestrators.preflight import step_17__attachment_fingerprint, step_19__attach_check

        # Step 17: Compute fingerprints
        attachments = [
            {'filename': 'doc.pdf', 'content': b'PDF content', 'mime_type': 'application/pdf', 'size': 100}
        ]

        step_17_ctx = {
            'attachments': attachments,
            'request_id': 'test-integration-17-19'
        }

        step_17_result = await step_17__attachment_fingerprint(messages=[], ctx=step_17_ctx)

        # Should compute fingerprints and route to check
        assert step_17_result['hashes_computed'] is True
        assert step_17_result['next_step'] == 'attachments_present_check'

        # Step 19: Check if attachments present
        step_19_ctx = {
            'fingerprints': step_17_result['fingerprints'],
            'attachment_count': step_17_result['attachment_count'],
            'request_id': step_17_result['request_id']
        }

        step_19_result = await step_19__attach_check(messages=[], ctx=step_19_ctx)

        # Should detect attachments and route to validation
        assert step_19_result['attachments_present'] is True
        assert step_19_result['next_step'] == 'validate_attachments'

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_to_84_validation_flow(self, mock_rag_log):
        """Test Step 19 → Step 84 (validation) flow with attachments."""
        from app.orchestrators.preflight import step_19__attach_check

        fingerprints = [
            {'hash': 'abc123', 'filename': 'invoice.pdf', 'size': 2048}
        ]

        ctx = {
            'fingerprints': fingerprints,
            'attachment_count': 1,
            'request_id': 'test-19-to-84'
        }

        result = await step_19__attach_check(messages=[], ctx=ctx)

        # Should route to Step 84 validation
        assert result['next_step'] == 'validate_attachments'
        assert result['attachments_present'] is True

        # Context should be ready for Step 84
        assert 'fingerprints' in ctx
        assert 'attachment_count' in ctx

    @pytest.mark.asyncio
    @patch('app.orchestrators.preflight.rag_step_log')
    async def test_step_19_to_24_golden_flow(self, mock_rag_log):
        """Test Step 19 → Step 24 (golden set) flow without attachments."""
        from app.orchestrators.preflight import step_19__attach_check

        ctx = {
            'fingerprints': [],
            'attachment_count': 0,
            'request_id': 'test-19-to-24'
        }

        result = await step_19__attach_check(messages=[], ctx=ctx)

        # Should route to Step 24 golden set lookup
        assert result['next_step'] == 'golden_set_lookup'
        assert result['attachments_present'] is False