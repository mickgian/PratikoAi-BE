"""
Tests for RAG STEP 87 — DocSanitizer.sanitize Strip macros and JS (RAG.docs.docsanitizer.sanitize.strip.macros.and.js)

This process step sanitizes uploaded documents by stripping macros, JavaScript, and other
potentially malicious content before further processing.
"""

from unittest.mock import patch

import pytest


class TestRAGStep87DocSecurity:
    """Test suite for RAG STEP 87 - Document security sanitization."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_sanitize_pdf_with_javascript(self, mock_rag_log):
        """Test Step 87: Sanitize PDF containing JavaScript."""
        from app.orchestrators.docs import step_87__doc_security

        extracted_docs = [
            {
                'filename': 'invoice.pdf',
                'content': b'%PDF-1.4\n/JS <javascript code here>\n%%EOF',
                'mime_type': 'application/pdf',
                'detected_type': 'pdf'
            }
        ]

        ctx = {
            'extracted_docs': extracted_docs,
            'document_count': 1,
            'request_id': 'test-87-pdf-js'
        }

        result = await step_87__doc_security(messages=[], ctx=ctx)

        # Should detect and remove JavaScript
        assert isinstance(result, dict)
        assert result['sanitization_completed'] is True
        assert result['document_count'] == 1
        assert result['threats_removed'] > 0
        assert result['request_id'] == 'test-87-pdf-js'

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 87
        assert completed_log['node_label'] == 'DocSecurity'
        assert completed_log['sanitization_completed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_sanitize_office_with_macros(self, mock_rag_log):
        """Test Step 87: Sanitize Office document with macros."""
        from app.orchestrators.docs import step_87__doc_security

        # Simulate Office document with VBA macros
        extracted_docs = [
            {
                'filename': 'document.docx',
                'content': b'PK\x03\x04...vbaProject.bin...macros...',
                'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'detected_type': 'docx'
            }
        ]

        ctx = {
            'extracted_docs': extracted_docs,
            'document_count': 1,
            'request_id': 'test-87-macro'
        }

        result = await step_87__doc_security(messages=[], ctx=ctx)

        # Should detect macros
        assert result['sanitization_completed'] is True
        assert result['threats_removed'] > 0
        assert 'sanitized_docs' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_clean_document(self, mock_rag_log):
        """Test Step 87: Clean document with no threats."""
        from app.orchestrators.docs import step_87__doc_security

        extracted_docs = [
            {
                'filename': 'clean.pdf',
                'content': b'%PDF-1.4\nClean content\n%%EOF',
                'mime_type': 'application/pdf',
                'detected_type': 'pdf'
            }
        ]

        ctx = {
            'extracted_docs': extracted_docs,
            'document_count': 1,
            'request_id': 'test-87-clean'
        }

        result = await step_87__doc_security(messages=[], ctx=ctx)

        # Should pass through clean documents
        assert result['sanitization_completed'] is True
        assert result['threats_removed'] == 0
        assert result['next_step'] == 'doc_classify'  # Routes to Step 88

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_multiple_documents(self, mock_rag_log):
        """Test Step 87: Sanitize multiple documents."""
        from app.orchestrators.docs import step_87__doc_security

        extracted_docs = [
            {
                'filename': 'doc1.pdf',
                'content': b'%PDF-1.4\n/JS <script>\n%%EOF',
                'mime_type': 'application/pdf',
                'detected_type': 'pdf'
            },
            {
                'filename': 'doc2.xlsx',
                'content': b'PK\x03\x04...clean content...',
                'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'detected_type': 'xlsx'
            },
            {
                'filename': 'doc3.xml',
                'content': b'<?xml version="1.0"?><!ENTITY xxe SYSTEM "file:///etc/passwd">',
                'mime_type': 'application/xml',
                'detected_type': 'xml'
            }
        ]

        ctx = {
            'extracted_docs': extracted_docs,
            'document_count': 3,
            'request_id': 'test-87-multi'
        }

        result = await step_87__doc_security(messages=[], ctx=ctx)

        # Should sanitize all documents
        assert result['sanitization_completed'] is True
        assert result['document_count'] == 3
        assert len(result['sanitized_docs']) == 3
        assert result['threats_removed'] >= 2  # At least PDF JS and XXE

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_detect_activex(self, mock_rag_log):
        """Test Step 87: Detect ActiveX objects."""
        from app.orchestrators.docs import step_87__doc_security

        extracted_docs = [
            {
                'filename': 'malicious.doc',
                'content': b'...ActiveXObject...Shell.Application...',
                'mime_type': 'application/msword',
                'detected_type': 'doc'
            }
        ]

        ctx = {
            'extracted_docs': extracted_docs,
            'document_count': 1,
            'request_id': 'test-87-activex'
        }

        result = await step_87__doc_security(messages=[], ctx=ctx)

        # Should detect ActiveX
        assert result['sanitization_completed'] is True
        assert result['threats_removed'] > 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_detect_xxe(self, mock_rag_log):
        """Test Step 87: Detect XML External Entity (XXE) attacks."""
        from app.orchestrators.docs import step_87__doc_security

        extracted_docs = [
            {
                'filename': 'fattura.xml',
                'content': b'<?xml version="1.0"?><!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>',
                'mime_type': 'application/xml',
                'detected_type': 'xml'
            }
        ]

        ctx = {
            'extracted_docs': extracted_docs,
            'document_count': 1,
            'request_id': 'test-87-xxe'
        }

        result = await step_87__doc_security(messages=[], ctx=ctx)

        # Should detect XXE
        assert result['sanitization_completed'] is True
        assert result['threats_removed'] > 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_threat_details(self, mock_rag_log):
        """Test Step 87: Provide detailed threat information."""
        from app.orchestrators.docs import step_87__doc_security

        extracted_docs = [
            {
                'filename': 'suspicious.pdf',
                'content': b'%PDF-1.4\n/JS <malicious script>\n/Launch <executable>\n%%EOF',
                'mime_type': 'application/pdf',
                'detected_type': 'pdf'
            }
        ]

        ctx = {
            'extracted_docs': extracted_docs,
            'document_count': 1,
            'request_id': 'test-87-details'
        }

        result = await step_87__doc_security(messages=[], ctx=ctx)

        # Should provide threat details
        assert 'threat_details' in result
        assert len(result['threat_details']) > 0


class TestRAGStep87Parity:
    """Parity tests proving Step 87 preserves existing security logic."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_parity_pdf_javascript_detection(self, mock_rag_log):
        """Test Step 87: Parity for PDF JavaScript detection."""
        from app.orchestrators.docs import step_87__doc_security

        # Test PDF with JavaScript (same pattern as DocumentUploader)
        pdf_content = b'%PDF-1.4\n/JS <script>\n/JavaScript <code>\n%%EOF'

        extracted_docs = [
            {
                'filename': 'test.pdf',
                'content': pdf_content,
                'mime_type': 'application/pdf',
                'detected_type': 'pdf'
            }
        ]

        ctx = {
            'extracted_docs': extracted_docs,
            'document_count': 1,
            'request_id': 'test-parity'
        }

        result = await step_87__doc_security(messages=[], ctx=ctx)

        # Should detect JavaScript threats
        assert result['threats_removed'] >= 1
        assert any('JavaScript' in str(detail['threats']) for detail in result['threat_details'])

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_parity_script_content_detection(self, mock_rag_log):
        """Test Step 87: Parity for script content detection."""
        from app.orchestrators.docs import step_87__doc_security

        # Test content with scripts (same patterns as DocumentUploader)
        test_cases = [
            (b'javascript:alert(1)', "JavaScript protocol"),
            (b'vbscript:msgbox', "VBScript protocol"),
            (b'<script>alert(1)</script>', "Script tag"),
            (b'eval(malicious_code)', "Code evaluation"),
            (b'ActiveXObject("WScript.Shell")', "ActiveX object")
        ]

        for content, expected_threat_type in test_cases:
            extracted_docs = [
                {
                    'filename': 'test.txt',
                    'content': content,
                    'mime_type': 'text/plain',
                    'detected_type': 'txt'
                }
            ]

            ctx = {
                'extracted_docs': extracted_docs,
                'document_count': 1,
                'request_id': 'test-parity-script'
            }

            result = await step_87__doc_security(messages=[], ctx=ctx)

            # Should detect threats
            assert result['threats_removed'] > 0, f"Failed to detect: {expected_threat_type}"


class TestRAGStep87Integration:
    """Integration tests for Step 85 → Step 87 → Step 88 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_85_to_87_integration(self, mock_rag_log):
        """Test Step 85 (valid) → Step 87 (sanitize) integration."""
        from app.orchestrators.preflight import step_85__valid_attachments_check
        from app.orchestrators.docs import step_87__doc_security

        # Step 85: Valid attachments
        step_85_ctx = {
            'validation_passed': True,
            'errors': [],
            'attachment_count': 1,
            'fingerprints': [
                {'hash': 'abc', 'filename': 'doc.pdf', 'size': 1024, 'mime_type': 'application/pdf'}
            ],
            'extracted_docs': [
                {
                    'filename': 'doc.pdf',
                    'content': b'%PDF-1.4\nClean content\n%%EOF',
                    'mime_type': 'application/pdf',
                    'detected_type': 'pdf'
                }
            ],
            'request_id': 'test-integration-85-87'
        }

        step_85_result = await step_85__valid_attachments_check(messages=[], ctx=step_85_ctx)

        # Should route to Step 21 (then to Step 87 after Step 22)
        assert step_85_result['attachments_valid'] is True
        assert step_85_result['next_step'] == 'doc_pre_ingest'

        # Step 87: Sanitize documents
        step_87_ctx = {
            'extracted_docs': step_85_ctx['extracted_docs'],
            'document_count': step_85_result['attachment_count'],
            'request_id': step_85_result['request_id']
        }

        step_87_result = await step_87__doc_security(messages=[], ctx=step_87_ctx)

        # Should sanitize successfully
        assert step_87_result['sanitization_completed'] is True
        assert step_87_result['next_step'] == 'doc_classify'

    @pytest.mark.asyncio
    @patch('app.orchestrators.docs.rag_step_log')
    async def test_step_87_to_88_flow(self, mock_rag_log):
        """Test Step 87 → Step 88 (classify) flow."""
        from app.orchestrators.docs import step_87__doc_security

        extracted_docs = [
            {
                'filename': 'IT12345678901_FPA01.xml',
                'content': b'<?xml version="1.0"?><FatturaElettronica>...</FatturaElettronica>',
                'mime_type': 'application/xml',
                'detected_type': 'xml',
                'potential_category': 'fattura_elettronica'
            }
        ]

        ctx = {
            'extracted_docs': extracted_docs,
            'document_count': 1,
            'request_id': 'test-87-to-88'
        }

        result = await step_87__doc_security(messages=[], ctx=ctx)

        # Should route to Step 88
        assert result['next_step'] == 'doc_classify'
        assert result['sanitization_completed'] is True

        # Context should be ready for Step 88
        assert 'sanitized_docs' in result
        assert len(result['sanitized_docs']) > 0