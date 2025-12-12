"""
Tests for _convert_attachments_to_doc_facts() helper function (DEV-007)

This helper converts resolved attachments from AttachmentResolver into
document_facts format for ContextBuilderMerge to include in LLM context.
"""

import pytest


class TestConvertAttachmentsToDocFacts:
    """Test suite for attachment to document_facts conversion."""

    def test_convert_empty_list_returns_empty(self):
        """Empty attachments returns empty doc_facts."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        result = _convert_attachments_to_doc_facts([])
        assert result == []

    def test_convert_none_returns_empty(self):
        """None attachments returns empty doc_facts."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        result = _convert_attachments_to_doc_facts(None)
        assert result == []

    def test_convert_attachment_with_extracted_text(self):
        """Attachment with extracted_text converts to doc_fact string."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        attachments = [
            {
                "id": "doc-123",
                "filename": "report.pdf",
                "extracted_text": "This is the document content about tax calculations.",
                "extracted_data": None,
                "document_category": "financial",
            }
        ]

        result = _convert_attachments_to_doc_facts(attachments)

        assert len(result) == 1
        assert "[Documento: report.pdf]" in result[0]
        assert "This is the document content about tax calculations." in result[0]

    def test_convert_attachment_with_extracted_data_dict(self):
        """Attachment with extracted_data dict formats key-value pairs."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        attachments = [
            {
                "id": "doc-456",
                "filename": "invoice.xlsx",
                "extracted_text": None,
                "extracted_data": {
                    "total": "1500.00",
                    "tax_rate": "22%",
                    "company": "Acme Corp",
                },
                "document_category": "invoice",
            }
        ]

        result = _convert_attachments_to_doc_facts(attachments)

        assert len(result) == 1
        assert "[Documento: invoice.xlsx]" in result[0]
        assert "total: 1500.00" in result[0]
        assert "tax_rate: 22%" in result[0]
        assert "company: Acme Corp" in result[0]

    def test_convert_attachment_includes_both_text_and_data(self):
        """DEV-007 Issue 10: Both extracted_text AND extracted_data should be included."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        attachments = [
            {
                "id": "doc-789",
                "filename": "data.csv",
                "extracted_text": "Sheet1 | Name | Amount\nRow1 | John | 1000",
                "extracted_data": {"totale": "1000", "document_type": "f24"},
                "document_category": "data",
            }
        ]

        result = _convert_attachments_to_doc_facts(attachments)

        assert len(result) == 1
        # extracted_text should be included (the actual document content)
        assert "Sheet1 | Name | Amount" in result[0]
        assert "Row1 | John | 1000" in result[0]
        # extracted_data fields should also be included (except document_type which is redundant)
        assert "totale: 1000" in result[0]
        # document_type should be skipped as it's redundant with filename context
        assert "document_type:" not in result[0]

    def test_convert_truncates_long_text(self):
        """Text over 8000 chars is truncated (DEV-007 Issue 11: increased limit for deep analysis)."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        long_text = "A" * 10000  # 10000 chars
        attachments = [
            {
                "id": "doc-long",
                "filename": "large_doc.pdf",
                "extracted_text": long_text,
                "extracted_data": None,
            }
        ]

        result = _convert_attachments_to_doc_facts(attachments)

        assert len(result) == 1
        # The filename header is "[Documento: large_doc.pdf]\n" so total should be under 8100 chars
        # (8000 content + header)
        assert len(result[0]) < 8100

    def test_convert_multiple_attachments(self):
        """Multiple attachments each convert to separate doc_facts."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        attachments = [
            {
                "id": "doc-1",
                "filename": "file1.pdf",
                "extracted_text": "Content from file 1",
                "extracted_data": None,
            },
            {
                "id": "doc-2",
                "filename": "file2.xlsx",
                "extracted_text": None,
                "extracted_data": {"value": "123"},
            },
        ]

        result = _convert_attachments_to_doc_facts(attachments)

        assert len(result) == 2
        assert "[Documento: file1.pdf]" in result[0]
        assert "Content from file 1" in result[0]
        assert "[Documento: file2.xlsx]" in result[1]
        assert "value: 123" in result[1]

    def test_convert_attachment_missing_filename(self):
        """Attachment without filename uses 'unknown' as default."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        attachments = [
            {
                "id": "doc-no-name",
                "extracted_text": "Some content",
            }
        ]

        result = _convert_attachments_to_doc_facts(attachments)

        assert len(result) == 1
        assert "[Documento: unknown]" in result[0]

    def test_convert_attachment_with_empty_extracted_data(self):
        """Attachment with empty extracted_data dict falls back to extracted_text."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        attachments = [
            {
                "id": "doc-empty-data",
                "filename": "file.pdf",
                "extracted_text": "Fallback text content",
                "extracted_data": {},
            }
        ]

        result = _convert_attachments_to_doc_facts(attachments)

        assert len(result) == 1
        # Empty dict is falsy in Python, so should fall back to extracted_text
        assert "Fallback text content" in result[0]

    def test_convert_skips_none_values_in_extracted_data(self):
        """Extracted_data with None values are skipped."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        attachments = [
            {
                "id": "doc-with-nulls",
                "filename": "file.xlsx",
                "extracted_data": {
                    "field1": "value1",
                    "field2": None,
                    "field3": "",
                    "field4": "value4",
                },
            }
        ]

        result = _convert_attachments_to_doc_facts(attachments)

        assert len(result) == 1
        assert "field1: value1" in result[0]
        assert "field4: value4" in result[0]
        assert "field2" not in result[0]
        assert "field3" not in result[0]


class TestStep40AttachmentIntegration:
    """Test that step_40__build_context uses attachments via conversion."""

    @pytest.mark.asyncio
    async def test_step_40_converts_attachments_when_no_doc_facts(self):
        """Step 40 converts attachments to doc_facts when doc_facts is empty."""
        from unittest.mock import patch

        from app.orchestrators.facts import step_40__build_context

        attachments = [
            {
                "id": "test-attachment",
                "filename": "pension_comparison.xlsx",
                "extracted_text": "Comparison of pension fund vs ETF returns",
                "extracted_data": None,
            }
        ]

        ctx = {
            "attachments": attachments,
            "document_facts": [],  # Empty - should trigger conversion
            "request_id": "test-step40-attachments",
            "canonical_facts": [],
        }

        with patch("app.orchestrators.facts.rag_step_log"):
            result = await step_40__build_context(messages=[], ctx=ctx)

        # Verify the function completed
        assert isinstance(result, dict)
        # The merged_context should contain our attachment content
        merged_context = result.get("merged_context", "")
        assert "pension_comparison.xlsx" in merged_context or "pension" in merged_context.lower()

    @pytest.mark.asyncio
    async def test_step_40_preserves_existing_doc_facts(self):
        """Step 40 does NOT convert attachments when doc_facts already exist."""
        from unittest.mock import patch

        from app.orchestrators.facts import step_40__build_context

        attachments = [
            {
                "id": "ignored-attachment",
                "filename": "should_be_ignored.pdf",
                "extracted_text": "This should not appear",
            }
        ]

        existing_doc_facts = ["[Existing Fact] Pre-existing document fact content"]

        ctx = {
            "attachments": attachments,
            "document_facts": existing_doc_facts,  # Already has doc_facts
            "request_id": "test-step40-preserve",
            "canonical_facts": [],
        }

        with patch("app.orchestrators.facts.rag_step_log"):
            result = await step_40__build_context(messages=[], ctx=ctx)

        # Should use existing doc_facts, not convert attachments
        merged_context = result.get("merged_context", "")
        assert "Pre-existing document fact content" in merged_context
        # The attachment should NOT be in context
        assert "should_be_ignored.pdf" not in merged_context
