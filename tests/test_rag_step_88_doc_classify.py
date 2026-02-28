"""
Tests for RAG STEP 88 — DocClassifier.classify Detect document type (RAG.classify.docclassifier.classify.detect.document.type)

This process step classifies sanitized documents to determine their specific type
(Fattura XML, F24, Contratto, Payslip, Generic) for routing to appropriate parsers.
"""

from unittest.mock import patch

import pytest


class TestRAGStep88DocClassify:
    """Test suite for RAG STEP 88 - Document classification."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_classify_fattura_xml(self, mock_rag_log):
        """Test Step 88: Classify Fattura Elettronica XML."""
        from app.orchestrators.docs import step_88__doc_classify

        sanitized_docs = [
            {
                "filename": "IT12345678901_FPA01.xml",
                "content": b'<?xml version="1.0"?><FatturaElettronica xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">',
                "mime_type": "application/xml",
                "detected_type": "xml",
                "potential_category": "fattura_elettronica",
                "is_safe": True,
            }
        ]

        ctx = {"sanitized_docs": sanitized_docs, "document_count": 1, "request_id": "test-88-fattura"}

        result = await step_88__doc_classify(messages=[], ctx=ctx)

        # Should classify as Fattura XML
        assert isinstance(result, dict)
        assert result["classification_completed"] is True
        assert result["document_count"] == 1
        assert result["classified_docs"][0]["document_type"] == "fattura_elettronica"
        assert result["request_id"] == "test-88-fattura"

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 88
        assert completed_log["node_label"] == "DocClassify"
        assert completed_log["classification_completed"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_classify_f24(self, mock_rag_log):
        """Test Step 88: Classify F24 document."""
        from app.orchestrators.docs import step_88__doc_classify

        sanitized_docs = [
            {
                "filename": "F24_2024.pdf",
                "content": b"%PDF-1.4\nF24 ELIDE content...",
                "mime_type": "application/pdf",
                "detected_type": "pdf",
                "potential_category": "f24",
                "is_safe": True,
            }
        ]

        ctx = {"sanitized_docs": sanitized_docs, "document_count": 1, "request_id": "test-88-f24"}

        result = await step_88__doc_classify(messages=[], ctx=ctx)

        # Should classify as F24
        assert result["classification_completed"] is True
        assert result["classified_docs"][0]["document_type"] == "f24"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_classify_contratto(self, mock_rag_log):
        """Test Step 88: Classify Contratto."""
        from app.orchestrators.docs import step_88__doc_classify

        sanitized_docs = [
            {
                "filename": "contratto_lavoro_2024.pdf",
                "content": b"%PDF-1.4\nContratto di lavoro...",
                "mime_type": "application/pdf",
                "detected_type": "pdf",
                "potential_category": "contratto",
                "is_safe": True,
            }
        ]

        ctx = {"sanitized_docs": sanitized_docs, "document_count": 1, "request_id": "test-88-contratto"}

        result = await step_88__doc_classify(messages=[], ctx=ctx)

        # Should classify as Contratto
        assert result["classification_completed"] is True
        assert result["classified_docs"][0]["document_type"] == "contratto"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_classify_payslip(self, mock_rag_log):
        """Test Step 88: Classify Busta Paga (Payslip)."""
        from app.orchestrators.docs import step_88__doc_classify

        sanitized_docs = [
            {
                "filename": "busta_paga_gennaio_2024.pdf",
                "content": b"%PDF-1.4\nBusta Paga content...",
                "mime_type": "application/pdf",
                "detected_type": "pdf",
                "potential_category": "busta_paga",
                "is_safe": True,
            }
        ]

        ctx = {"sanitized_docs": sanitized_docs, "document_count": 1, "request_id": "test-88-payslip"}

        result = await step_88__doc_classify(messages=[], ctx=ctx)

        # Should classify as Busta Paga
        assert result["classification_completed"] is True
        assert result["classified_docs"][0]["document_type"] == "busta_paga"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_classify_generic(self, mock_rag_log):
        """Test Step 88: Classify generic document."""
        from app.orchestrators.docs import step_88__doc_classify

        sanitized_docs = [
            {
                "filename": "report.pdf",
                "content": b"%PDF-1.4\nGeneric business report...",
                "mime_type": "application/pdf",
                "detected_type": "pdf",
                "potential_category": None,
                "is_safe": True,
            }
        ]

        ctx = {"sanitized_docs": sanitized_docs, "document_count": 1, "request_id": "test-88-generic"}

        result = await step_88__doc_classify(messages=[], ctx=ctx)

        # Should classify as generic
        assert result["classification_completed"] is True
        assert result["classified_docs"][0]["document_type"] == "generic"
        assert result["next_step"] == "doc_type_decision"  # Routes to Step 89

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_content_based_classification(self, mock_rag_log):
        """Test Step 88: Content-based classification when filename is ambiguous."""
        from app.orchestrators.docs import step_88__doc_classify

        sanitized_docs = [
            {
                "filename": "document.xml",
                "content": b'<?xml version="1.0"?><FatturaElettronica xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"><FatturaElettronicaHeader>',
                "mime_type": "application/xml",
                "detected_type": "xml",
                "potential_category": None,  # No hint from filename
                "is_safe": True,
            }
        ]

        ctx = {"sanitized_docs": sanitized_docs, "document_count": 1, "request_id": "test-88-content"}

        result = await step_88__doc_classify(messages=[], ctx=ctx)

        # Should detect Fattura from content
        assert result["classification_completed"] is True
        assert result["classified_docs"][0]["document_type"] == "fattura_elettronica"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_multiple_documents(self, mock_rag_log):
        """Test Step 88: Classify multiple documents."""
        from app.orchestrators.docs import step_88__doc_classify

        sanitized_docs = [
            {
                "filename": "fattura.xml",
                "content": b'<?xml version="1.0"?><FatturaElettronica>',
                "mime_type": "application/xml",
                "detected_type": "xml",
                "potential_category": "fattura_elettronica",
                "is_safe": True,
            },
            {
                "filename": "F24.pdf",
                "content": b"%PDF F24 content",
                "mime_type": "application/pdf",
                "detected_type": "pdf",
                "potential_category": "f24",
                "is_safe": True,
            },
            {
                "filename": "contratto.pdf",
                "content": b"%PDF Contratto content",
                "mime_type": "application/pdf",
                "detected_type": "pdf",
                "potential_category": "contratto",
                "is_safe": True,
            },
        ]

        ctx = {"sanitized_docs": sanitized_docs, "document_count": 3, "request_id": "test-88-multi"}

        result = await step_88__doc_classify(messages=[], ctx=ctx)

        # Should classify all documents
        assert result["classification_completed"] is True
        assert result["document_count"] == 3
        assert len(result["classified_docs"]) == 3

        types = [doc["document_type"] for doc in result["classified_docs"]]
        assert "fattura_elettronica" in types
        assert "f24" in types
        assert "contratto" in types


class TestRAGStep88Parity:
    """Parity tests proving Step 88 preserves existing classification logic."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_parity_fattura_detection(self, mock_rag_log):
        """Test Step 88: Parity with Step 21 fattura detection."""
        from app.orchestrators.docs import step_88__doc_classify

        # Same pattern as Step 21
        sanitized_docs = [
            {
                "filename": "IT12345678901_FPA01.xml",
                "content": b'<?xml version="1.0"?><FatturaElettronica>',
                "mime_type": "application/xml",
                "detected_type": "xml",
                "potential_category": "fattura_elettronica",
                "is_safe": True,
            }
        ]

        ctx = {"sanitized_docs": sanitized_docs, "document_count": 1, "request_id": "test-parity-fattura"}

        result = await step_88__doc_classify(messages=[], ctx=ctx)

        # Should preserve Step 21's hint
        assert result["classified_docs"][0]["document_type"] == "fattura_elettronica"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_parity_category_mapping(self, mock_rag_log):
        """Test Step 88: Parity with Step 21 category hints."""
        from app.orchestrators.docs import step_88__doc_classify

        # Test all Step 21 categories
        test_cases = [
            ("fattura_elettronica", "fattura_elettronica"),
            ("f24", "f24"),
            ("contratto", "contratto"),
            ("busta_paga", "busta_paga"),
            ("bilancio", "generic"),  # bilancio maps to generic
            (None, "generic"),  # No category maps to generic
        ]

        for potential_category, expected_type in test_cases:
            sanitized_docs = [
                {
                    "filename": "test.pdf",
                    "content": b"%PDF content",
                    "mime_type": "application/pdf",
                    "detected_type": "pdf",
                    "potential_category": potential_category,
                    "is_safe": True,
                }
            ]

            ctx = {"sanitized_docs": sanitized_docs, "document_count": 1, "request_id": "test-parity"}

            result = await step_88__doc_classify(messages=[], ctx=ctx)

            assert result["classified_docs"][0]["document_type"] == expected_type, (
                f"Failed for potential_category={potential_category}"
            )


class TestRAGStep88Integration:
    """Integration tests for Step 87 → Step 88 → Step 89 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_87_to_88_integration(self, mock_rag_log):
        """Test Step 87 (sanitize) → Step 88 (classify) integration."""
        from app.orchestrators.docs import step_87__doc_security, step_88__doc_classify

        # Step 87: Sanitize document
        extracted_docs = [
            {
                "filename": "IT123_FPA.xml",
                "content": b'<?xml version="1.0"?><FatturaElettronica xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">',
                "mime_type": "application/xml",
                "detected_type": "xml",
                "potential_category": "fattura_elettronica",
            }
        ]

        step_87_ctx = {"extracted_docs": extracted_docs, "document_count": 1, "request_id": "test-integration-87-88"}

        step_87_result = await step_87__doc_security(messages=[], ctx=step_87_ctx)

        # Should sanitize and route to classify
        assert step_87_result["sanitization_completed"] is True
        assert step_87_result["next_step"] == "doc_classify"

        # Step 88: Classify sanitized documents
        step_88_ctx = {
            "sanitized_docs": step_87_result["sanitized_docs"],
            "document_count": step_87_result["document_count"],
            "request_id": step_87_result["request_id"],
        }

        step_88_result = await step_88__doc_classify(messages=[], ctx=step_88_ctx)

        # Should classify successfully
        assert step_88_result["classification_completed"] is True
        assert step_88_result["classified_docs"][0]["document_type"] == "fattura_elettronica"
        assert step_88_result["next_step"] == "doc_type_decision"

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    async def test_step_88_to_89_flow(self, mock_rag_log):
        """Test Step 88 → Step 89 (decision) flow."""
        from app.orchestrators.docs import step_88__doc_classify

        sanitized_docs = [
            {
                "filename": "F24_2024.pdf",
                "content": b"%PDF F24 content",
                "mime_type": "application/pdf",
                "detected_type": "pdf",
                "potential_category": "f24",
                "is_safe": True,
            }
        ]

        ctx = {"sanitized_docs": sanitized_docs, "document_count": 1, "request_id": "test-88-to-89"}

        result = await step_88__doc_classify(messages=[], ctx=ctx)

        # Should route to Step 89 decision
        assert result["next_step"] == "doc_type_decision"
        assert result["classification_completed"] is True

        # Context ready for Step 89
        assert "classified_docs" in result
        assert len(result["classified_docs"]) > 0
        assert result["classified_docs"][0]["document_type"] == "f24"
