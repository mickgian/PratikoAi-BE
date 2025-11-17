"""
Tests for RAG STEP 75 — Response has tool_calls? (RAG.response.response.has.tool.calls)

This decision step checks if the LLM response contains tool calls.
Routes to tool call conversion (Step 76) if present, or simple message conversion (Step 77) if not.
"""

from unittest.mock import patch

import pytest

from app.core.llm.base import LLMResponse


class TestRAGStep75ToolCheck:
    """Test suite for RAG STEP 75 - Response has tool_calls decision."""

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_75_response_has_tool_calls(self, mock_rag_log):
        """Test Step 75: Response has tool calls - routes to Step 76."""
        from app.orchestrators.response import step_75__tool_check

        # Create response with tool calls
        tool_calls = [{"name": "search_knowledge_base", "args": {"query": "tax rates"}, "id": "call_123"}]

        llm_response = LLMResponse(
            content="I'll search for tax rates information.",
            tool_calls=tool_calls,
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai",
        )

        ctx = {"llm_response": llm_response, "request_id": "test-75-with-tools"}

        result = await step_75__tool_check(messages=[], ctx=ctx)

        # Verify decision result
        assert isinstance(result, dict)
        assert result["has_tool_calls"] is True
        assert result["tool_call_count"] == 1
        assert result["next_step"] == "convert_with_tool_calls"  # Routes to Step 76
        assert result["llm_response"] == llm_response
        assert result["tool_calls"] == tool_calls

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 75
        assert completed_log["node_label"] == "ToolCheck"
        assert completed_log["has_tool_calls"] is True
        assert completed_log["decision"] == "with_tools"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_75_response_no_tool_calls(self, mock_rag_log):
        """Test Step 75: Response has no tool calls - routes to Step 77."""
        from app.orchestrators.response import step_75__tool_check

        # Create response without tool calls
        llm_response = LLMResponse(
            content="Here's the answer to your question...",
            tool_calls=[],  # Empty list
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai",
        )

        ctx = {"llm_response": llm_response, "request_id": "test-75-no-tools"}

        result = await step_75__tool_check(messages=[], ctx=ctx)

        # Verify routes to simple message
        assert result["has_tool_calls"] is False
        assert result["tool_call_count"] == 0
        assert result["next_step"] == "convert_simple_message"  # Routes to Step 77
        assert result["tool_calls"] == []

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_75_response_none_tool_calls(self, mock_rag_log):
        """Test Step 75: Response with None tool_calls."""
        from app.orchestrators.response import step_75__tool_check

        llm_response = LLMResponse(
            content="Simple response",
            tool_calls=None,  # None instead of empty list
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai",
        )

        ctx = {"llm_response": llm_response, "request_id": "test-75-none-tools"}

        result = await step_75__tool_check(messages=[], ctx=ctx)

        # Should treat None as no tool calls
        assert result["has_tool_calls"] is False
        assert result["tool_call_count"] == 0
        assert result["next_step"] == "convert_simple_message"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_75_multiple_tool_calls(self, mock_rag_log):
        """Test Step 75: Response with multiple tool calls."""
        from app.orchestrators.response import step_75__tool_check

        tool_calls = [
            {"name": "search_kb", "args": {"query": "tax"}, "id": "call_1"},
            {"name": "search_faq", "args": {"query": "deduction"}, "id": "call_2"},
            {"name": "ccnl_query", "args": {"sector": "retail"}, "id": "call_3"},
        ]

        llm_response = LLMResponse(
            content="I'll search multiple sources.",
            tool_calls=tool_calls,
            cost_estimate=0.002,
            model="gpt-4",
            provider="openai",
        )

        ctx = {"llm_response": llm_response, "request_id": "test-75-multiple"}

        result = await step_75__tool_check(messages=[], ctx=ctx)

        assert result["has_tool_calls"] is True
        assert result["tool_call_count"] == 3
        assert result["next_step"] == "convert_with_tool_calls"
        assert len(result["tool_calls"]) == 3

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_75_tool_call_metadata(self, mock_rag_log):
        """Test Step 75: Captures tool call metadata."""
        from app.orchestrators.response import step_75__tool_check

        tool_calls = [
            {"name": "search_knowledge_base", "args": {"query": "contract law", "limit": 5}, "id": "call_abc123"}
        ]

        llm_response = LLMResponse(
            content="Searching for contract law information...",
            tool_calls=tool_calls,
            cost_estimate=0.0015,
            model="gpt-4-turbo",
            provider="openai",
        )

        ctx = {
            "llm_response": llm_response,
            "provider": "openai",
            "model": "gpt-4-turbo",
            "request_id": "test-75-metadata",
        }

        result = await step_75__tool_check(messages=[], ctx=ctx)

        # Verify metadata captured
        assert result["has_tool_calls"] is True
        assert result["tool_names"] == ["search_knowledge_base"]
        assert "search_knowledge_base" in result["tool_names"]

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_75_missing_response(self, mock_rag_log):
        """Test Step 75: Handle missing LLM response gracefully."""
        from app.orchestrators.response import step_75__tool_check

        ctx = {"llm_response": None, "request_id": "test-75-missing"}

        result = await step_75__tool_check(messages=[], ctx=ctx)

        # Should treat missing response as no tool calls
        assert result["has_tool_calls"] is False
        assert result["tool_call_count"] == 0
        assert result["next_step"] == "convert_simple_message"


class TestRAGStep75Parity:
    """Parity tests proving Step 75 preserves existing logic."""

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_75_parity_tool_calls_check(self, mock_rag_log):
        """Test Step 75: Parity with existing tool_calls check."""
        from app.orchestrators.response import step_75__tool_check

        # Original logic from graph.py:742
        # if response.tool_calls:
        tool_calls = [{"name": "test", "args": {}, "id": "1"}]

        llm_response = LLMResponse(
            content="Test", tool_calls=tool_calls, cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        ctx = {"llm_response": llm_response, "request_id": "test-parity-check"}

        result = await step_75__tool_check(messages=[], ctx=ctx)

        # Original condition: if response.tool_calls
        original_has_tools = bool(llm_response.tool_calls)

        # Verify identical decision
        assert result["has_tool_calls"] == original_has_tools
        assert result["has_tool_calls"] is True

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_75_parity_no_tool_calls(self, mock_rag_log):
        """Test Step 75: Parity for no tool calls case."""
        from app.orchestrators.response import step_75__tool_check

        # Original: else branch when no tool_calls
        llm_response = LLMResponse(
            content="Simple response", tool_calls=[], cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        ctx = {"llm_response": llm_response, "request_id": "test-parity-no-tools"}

        result = await step_75__tool_check(messages=[], ctx=ctx)

        # Original condition: not response.tool_calls
        original_has_tools = bool(llm_response.tool_calls)

        assert result["has_tool_calls"] == original_has_tools
        assert result["has_tool_calls"] is False


class TestRAGStep75Integration:
    """Integration tests for Step 67 → Step 75 → Step 76/77 flow."""

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_67_to_75_with_tools_integration(self, mock_rag_log):
        """Test Step 67 (success) → Step 75 (has tools) → Step 76 flow."""
        from app.orchestrators.llm import step_67__llmsuccess
        from app.orchestrators.response import step_75__tool_check

        # Step 67: LLM call succeeded with tool calls
        tool_calls = [{"name": "search", "args": {"q": "test"}, "id": "c1"}]

        llm_response = LLMResponse(
            content="Searching...", tool_calls=tool_calls, cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        step_67_ctx = {"llm_response": llm_response, "request_id": "test-integration-67-75-tools"}

        step_67_result = await step_67__llmsuccess(messages=[], ctx=step_67_ctx)

        # Should indicate success
        assert step_67_result["llm_success"] is True
        assert step_67_result["next_step"] == "cache_response"

        # Step 75: Check for tool calls
        step_75_ctx = {"llm_response": step_67_result["llm_response"], "request_id": step_67_result["request_id"]}

        step_75_result = await step_75__tool_check(messages=[], ctx=step_75_ctx)

        # Should detect tool calls and route to Step 76
        assert step_75_result["has_tool_calls"] is True
        assert step_75_result["next_step"] == "convert_with_tool_calls"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_67_to_75_no_tools_integration(self, mock_rag_log):
        """Test Step 67 (success) → Step 75 (no tools) → Step 77 flow."""
        from app.orchestrators.llm import step_67__llmsuccess
        from app.orchestrators.response import step_75__tool_check

        # Step 67: LLM call succeeded without tool calls
        llm_response = LLMResponse(
            content="Here's your answer...", tool_calls=[], cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        step_67_ctx = {"llm_response": llm_response, "request_id": "test-integration-67-75-no-tools"}

        step_67_result = await step_67__llmsuccess(messages=[], ctx=step_67_ctx)

        # Should indicate success
        assert step_67_result["llm_success"] is True

        # Step 75: Check for tool calls
        step_75_ctx = {"llm_response": step_67_result["llm_response"], "request_id": step_67_result["request_id"]}

        step_75_result = await step_75__tool_check(messages=[], ctx=step_75_ctx)

        # Should detect no tool calls and route to Step 77
        assert step_75_result["has_tool_calls"] is False
        assert step_75_result["next_step"] == "convert_simple_message"
