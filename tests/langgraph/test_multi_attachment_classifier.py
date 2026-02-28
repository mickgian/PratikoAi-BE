"""TDD Tests for Multi-Attachment Classifier Bug.

These tests verify that when multiple attachments are uploaded in the SAME message,
ALL their filenames are passed to the query composition classifier.

DEV-007: Written BEFORE the fix to ensure TDD approach.

BUG: When user uploads Payslip 8 + Payslip 9 in Turn 2:
- `attachments` = [Payslip 10 (prior), Payslip 8 (current), Payslip 9 (current)]
- `attachments[0]` = Payslip 10 (WRONG - from Turn 1!)
- Classifier only sees Payslip 10, ignores Payslip 8 and 9

FIX: Filter to get only CURRENT attachments and pass ALL their filenames.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestMultiAttachmentFilenames:
    """Test that multiple attachment filenames are passed to classifier."""

    @pytest.mark.asyncio
    async def test_classifier_receives_all_current_attachment_filenames(self):
        """Classifier should receive ALL current attachment filenames, not just first.

        This is the critical test - when user uploads multiple files in one message,
        the classifier should know about ALL of them.
        """
        from app.orchestrators.classify import step_31__classify_domain

        # Given: Current attachments (Turn 2) with multiple files
        current_message_index = 1  # Second user message
        attachments = [
            # Prior attachment (Turn 1) - should be FILTERED OUT
            {"filename": "Payslip 10 - Ottobre 2025.pdf", "message_index": 0},
            # Current attachments (Turn 2) - should ALL be included
            {"filename": "Payslip 8 - Agosto 2025.pdf", "message_index": 1},
            {"filename": "Payslip 9 - Settembre 2025.pdf", "message_index": 1},
        ]

        ctx = {
            "user_query": "E queste?",
            "attachments": attachments,
            "current_message_index": current_message_index,
        }

        # Mock the classifier service
        mock_classifier = MagicMock()
        mock_classification = MagicMock()
        mock_classification.domain = MagicMock(value="document_analysis")
        mock_classification.action = MagicMock(value="explain")
        mock_classification.confidence = 0.95
        mock_classification.fallback_used = False
        mock_classifier.classify = AsyncMock(return_value=mock_classification)

        # Capture what filenames are passed to detect_query_composition
        captured_filenames = []

        async def capture_composition(query, has_attachments, attachment_filename=None):
            captured_filenames.append(attachment_filename)
            return MagicMock(value="pure_doc")

        mock_classifier.detect_query_composition = capture_composition

        # When: step_31 processes the classification
        result = await step_31__classify_domain(
            user_query="E queste?",
            classification_service=mock_classifier,
            ctx=ctx,
        )

        # Then: Classifier should receive ONLY current attachment filenames
        assert len(captured_filenames) == 1, "detect_query_composition should be called once"
        filename_str = captured_filenames[0]

        # Should include BOTH current attachments (comma-separated)
        assert "Payslip 8 - Agosto 2025.pdf" in filename_str, f"Should include Payslip 8, got: {filename_str}"
        assert "Payslip 9 - Settembre 2025.pdf" in filename_str, f"Should include Payslip 9, got: {filename_str}"
        # Should NOT include prior attachment
        assert "Payslip 10 - Ottobre 2025.pdf" not in filename_str, (
            f"Should NOT include prior attachment Payslip 10, got: {filename_str}"
        )

    @pytest.mark.asyncio
    async def test_classifier_filters_out_prior_attachments(self):
        """Prior attachments should be filtered out when current attachments exist."""
        from app.orchestrators.classify import step_31__classify_domain

        # Given: Mix of prior and current attachments
        attachments = [
            {"filename": "Prior_Doc.pdf", "message_index": 0},  # Prior
            {"filename": "Current_Doc_1.pdf", "message_index": 2},  # Current
            {"filename": "Current_Doc_2.pdf", "message_index": 2},  # Current
        ]

        ctx = {
            "user_query": "Analizza questi",
            "attachments": attachments,
            "current_message_index": 2,
        }

        mock_classifier = MagicMock()
        mock_classification = MagicMock()
        mock_classification.domain = MagicMock(value="document_analysis")
        mock_classification.action = MagicMock(value="analyze")
        mock_classification.confidence = 0.9
        mock_classification.fallback_used = False
        mock_classifier.classify = AsyncMock(return_value=mock_classification)

        captured_filenames = []

        async def capture_composition(query, has_attachments, attachment_filename=None):
            captured_filenames.append(attachment_filename)
            return MagicMock(value="pure_doc")

        mock_classifier.detect_query_composition = capture_composition

        # When
        await step_31__classify_domain(
            user_query="Analizza questi",
            classification_service=mock_classifier,
            ctx=ctx,
        )

        # Then: Only current attachment filenames should be passed
        assert len(captured_filenames) == 1
        filename_str = captured_filenames[0]
        assert "Prior_Doc.pdf" not in filename_str, "Prior attachment should be filtered out"
        assert "Current_Doc_1.pdf" in filename_str, "Current attachment 1 should be included"
        assert "Current_Doc_2.pdf" in filename_str, "Current attachment 2 should be included"


class TestMultiAttachmentRegression:
    """Regression tests for the multiple attachments ignored bug.

    Bug: User uploads Payslip 8+9 in Turn 2, but LLM only analyzes Payslip 8
    because classifier only sees Payslip 10 from Turn 1.
    """

    @pytest.mark.asyncio
    async def test_turn2_multiple_attachments_all_passed_to_classifier(self):
        """Turn 2 with multiple attachments should pass ALL to classifier.

        Regression test for: Payslip 9 ignored when uploaded with Payslip 8.
        """
        from app.orchestrators.classify import step_31__classify_domain

        # Given: State simulating Turn 2 with multiple new attachments
        # Order matters: prior comes first in resolved_attachments
        attachments = [
            {"filename": "Payslip 10 - Ottobre 2025.pdf", "message_index": 0},  # Turn 1
            {"filename": "Payslip 8 - Agosto 2025.pdf", "message_index": 1},  # Turn 2
            {"filename": "Payslip 9 - Settembre 2025.pdf", "message_index": 1},  # Turn 2
        ]

        ctx = {
            "user_query": "E queste?",
            "attachments": attachments,
            "current_message_index": 1,  # Turn 2
        }

        mock_classifier = MagicMock()
        mock_classification = MagicMock()
        mock_classification.domain = MagicMock(value="document_analysis")
        mock_classification.action = MagicMock(value="explain")
        mock_classification.confidence = 0.95
        mock_classification.fallback_used = False
        mock_classifier.classify = AsyncMock(return_value=mock_classification)

        captured_filename = None

        async def capture_composition(query, has_attachments, attachment_filename=None):
            nonlocal captured_filename
            captured_filename = attachment_filename
            return MagicMock(value="pure_doc")

        mock_classifier.detect_query_composition = capture_composition

        # When
        await step_31__classify_domain(
            user_query="E queste?",
            classification_service=mock_classifier,
            ctx=ctx,
        )

        # Then: Payslip 9 should NOT be ignored
        # The bug was that only attachments[0] was used (Payslip 10)
        # After fix, should have current attachments only
        assert "Payslip 9 - Settembre 2025.pdf" in captured_filename, (
            f"Payslip 9 should NOT be ignored! Got: {captured_filename}"
        )
        assert "Payslip 8 - Agosto 2025.pdf" in captured_filename, (
            f"Payslip 8 should be included. Got: {captured_filename}"
        )
        assert "Payslip 10 - Ottobre 2025.pdf" not in captured_filename, (
            f"Prior attachment Payslip 10 should be filtered out. Got: {captured_filename}"
        )

    @pytest.mark.asyncio
    async def test_single_current_attachment_still_works(self):
        """Single attachment upload should still work correctly."""
        from app.orchestrators.classify import step_31__classify_domain

        # Given: Single current attachment (normal case)
        attachments = [
            {"filename": "Invoice_2025.pdf", "message_index": 0},
        ]

        ctx = {
            "user_query": "Spiegami questa fattura",
            "attachments": attachments,
            "current_message_index": 0,
        }

        mock_classifier = MagicMock()
        mock_classification = MagicMock()
        mock_classification.domain = MagicMock(value="document_analysis")
        mock_classification.action = MagicMock(value="explain")
        mock_classification.confidence = 0.9
        mock_classification.fallback_used = False
        mock_classifier.classify = AsyncMock(return_value=mock_classification)

        captured_filename = None

        async def capture_composition(query, has_attachments, attachment_filename=None):
            nonlocal captured_filename
            captured_filename = attachment_filename
            return MagicMock(value="pure_doc")

        mock_classifier.detect_query_composition = capture_composition

        # When
        await step_31__classify_domain(
            user_query="Spiegami questa fattura",
            classification_service=mock_classifier,
            ctx=ctx,
        )

        # Then: Single attachment should be passed correctly
        assert captured_filename == "Invoice_2025.pdf", f"Single attachment should be passed. Got: {captured_filename}"

    @pytest.mark.asyncio
    async def test_follow_up_question_uses_all_prior_attachments(self):
        """Follow-up question (no new attachments) should reference all prior attachments."""
        from app.orchestrators.classify import step_31__classify_domain

        # Given: Follow-up message (message_index=2) with no new attachments
        # User is asking about documents uploaded in earlier messages
        attachments = [
            {"filename": "Doc_1.pdf", "message_index": 0},
            {"filename": "Doc_2.pdf", "message_index": 1},
        ]

        ctx = {
            "user_query": "Confronta questi due documenti",
            "attachments": attachments,
            "current_message_index": 2,  # No attachments at this index
        }

        mock_classifier = MagicMock()
        mock_classification = MagicMock()
        mock_classification.domain = MagicMock(value="document_analysis")
        mock_classification.action = MagicMock(value="compare")
        mock_classification.confidence = 0.9
        mock_classification.fallback_used = False
        mock_classifier.classify = AsyncMock(return_value=mock_classification)

        captured_filename = None

        async def capture_composition(query, has_attachments, attachment_filename=None):
            nonlocal captured_filename
            captured_filename = attachment_filename
            return MagicMock(value="pure_doc")

        mock_classifier.detect_query_composition = capture_composition

        # When
        await step_31__classify_domain(
            user_query="Confronta questi due documenti",
            classification_service=mock_classifier,
            ctx=ctx,
        )

        # Then: All prior attachments should be included for context
        assert "Doc_1.pdf" in captured_filename, f"Doc_1 should be included. Got: {captured_filename}"
        assert "Doc_2.pdf" in captured_filename, f"Doc_2 should be included. Got: {captured_filename}"
