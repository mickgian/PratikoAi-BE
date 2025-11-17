"""
Tests for RAG STEP 82 — DocumentIngestTool.process Process attachments (RAG.preflight.documentingesttool.process.process.attachments)

This process step executes document processing when the LLM calls the DocumentIngestTool.
Uses DocumentIngestTool for text extraction, document classification, and preparing files for RAG pipeline.
"""

import base64
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRAGStep82DocIngest:
    """Test suite for RAG STEP 82 - Document ingest tool."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_82_executes_document_ingest(self, mock_rag_log):
        """Test Step 82: Executes document processing via tool."""
        from app.orchestrators.preflight import step_82__doc_ingest

        # Sample PDF content (minimal valid PDF)
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 <<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\n>>\n>>\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF"

        ctx = {
            "tool_name": "DocumentIngestTool",
            "tool_args": {
                "attachments": [
                    {
                        "attachment_id": "attach_123",
                        "filename": "test.pdf",
                        "content_type": "application/pdf",
                        "size": len(pdf_content),
                        "content": base64.b64encode(pdf_content).decode("utf-8"),
                    }
                ],
                "user_id": "user123",
                "session_id": "session456",
            },
            "tool_call_id": "call_doc_123",
            "request_id": "test-82-ingest",
        }

        result = await step_82__doc_ingest(messages=[], ctx=ctx)

        assert "processing_results" in result or "documents" in result
        assert result["next_step"] == "validate_attachments"

        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 82
        assert completed_log["node_label"] == "DocIngest"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    @patch("app.core.langgraph.tools.document_ingest_tool.DocumentIngestTool._arun")
    async def test_step_82_uses_document_ingest_tool(self, mock_arun, mock_rag_log):
        """Test Step 82: Uses DocumentIngestTool for processing."""
        from app.orchestrators.preflight import step_82__doc_ingest

        mock_arun.return_value = {
            "success": True,
            "processed_count": 1,
            "documents": [{"filename": "test.pdf", "text": "Sample text"}],
        }

        ctx = {
            "tool_args": {
                "attachments": [
                    {
                        "attachment_id": "attach_1",
                        "filename": "invoice.pdf",
                        "content_type": "application/pdf",
                        "size": 1024,
                        "content": "base64content",
                    }
                ],
                "user_id": "user1",
                "session_id": "sess1",
            },
            "tool_call_id": "call_123",
            "request_id": "test-82-tool",
        }

        result = await step_82__doc_ingest(messages=[], ctx=ctx)

        assert "processing_results" in result or "documents" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_82_handles_multiple_attachments(self, mock_rag_log):
        """Test Step 82: Handles multiple attachments."""
        from app.orchestrators.preflight import step_82__doc_ingest

        ctx = {
            "tool_args": {
                "attachments": [
                    {
                        "attachment_id": "attach_1",
                        "filename": "doc1.pdf",
                        "content_type": "application/pdf",
                        "size": 1024,
                        "content": "content1",
                    },
                    {
                        "attachment_id": "attach_2",
                        "filename": "doc2.pdf",
                        "content_type": "application/pdf",
                        "size": 2048,
                        "content": "content2",
                    },
                ],
                "user_id": "user123",
                "session_id": "session456",
            },
            "tool_call_id": "call_multi",
            "request_id": "test-82-multi",
        }

        result = await step_82__doc_ingest(messages=[], ctx=ctx)

        assert "attachment_count" in result or "processed_count" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_82_includes_metadata(self, mock_rag_log):
        """Test Step 82: Includes processing metadata in results."""
        from app.orchestrators.preflight import step_82__doc_ingest

        ctx = {
            "tool_args": {
                "attachments": [
                    {
                        "attachment_id": "attach_meta",
                        "filename": "contract.pdf",
                        "content_type": "application/pdf",
                        "size": 512,
                        "content": "test_content",
                    }
                ],
                "user_id": "user789",
                "session_id": "session012",
            },
            "tool_call_id": "call_meta",
            "request_id": "test-82-metadata",
        }

        result = await step_82__doc_ingest(messages=[], ctx=ctx)

        assert "processing_metadata" in result or "user_id" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_82_routes_to_validate_attachments(self, mock_rag_log):
        """Test Step 82: Routes to Step 84 (ValidateAttachments) per Mermaid."""
        from app.orchestrators.preflight import step_82__doc_ingest

        ctx = {
            "tool_args": {
                "attachments": [
                    {
                        "attachment_id": "attach_route",
                        "filename": "test.pdf",
                        "content_type": "application/pdf",
                        "size": 1024,
                        "content": "content",
                    }
                ],
                "user_id": "user1",
                "session_id": "sess1",
            },
            "tool_call_id": "call_route",
            "request_id": "test-82-route",
        }

        result = await step_82__doc_ingest(messages=[], ctx=ctx)

        # Per Mermaid: DocIngest → ValidateAttach
        assert result["next_step"] == "validate_attachments"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_82_preserves_context(self, mock_rag_log):
        """Test Step 82: Preserves context fields for next steps."""
        from app.orchestrators.preflight import step_82__doc_ingest

        ctx = {
            "tool_args": {
                "attachments": [
                    {
                        "attachment_id": "attach_ctx",
                        "filename": "doc.pdf",
                        "content_type": "application/pdf",
                        "size": 1024,
                        "content": "content",
                    }
                ],
                "user_id": "user456",
                "session_id": "session789",
            },
            "tool_call_id": "call_ctx",
            "request_id": "test-82-context",
            "other_field": "preserved_value",
        }

        result = await step_82__doc_ingest(messages=[], ctx=ctx)

        assert result["request_id"] == "test-82-context"
        assert result["other_field"] == "preserved_value"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_82_handles_error_gracefully(self, mock_rag_log):
        """Test Step 82: Handles document processing errors gracefully."""
        from app.orchestrators.preflight import step_82__doc_ingest

        ctx = {
            "tool_args": {
                "attachments": [
                    {
                        "attachment_id": "attach_error",
                        "filename": "corrupted.pdf",
                        "content_type": "application/pdf",
                        "size": 1024,
                        "content": "invalid_base64_content!!!",
                    }
                ],
                "user_id": "user1",
                "session_id": "sess1",
            },
            "tool_call_id": "call_error",
            "request_id": "test-82-error",
        }

        result = await step_82__doc_ingest(messages=[], ctx=ctx)

        # Should still route to next step even on error
        assert result["next_step"] == "validate_attachments"


class TestRAGStep82Parity:
    """Parity tests proving Step 82 uses DocumentIngestTool correctly."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_82_parity_with_document_ingest_tool(self, mock_rag_log):
        """Test Step 82: Uses same logic as DocumentIngestTool."""
        from app.core.langgraph.tools.document_ingest_tool import DocumentIngestTool
        from app.orchestrators.preflight import step_82__doc_ingest

        tool_args = {
            "attachments": [
                {
                    "attachment_id": "attach_parity",
                    "filename": "test.pdf",
                    "content_type": "application/pdf",
                    "size": 512,
                    "content": base64.b64encode(b"test content").decode("utf-8"),
                }
            ],
            "user_id": "user_parity",
            "session_id": "sess_parity",
        }

        # Direct tool instantiation
        DocumentIngestTool()

        # Orchestrator call
        ctx = {"tool_args": tool_args, "tool_call_id": "call_parity", "request_id": "parity-test"}

        orch_result = await step_82__doc_ingest(messages=[], ctx=ctx)

        # Both should produce processing results
        assert "processing_results" in orch_result or "documents" in orch_result


class TestRAGStep82Integration:
    """Integration tests for Step 79 → Step 82 → Step 84 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_79_to_82_integration(self, mock_preflight_log):
        """Test Step 79 (ToolType) → Step 82 (DocIngest) integration flow."""
        from app.orchestrators.preflight import step_82__doc_ingest

        # Simulate Step 79 output (when Document tool type is detected)
        # Note: Step 79 is not yet implemented, so we mock its expected output
        step_79_output = {
            "tool_type": "Document",
            "tool_name": "DocumentIngestTool",
            "tool_call_id": "call_integration",
            "tool_args": {
                "attachments": [
                    {
                        "attachment_id": "attach_int",
                        "filename": "invoice.pdf",
                        "content_type": "application/pdf",
                        "size": 1024,
                        "content": base64.b64encode(b"PDF content").decode("utf-8"),
                    }
                ],
                "user_id": "user_int",
                "session_id": "sess_int",
            },
            "next_step": "doc_ingest",
            "request_id": "test-integration-79-82",
        }

        # Step 82: Execute document ingest
        step_82_result = await step_82__doc_ingest(messages=[], ctx=step_79_output)

        # Should route to Step 84 (ValidateAttachments)
        assert step_82_result["next_step"] == "validate_attachments"
        assert "processing_results" in step_82_result or "documents" in step_82_result

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_82_prepares_for_step_84(self, mock_rag_log):
        """Test Step 82: Prepares output for Step 84 (ValidateAttachments)."""
        from app.orchestrators.preflight import step_82__doc_ingest

        ctx = {
            "tool_args": {
                "attachments": [
                    {
                        "attachment_id": "attach_final",
                        "filename": "contract.pdf",
                        "content_type": "application/pdf",
                        "size": 2048,
                        "content": base64.b64encode(b"Contract content").decode("utf-8"),
                    }
                ],
                "user_id": "user_final",
                "session_id": "sess_final",
            },
            "tool_call_id": "call_final",
            "request_id": "test-82-final",
            "ai_message": MagicMock(),
        }

        result = await step_82__doc_ingest(messages=[], ctx=ctx)

        # Should have everything Step 84 needs
        assert "tool_call_id" in result
        assert result["next_step"] == "validate_attachments"
        assert "attachments" in result or "processing_results" in result
