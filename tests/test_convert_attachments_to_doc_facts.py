"""
Tests for _convert_attachments_to_doc_facts() helper function (DEV-007)

This helper converts resolved attachments from AttachmentResolver into
document_facts format for ContextBuilderMerge to include in LLM context.

DEV-007 PII: Function now returns tuple (doc_facts, deanonymization_map)
to support reversible PII anonymization.
"""

import pytest


class TestConvertAttachmentsToDocFacts:
    """Test suite for attachment to document_facts conversion."""

    def test_convert_empty_list_returns_empty(self):
        """Empty attachments returns empty doc_facts and empty map."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        doc_facts, deanon_map = _convert_attachments_to_doc_facts([])
        assert doc_facts == []
        assert deanon_map == {}

    def test_convert_none_returns_empty(self):
        """None attachments returns empty doc_facts and empty map."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(None)
        assert doc_facts == []
        assert deanon_map == {}

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

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(attachments)

        assert len(doc_facts) == 1
        assert "[Documento: report.pdf]" in doc_facts[0]
        assert "This is the document content about tax calculations." in doc_facts[0]

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

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(attachments)

        assert len(doc_facts) == 1
        assert "[Documento: invoice.xlsx]" in doc_facts[0]
        assert "total: 1500.00" in doc_facts[0]
        assert "tax_rate: 22%" in doc_facts[0]
        assert "company: Acme Corp" in doc_facts[0]

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

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(attachments)

        assert len(doc_facts) == 1
        # extracted_text should be included (the actual document content)
        assert "Sheet1 | Name | Amount" in doc_facts[0]
        assert "Row1 | John | 1000" in doc_facts[0]
        # extracted_data fields should also be included (except document_type which is redundant)
        assert "totale: 1000" in doc_facts[0]
        # document_type should be skipped as it's redundant with filename context
        assert "document_type:" not in doc_facts[0]

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

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(attachments)

        assert len(doc_facts) == 1
        # The filename header is "[Documento: large_doc.pdf]\n" so total should be under 8100 chars
        # (8000 content + header)
        assert len(doc_facts[0]) < 8100

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

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(attachments)

        assert len(doc_facts) == 2
        assert "[Documento: file1.pdf]" in doc_facts[0]
        assert "Content from file 1" in doc_facts[0]
        assert "[Documento: file2.xlsx]" in doc_facts[1]
        assert "value: 123" in doc_facts[1]

    def test_convert_attachment_missing_filename(self):
        """Attachment without filename uses 'unknown' as default."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        attachments = [
            {
                "id": "doc-no-name",
                "extracted_text": "Some content",
            }
        ]

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(attachments)

        assert len(doc_facts) == 1
        assert "[Documento: unknown]" in doc_facts[0]

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

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(attachments)

        assert len(doc_facts) == 1
        # Empty dict is falsy in Python, so should fall back to extracted_text
        assert "Fallback text content" in doc_facts[0]

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

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(attachments)

        assert len(doc_facts) == 1
        assert "field1: value1" in doc_facts[0]
        assert "field4: value4" in doc_facts[0]
        assert "field2" not in doc_facts[0]
        assert "field3" not in doc_facts[0]

    def test_convert_returns_deanonymization_map_for_pii(self):
        """DEV-007 PII: Returns deanonymization map for reversing PII placeholders."""
        from app.orchestrators.facts import _convert_attachments_to_doc_facts

        attachments = [
            {
                "id": "doc-pii",
                "filename": "cliente.pdf",
                "extracted_text": "Cliente: Mario Rossi, CF: RSSMRA85M01H501Z, Email: mario.rossi@email.com",
            }
        ]

        doc_facts, deanon_map = _convert_attachments_to_doc_facts(attachments)

        assert len(doc_facts) == 1
        # PII should be anonymized in doc_facts
        assert "RSSMRA85M01H501Z" not in doc_facts[0]
        assert "mario.rossi@email.com" not in doc_facts[0]
        # Deanonymization map should have entries
        assert len(deanon_map) > 0
        # Map values should be original PII
        map_values = list(deanon_map.values())
        assert "RSSMRA85M01H501Z" in map_values
        assert "mario.rossi@email.com" in map_values


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
    async def test_step_40_attachments_replace_existing_doc_facts(self):
        """DEV-007: Step 40 converts attachments and REPLACES existing doc_facts.

        When user uploads attachments, they are the source of truth for document context.
        Any pre-existing doc_facts are replaced by the converted attachments.
        """
        from unittest.mock import patch

        from app.orchestrators.facts import step_40__build_context

        attachments = [
            {
                "id": "new-attachment",
                "filename": "uploaded_document.pdf",
                "extracted_text": "Content from newly uploaded document",
            }
        ]

        existing_doc_facts = ["[Existing Fact] Pre-existing document fact content"]

        ctx = {
            "attachments": attachments,
            "document_facts": existing_doc_facts,  # Will be replaced by attachments
            "request_id": "test-step40-replace",
            "canonical_facts": [],
        }

        with patch("app.orchestrators.facts.rag_step_log"):
            result = await step_40__build_context(messages=[], ctx=ctx)

        # DEV-007: Attachments should be converted and REPLACE existing doc_facts
        merged_context = result.get("merged_context", "")
        # The attachment content should appear
        assert "uploaded_document.pdf" in merged_context
        assert "Content from newly uploaded document" in merged_context
        # Pre-existing doc_facts should NOT appear (replaced by attachments)
        assert "Pre-existing document fact content" not in merged_context

    @pytest.mark.asyncio
    async def test_step_40_current_attachments_before_prior(self):
        """DEV-007: Current attachments must appear BEFORE prior attachments in context.

        When user has prior attachments (from previous turn) and uploads new attachments,
        the new (current) attachments should appear first in the context, marked with
        [DOCUMENTI ALLEGATI ORA], and prior attachments after with [CONTESTO PRECEDENTE].
        """
        from unittest.mock import patch

        from app.orchestrators.facts import step_40__build_context

        # Simulate Turn 2: User uploads Payslip 8 and 9, having previously uploaded Payslip 10
        attachments = [
            # Prior attachment (from turn 1, message_index=0)
            {
                "id": "prior-att",
                "filename": "Payslip 10 - October.pdf",
                "extracted_text": "October payslip content",
                "message_index": 0,
            },
            # Current attachments (from turn 2, message_index=1)
            {
                "id": "current-att-1",
                "filename": "Payslip 8 - August.pdf",
                "extracted_text": "August payslip content",
                "message_index": 1,
            },
            {
                "id": "current-att-2",
                "filename": "Payslip 9 - September.pdf",
                "extracted_text": "September payslip content",
                "message_index": 1,
            },
        ]

        ctx = {
            "attachments": attachments,
            "current_message_index": 1,  # User is on turn 2
            "request_id": "test-step40-ordering",
            "canonical_facts": [],
        }

        with patch("app.orchestrators.facts.rag_step_log"):
            result = await step_40__build_context(messages=[], ctx=ctx)

        merged_context = result.get("merged_context", "")

        # Verify all attachments are present
        assert "Payslip 8" in merged_context
        assert "Payslip 9" in merged_context
        assert "Payslip 10" in merged_context

        # Verify markers are correct
        assert "[DOCUMENTI ALLEGATI ORA]" in merged_context
        assert "[CONTESTO PRECEDENTE]" in merged_context

        # CRITICAL: Verify ordering - current documents MUST come before prior
        # Find positions of each document
        pos_payslip_8 = merged_context.find("Payslip 8")
        pos_payslip_9 = merged_context.find("Payslip 9")
        pos_payslip_10 = merged_context.find("Payslip 10")

        # Current (Payslip 8 and 9) should appear before prior (Payslip 10)
        assert pos_payslip_8 < pos_payslip_10, "Payslip 8 (current) should appear before Payslip 10 (prior)"
        assert pos_payslip_9 < pos_payslip_10, "Payslip 9 (current) should appear before Payslip 10 (prior)"

        # Verify [DOCUMENTI ALLEGATI ORA] marker appears before [CONTESTO PRECEDENTE]
        pos_current_marker = merged_context.find("[DOCUMENTI ALLEGATI ORA]")
        pos_prior_marker = merged_context.find("[CONTESTO PRECEDENTE]")
        assert pos_current_marker < pos_prior_marker, (
            "Current attachment marker should appear before prior attachment marker"
        )
