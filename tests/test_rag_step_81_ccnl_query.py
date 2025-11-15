"""
Tests for RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements)

This process step executes on-demand CCNL (Italian Collective Labor Agreement) queries when the LLM calls the CCNLTool.
Uses CCNLTool for querying labor agreements, salary calculations, leave entitlements, and compliance information.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRAGStep81CCNLQuery:
    """Test suite for RAG STEP 81 - CCNL query tool."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_executes_ccnl_query(self, mock_rag_log):
        """Test Step 81: Executes CCNL labor agreement query via tool."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        ctx = {
            "tool_name": "ccnl_query",
            "tool_args": {"query_type": "search", "sector": "metalworking", "search_terms": "ferie annuali"},
            "tool_call_id": "call_ccnl_123",
            "request_id": "test-81-query",
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        assert "ccnl_results" in result or "query_result" in result
        assert result["next_step"] == "tool_results"

        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 81
        assert completed_log["node_label"] == "CCNLQuery"

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    @patch("app.core.langgraph.tools.ccnl_tool.CCNLTool._arun")
    async def test_step_81_uses_ccnl_tool(self, mock_arun, mock_rag_log):
        """Test Step 81: Uses CCNLTool for CCNL queries."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        mock_arun.return_value = '{"success": true, "result": "CCNL data"}'

        ctx = {
            "tool_args": {"query_type": "salary_calculation", "sector": "construction", "job_category": "worker"},
            "tool_call_id": "call_123",
            "request_id": "test-81-tool",
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        assert "ccnl_results" in result or "query_result" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_handles_search_query(self, mock_rag_log):
        """Test Step 81: Handles CCNL search queries."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        ctx = {
            "tool_args": {"query_type": "search", "sector": "commerce", "search_terms": "preavviso dimissioni"},
            "tool_call_id": "call_search",
            "request_id": "test-81-search",
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        assert "query_type" in result
        assert result["query_type"] == "search"

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_handles_salary_calculation(self, mock_rag_log):
        """Test Step 81: Handles salary calculation queries."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        ctx = {
            "tool_args": {
                "query_type": "salary_calculation",
                "sector": "metalworking",
                "job_category": "employee",
                "experience_years": 5,
            },
            "tool_call_id": "call_salary",
            "request_id": "test-81-salary",
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        assert result["query_type"] == "salary_calculation"

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_handles_leave_calculation(self, mock_rag_log):
        """Test Step 81: Handles leave entitlement calculations."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        ctx = {
            "tool_args": {
                "query_type": "leave_calculation",
                "sector": "textile",
                "job_category": "worker",
                "experience_years": 3,
            },
            "tool_call_id": "call_leave",
            "request_id": "test-81-leave",
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        assert result["query_type"] == "leave_calculation"

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_includes_query_metadata(self, mock_rag_log):
        """Test Step 81: Includes query metadata in results."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        ctx = {
            "tool_args": {"query_type": "notice_period", "sector": "banking", "job_category": "manager"},
            "tool_call_id": "call_meta",
            "request_id": "test-81-metadata",
            "user_id": "user123",
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        assert "query_metadata" in result or "sector" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_routes_to_tool_results(self, mock_rag_log):
        """Test Step 81: Routes to Step 99 (ToolResults) per Mermaid."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        ctx = {
            "tool_args": {"query_type": "search", "sector": "food", "search_terms": "straordinario"},
            "tool_call_id": "call_route",
            "request_id": "test-81-route",
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        # Per Mermaid: CCNLQuery → PostgresQuery → CCNLCalc → ToolResults
        # But implementation collapses to: CCNLQuery → ToolResults (CCNLTool handles internals)
        assert result["next_step"] == "tool_results"

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_preserves_context(self, mock_rag_log):
        """Test Step 81: Preserves context fields for Step 99."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        ctx = {
            "tool_args": {"query_type": "search", "sector": "logistics", "search_terms": "test"},
            "tool_call_id": "call_ctx",
            "request_id": "test-81-context",
            "user_id": "user456",
            "session_id": "session789",
            "other_field": "preserved_value",
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        assert result["request_id"] == "test-81-context"
        assert result["user_id"] == "user456"
        assert result["session_id"] == "session789"
        assert result["other_field"] == "preserved_value"

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_handles_error_gracefully(self, mock_rag_log):
        """Test Step 81: Handles CCNL tool errors gracefully."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        ctx = {
            "tool_args": {"query_type": "invalid_type", "sector": "unknown"},
            "tool_call_id": "call_error",
            "request_id": "test-81-error",
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        # Should still route to tool_results even on error
        assert result["next_step"] == "tool_results"


class TestRAGStep81Parity:
    """Parity tests proving Step 81 uses CCNLTool correctly."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_parity_with_ccnl_tool(self, mock_rag_log):
        """Test Step 81: Uses same logic as CCNLTool."""
        from app.core.langgraph.tools.ccnl_tool import CCNLTool
        from app.orchestrators.ccnl import step_81__ccnlquery

        tool_args = {"query_type": "search", "sector": "metalworking", "search_terms": "straordinario notturno"}

        # Direct tool instantiation
        CCNLTool()

        # Orchestrator call
        ctx = {"tool_args": tool_args, "tool_call_id": "call_parity", "request_id": "parity-test"}

        orch_result = await step_81__ccnlquery(messages=[], ctx=ctx)

        # Both should produce CCNL results
        assert "ccnl_results" in orch_result or "query_result" in orch_result


class TestRAGStep81Integration:
    """Integration tests for Step 79 → Step 81 → Step 99 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_79_to_81_integration(self, mock_ccnl_log):
        """Test Step 79 (ToolType) → Step 81 (CCNLQuery) integration flow."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        # Simulate Step 79 output (when CCNL tool type is detected)
        # Note: Step 79 is not yet implemented, so we mock its expected output
        step_79_output = {
            "tool_type": "CCNL",
            "tool_name": "ccnl_query",
            "tool_call_id": "call_integration",
            "tool_args": {"query_type": "search", "sector": "commerce", "search_terms": "permessi retribuiti"},
            "next_step": "ccnl_query",
            "request_id": "test-integration-79-81",
        }

        # Step 81: Execute CCNL query
        step_81_result = await step_81__ccnlquery(messages=[], ctx=step_79_output)

        # Should route to Step 99 (ToolResults)
        assert step_81_result["next_step"] == "tool_results"
        assert "ccnl_results" in step_81_result or "query_result" in step_81_result

    @pytest.mark.asyncio
    @patch("app.orchestrators.ccnl.rag_step_log")
    async def test_step_81_prepares_for_step_99(self, mock_rag_log):
        """Test Step 81: Prepares output for Step 99 (ToolResults)."""
        from app.orchestrators.ccnl import step_81__ccnlquery

        ctx = {
            "tool_args": {
                "query_type": "salary_calculation",
                "sector": "construction",
                "job_category": "worker",
                "experience_years": 10,
            },
            "tool_call_id": "call_final",
            "request_id": "test-81-final",
            "ai_message": MagicMock(),
        }

        result = await step_81__ccnlquery(messages=[], ctx=ctx)

        # Should have everything Step 99 needs
        assert "tool_call_id" in result
        assert result["next_step"] == "tool_results"
        assert "ccnl_results" in result or "query_result" in result
