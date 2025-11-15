"""
Tests for RAG STEP 98 — Convert to ToolMessage facts and spans (RAG.facts.convert.to.toolmessage.facts.and.spans)

This process step converts extracted document facts and provenance into ToolMessage format
for returning to the LLM tool caller. Formats facts and metadata into structured tool response.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep98ToToolResults:
    """Test suite for RAG STEP 98 - Convert to ToolMessage."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_98_converts_facts_to_tool_message(self, mock_rag_log):
        """Test Step 98: Converts document facts to ToolMessage format."""
        from app.orchestrators.facts import step_98__to_tool_results

        # Simulate Step 97 (Provenance) output
        ctx = {
            "facts": [
                {
                    "type": "document_field",
                    "field_name": "amount",
                    "value": "1000.00",
                    "document_type": "fattura",
                    "source_file": "invoice.xml",
                },
                {
                    "type": "document_field",
                    "field_name": "date",
                    "value": "2024-01-15",
                    "document_type": "fattura",
                    "source_file": "invoice.xml",
                },
            ],
            "ledger_entries": [{"timestamp": "2024-01-15T10:00:00Z", "blob_id": "blob123", "filename": "invoice.xml"}],
            "tool_call_id": "call_abc123",
            "request_id": "test-98-convert",
        }

        result = await step_98__to_tool_results(messages=[], ctx=ctx)

        # Should create tool message
        assert "tool_message" in result
        assert result["conversion_successful"] is True

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 98
        assert completed_log["node_label"] == "ToToolResults"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_98_formats_facts_content(self, mock_rag_log):
        """Test Step 98: Formats facts into readable content."""
        from app.orchestrators.facts import step_98__to_tool_results

        ctx = {
            "facts": [
                {"type": "document_field", "field_name": "amount", "value": "500.00", "document_type": "fattura"}
            ],
            "tool_call_id": "call_123",
            "request_id": "test-98-format",
        }

        result = await step_98__to_tool_results(messages=[], ctx=ctx)

        # Should have formatted content
        assert "tool_message_content" in result
        content = result["tool_message_content"]
        assert "amount" in content or "500.00" in content

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_98_includes_provenance_metadata(self, mock_rag_log):
        """Test Step 98: Includes provenance metadata in tool message."""
        from app.orchestrators.facts import step_98__to_tool_results

        ledger = [
            {
                "timestamp": "2024-01-15T10:00:00Z",
                "blob_id": "blob_xyz",
                "filename": "contract.pdf",
                "document_type": "contratto",
            }
        ]

        ctx = {
            "facts": [{"type": "document_text", "value": "Contract text"}],
            "ledger_entries": ledger,
            "tool_call_id": "call_456",
            "request_id": "test-98-provenance",
        }

        result = await step_98__to_tool_results(messages=[], ctx=ctx)

        # Should preserve provenance
        assert "ledger_entries" in result
        assert result["ledger_entries"] == ledger

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_98_handles_empty_facts(self, mock_rag_log):
        """Test Step 98: Handles empty facts gracefully."""
        from app.orchestrators.facts import step_98__to_tool_results

        ctx = {"facts": [], "ledger_entries": [], "tool_call_id": "call_empty", "request_id": "test-98-empty"}

        result = await step_98__to_tool_results(messages=[], ctx=ctx)

        # Should handle empty facts
        assert result["conversion_successful"] is True
        assert "tool_message" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_98_handles_multiple_document_types(self, mock_rag_log):
        """Test Step 98: Handles facts from multiple document types."""
        from app.orchestrators.facts import step_98__to_tool_results

        ctx = {
            "facts": [
                {"type": "document_field", "value": "1000", "document_type": "fattura"},
                {"type": "document_field", "value": "2000", "document_type": "f24"},
                {"type": "document_text", "value": "Contract terms", "document_type": "contratto"},
            ],
            "tool_call_id": "call_multi",
            "request_id": "test-98-multi",
        }

        result = await step_98__to_tool_results(messages=[], ctx=ctx)

        # Should handle multiple types
        assert result["conversion_successful"] is True
        assert result["facts_count"] == 3

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_98_routes_to_tool_results(self, mock_rag_log):
        """Test Step 98: Routes to Step 99 (ToolResults)."""
        from app.orchestrators.facts import step_98__to_tool_results

        ctx = {
            "facts": [{"type": "document_field", "value": "test"}],
            "tool_call_id": "call_route",
            "request_id": "test-98-route",
        }

        result = await step_98__to_tool_results(messages=[], ctx=ctx)

        # Should route to Step 99
        assert result["next_step"] == "tool_results"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_98_preserves_context(self, mock_rag_log):
        """Test Step 98: Preserves context fields for Step 99."""
        from app.orchestrators.facts import step_98__to_tool_results

        ctx = {
            "facts": [{"type": "document_field", "value": "data"}],
            "tool_call_id": "call_ctx",
            "request_id": "test-98-context",
            "user_id": "user123",
            "session_id": "session456",
            "document_count": 2,
            "other_field": "preserved",
        }

        result = await step_98__to_tool_results(messages=[], ctx=ctx)

        # Should preserve all context
        assert result["request_id"] == "test-98-context"
        assert result["user_id"] == "user123"
        assert result["session_id"] == "session456"
        assert result["document_count"] == 2
        assert result["other_field"] == "preserved"


class TestRAGStep98Integration:
    """Integration tests for Step 97 → Step 98 → Step 99 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.docs.rag_step_log")
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_97_to_98_integration(self, mock_facts_log, mock_docs_log):
        """Test Step 97 (Provenance) → Step 98 (ToToolResults) integration."""
        from app.orchestrators.docs import step_97__provenance
        from app.orchestrators.facts import step_98__to_tool_results

        # Step 97: Log provenance
        step_97_ctx = {
            "blob_ids": [
                {
                    "blob_id": "blob_001",
                    "filename": "invoice.xml",
                    "document_type": "fattura",
                    "size": 1024,
                    "encrypted": True,
                }
            ],
            "facts": [
                {
                    "type": "document_field",
                    "field_name": "total_amount",
                    "value": "1500.00",
                    "document_type": "fattura",
                    "source_file": "invoice.xml",
                }
            ],
            "document_count": 1,
            "request_id": "test-integration-97-98",
            "tool_call_id": "call_integration",
        }

        step_97_result = await step_97__provenance(messages=[], ctx=step_97_ctx)

        # Step 98: Convert to tool message
        step_98_result = await step_98__to_tool_results(messages=[], ctx=step_97_result)

        # Should flow correctly
        assert step_97_result["next_step"] == "to_tool_results"
        assert step_97_result["provenance_logged"] is True

        assert step_98_result["next_step"] == "tool_results"
        assert step_98_result["conversion_successful"] is True

        # Should preserve provenance through the chain
        assert "ledger_entries" in step_98_result
        assert len(step_98_result["ledger_entries"]) > 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_98_prepares_for_step_99(self, mock_rag_log):
        """Test Step 98: Prepares output for Step 99 (ToolResults)."""
        from app.orchestrators.facts import step_98__to_tool_results

        ctx = {
            "facts": [
                {"type": "document_field", "field_name": "amount", "value": "2000"},
                {"type": "document_field", "field_name": "date", "value": "2024-01-20"},
            ],
            "ledger_entries": [{"blob_id": "blob_123"}],
            "tool_call_id": "call_final",
            "request_id": "test-98-final",
            "ai_message": MagicMock(),
        }

        result = await step_98__to_tool_results(messages=[], ctx=ctx)

        # Should have everything Step 99 needs
        assert "tool_message" in result
        assert "tool_call_id" in result
        assert result["next_step"] == "tool_results"
        assert "facts" in result
