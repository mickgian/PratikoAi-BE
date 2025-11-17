"""
Tests for RAG STEP 76 — Convert to AIMessage with tool_calls (RAG.platform.convert.to.aimessage.with.tool.calls)

This process step converts an LLM response with tool calls into a LangChain AIMessage object
with tool_calls attached, preparing it for tool execution.
"""

from unittest.mock import patch

import pytest

from app.core.llm.base import LLMResponse


class TestRAGStep76ConvertAIMsg:
    """Test suite for RAG STEP 76 - Convert to AIMessage with tool_calls."""

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_76_convert_with_single_tool_call(self, mock_rag_log):
        """Test Step 76: Convert response with single tool call to AIMessage."""
        from app.orchestrators.platform import step_76__convert_aimsg

        tool_calls = [{"name": "search_knowledge_base", "args": {"query": "tax rates"}, "id": "call_123"}]

        llm_response = LLMResponse(
            content="I'll search for tax rates information.",
            tool_calls=tool_calls,
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai",
        )

        ctx = {"llm_response": llm_response, "request_id": "test-76-single-tool"}

        result = await step_76__convert_aimsg(messages=[], ctx=ctx)

        # Verify conversion
        assert isinstance(result, dict)
        assert result["conversion_successful"] is True
        assert result["ai_message"] is not None
        assert result["message_type"] == "AIMessage"
        assert result["has_tool_calls"] is True
        assert result["tool_call_count"] == 1

        # Verify AIMessage structure
        ai_message = result["ai_message"]
        assert ai_message.content == "I'll search for tax rates information."
        assert hasattr(ai_message, "tool_calls")
        assert len(ai_message.tool_calls) == 1

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 76
        assert completed_log["node_label"] == "ConvertAIMsg"
        assert completed_log["conversion_successful"] is True

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_76_convert_with_multiple_tool_calls(self, mock_rag_log):
        """Test Step 76: Convert response with multiple tool calls."""
        from app.orchestrators.platform import step_76__convert_aimsg

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

        ctx = {"llm_response": llm_response, "request_id": "test-76-multiple"}

        result = await step_76__convert_aimsg(messages=[], ctx=ctx)

        # Verify multiple tool calls
        assert result["conversion_successful"] is True
        assert result["tool_call_count"] == 3
        assert len(result["ai_message"].tool_calls) == 3

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_76_preserves_content(self, mock_rag_log):
        """Test Step 76: Preserves response content in AIMessage."""
        from app.orchestrators.platform import step_76__convert_aimsg

        content = "Let me search the knowledge base for detailed information about Italian tax regulations."
        tool_calls = [{"name": "kb_search", "args": {"q": "tax"}, "id": "c1"}]

        llm_response = LLMResponse(
            content=content, tool_calls=tool_calls, cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        ctx = {"llm_response": llm_response, "request_id": "test-76-content"}

        result = await step_76__convert_aimsg(messages=[], ctx=ctx)

        # Verify content preservation
        assert result["conversion_successful"] is True
        assert result["ai_message"].content == content

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_76_tool_call_structure(self, mock_rag_log):
        """Test Step 76: Preserves tool call structure."""
        from app.orchestrators.platform import step_76__convert_aimsg

        tool_calls = [
            {
                "name": "search_knowledge_base",
                "args": {"query": "contract law", "limit": 5, "filters": {"type": "legal"}},
                "id": "call_abc123",
            }
        ]

        llm_response = LLMResponse(
            content="Searching...", tool_calls=tool_calls, cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        ctx = {"llm_response": llm_response, "request_id": "test-76-structure"}

        result = await step_76__convert_aimsg(messages=[], ctx=ctx)

        # Verify tool call structure preserved
        ai_message = result["ai_message"]
        assert len(ai_message.tool_calls) == 1
        tool_call = ai_message.tool_calls[0]

        # Check structure (dict or object)
        if isinstance(tool_call, dict):
            assert tool_call["name"] == "search_knowledge_base"
            assert tool_call["args"]["query"] == "contract law"
            assert tool_call["id"] == "call_abc123"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_76_routes_to_tool_execution(self, mock_rag_log):
        """Test Step 76: Routes to tool execution step."""
        from app.orchestrators.platform import step_76__convert_aimsg

        tool_calls = [{"name": "test", "args": {}, "id": "1"}]

        llm_response = LLMResponse(
            content="Test", tool_calls=tool_calls, cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        ctx = {"llm_response": llm_response, "request_id": "test-76-route"}

        result = await step_76__convert_aimsg(messages=[], ctx=ctx)

        # Should route to tool execution (Step 78)
        assert result["conversion_successful"] is True
        assert result["next_step"] == "execute_tools"


class TestRAGStep76Parity:
    """Parity tests proving Step 76 preserves existing conversion logic."""

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_76_parity_aimessage_creation(self, mock_rag_log):
        """Test Step 76: Parity with existing AIMessage creation."""
        from app.orchestrators.platform import step_76__convert_aimsg

        # Original logic from graph.py:745-748
        # AIMessage(content=response.content, tool_calls=response.tool_calls)
        content = "Test content"
        tool_calls = [{"name": "test_tool", "args": {"x": 1}, "id": "t1"}]

        llm_response = LLMResponse(
            content=content, tool_calls=tool_calls, cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        ctx = {"llm_response": llm_response, "request_id": "test-parity"}

        result = await step_76__convert_aimsg(messages=[], ctx=ctx)

        # Original: AIMessage(content=..., tool_calls=...)
        # Our result should match
        ai_message = result["ai_message"]
        assert ai_message.content == content
        assert hasattr(ai_message, "tool_calls")
        assert len(ai_message.tool_calls) == len(tool_calls)

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_76_parity_langchain_import(self, mock_rag_log):
        """Test Step 76: Uses LangChain AIMessage."""
        from langchain_core.messages import AIMessage

        from app.orchestrators.platform import step_76__convert_aimsg

        tool_calls = [{"name": "test", "args": {}, "id": "1"}]

        llm_response = LLMResponse(
            content="Test", tool_calls=tool_calls, cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        ctx = {"llm_response": llm_response, "request_id": "test-parity-import"}

        result = await step_76__convert_aimsg(messages=[], ctx=ctx)

        # Should create LangChain AIMessage instance
        assert isinstance(result["ai_message"], AIMessage)


class TestRAGStep76Integration:
    """Integration tests for Step 75 → Step 76 → Step 78 flow."""

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_75_to_76_integration(self, mock_rag_log):
        """Test Step 75 (has tools) → Step 76 (convert) integration."""
        from app.orchestrators.platform import step_76__convert_aimsg
        from app.orchestrators.response import step_75__tool_check

        # Step 75: Check for tool calls
        tool_calls = [{"name": "search", "args": {"q": "test"}, "id": "c1"}]

        llm_response = LLMResponse(
            content="Searching...", tool_calls=tool_calls, cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        step_75_ctx = {"llm_response": llm_response, "request_id": "test-integration-75-76"}

        step_75_result = await step_75__tool_check(messages=[], ctx=step_75_ctx)

        # Should detect tool calls
        assert step_75_result["has_tool_calls"] is True
        assert step_75_result["next_step"] == "convert_with_tool_calls"

        # Step 76: Convert to AIMessage
        step_76_ctx = {
            "llm_response": step_75_result["llm_response"],
            "tool_calls": step_75_result["tool_calls"],
            "request_id": step_75_result["request_id"],
        }

        step_76_result = await step_76__convert_aimsg(messages=[], ctx=step_76_ctx)

        # Should convert successfully
        assert step_76_result["conversion_successful"] is True
        assert step_76_result["has_tool_calls"] is True
        assert step_76_result["next_step"] == "execute_tools"

    @pytest.mark.asyncio
    @patch("app.observability.rag_logging.rag_step_log")
    async def test_step_76_prepares_for_tool_execution(self, mock_rag_log):
        """Test Step 76: Prepares AIMessage for tool execution."""
        from app.orchestrators.platform import step_76__convert_aimsg

        tool_calls = [{"name": "tool1", "args": {"x": 1}, "id": "t1"}, {"name": "tool2", "args": {"y": 2}, "id": "t2"}]

        llm_response = LLMResponse(
            content="Executing tools...", tool_calls=tool_calls, cost_estimate=0.001, model="gpt-4", provider="openai"
        )

        ctx = {
            "llm_response": llm_response,
            "messages": [{"role": "user", "content": "test"}],
            "request_id": "test-76-prep",
        }

        result = await step_76__convert_aimsg(messages=[], ctx=ctx)

        # Should prepare for Step 78 (tool execution)
        assert result["conversion_successful"] is True
        assert result["ai_message"] is not None
        assert result["next_step"] == "execute_tools"

        # Context should be ready for tool execution
        assert "ai_message" in result
        assert "tool_call_count" in result
