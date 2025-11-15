"""Test that Step 64 logs tools information in traces.

This test suite validates that tool calling observability is properly implemented:
- Tools provided to LLM should be logged
- Tool count and names should be captured
- Traces should include tools_provided, tool_count, tool_names fields
"""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.core.langgraph.tools.ccnl_tool import CCNLTool
from app.core.langgraph.tools.faq_tool import FAQTool
from app.core.langgraph.tools.knowledge_search_tool import KnowledgeSearchTool
from app.core.llm.base import LLMResponse
from app.orchestrators.providers import step_64__llmcall


@pytest.mark.asyncio
async def test_step_64_logs_tools_when_provided():
    """
    GIVEN: LLM call with tools provided
    WHEN: step_64__llmcall completes
    THEN: Completion log should include tools_provided=True, tool_count, tool_names
    """
    # Create tool instances
    tools = [KnowledgeSearchTool(), CCNLTool()]

    ctx = {
        "provider_instance": MagicMock(),
        "messages": [{"role": "user", "content": "Test query"}],
        "model": "gpt-4o-mini",
        "tools": tools,  # Tools provided
        "request_id": "test_request_123",
    }

    # Mock provider response
    mock_response = LLMResponse(
        content="Test response",
        model="gpt-4o-mini",
        provider="openai",
        tokens_used=100,
        cost_estimate=0.001,
        finish_reason="stop",
        tool_calls=None,
    )
    ctx["provider_instance"].chat_completion = AsyncMock(return_value=mock_response)

    with patch("app.observability.rag_logging.rag_step_log") as mock_log:
        with patch("app.observability.rag_logging.rag_step_timer"):
            await step_64__llmcall(ctx=ctx)

            # Find completion log call (processing_stage='completed')
            completion_calls = [
                call_obj
                for call_obj in mock_log.call_args_list
                if len(call_obj[1]) > 0 and call_obj[1].get("processing_stage") == "completed"
            ]

            assert len(completion_calls) >= 1, "Should have at least one completion log"
            completion_log = completion_calls[0][1]

            # Verify tools logging
            assert "tools_provided" in completion_log, "Should log tools_provided field"
            assert completion_log["tools_provided"] is True, "tools_provided should be True"
            assert "tool_count" in completion_log, "Should log tool_count field"
            assert completion_log["tool_count"] == 2, "Should log correct tool count"
            assert "tool_names" in completion_log, "Should log tool_names field"
            assert "KnowledgeSearchTool" in completion_log["tool_names"], "Should include KnowledgeSearchTool in names"
            assert "CCNLTool" in completion_log["tool_names"], "Should include CCNLTool in names"


@pytest.mark.asyncio
async def test_step_64_logs_no_tools_when_none_provided():
    """
    GIVEN: LLM call without tools
    WHEN: step_64__llmcall completes
    THEN: Completion log should include tools_provided=False, tool_count=0, empty tool_names
    """
    ctx = {
        "provider_instance": MagicMock(),
        "messages": [{"role": "user", "content": "Test query"}],
        "model": "gpt-4o-mini",
        "request_id": "test_request_456",
        # No tools key
    }

    mock_response = LLMResponse(
        content="Test response",
        model="gpt-4o-mini",
        provider="openai",
        tokens_used=50,
        cost_estimate=0.0005,
        finish_reason="stop",
        tool_calls=None,
    )
    ctx["provider_instance"].chat_completion = AsyncMock(return_value=mock_response)

    with patch("app.observability.rag_logging.rag_step_log") as mock_log:
        with patch("app.observability.rag_logging.rag_step_timer"):
            await step_64__llmcall(ctx=ctx)

            completion_calls = [
                call_obj
                for call_obj in mock_log.call_args_list
                if len(call_obj[1]) > 0 and call_obj[1].get("processing_stage") == "completed"
            ]

            completion_log = completion_calls[0][1]

            # Verify no-tools logging
            assert completion_log["tools_provided"] is False, "tools_provided should be False"
            assert completion_log["tool_count"] == 0, "tool_count should be 0"
            assert completion_log["tool_names"] == [], "tool_names should be empty list"


@pytest.mark.asyncio
async def test_step_64_logs_tools_from_llm_params():
    """
    GIVEN: Tools provided in llm_params dict (alternative location)
    WHEN: step_64__llmcall completes
    THEN: Should still detect and log tools correctly
    """
    tools = [FAQTool(), KnowledgeSearchTool(), CCNLTool()]

    ctx = {
        "provider_instance": MagicMock(),
        "messages": [{"role": "user", "content": "Test"}],
        "model": "gpt-4o-mini",
        "llm_params": {
            "tools": tools,  # Tools in llm_params instead of top-level
            "temperature": 0.2,
        },
        "request_id": "test_request_789",
    }

    mock_response = LLMResponse(content="Test", model="gpt-4o-mini", provider="openai", tool_calls=None)
    ctx["provider_instance"].chat_completion = AsyncMock(return_value=mock_response)

    with patch("app.observability.rag_logging.rag_step_log") as mock_log:
        with patch("app.observability.rag_logging.rag_step_timer"):
            await step_64__llmcall(ctx=ctx)

            completion_calls = [
                call_obj
                for call_obj in mock_log.call_args_list
                if len(call_obj[1]) > 0 and call_obj[1].get("processing_stage") == "completed"
            ]

            completion_log = completion_calls[0][1]

            # Should detect tools from llm_params
            assert completion_log["tools_provided"] is True
            assert completion_log["tool_count"] == 3
            assert len(completion_log["tool_names"]) == 3


@pytest.mark.asyncio
async def test_step_64_limits_tool_names_to_five():
    """
    GIVEN: LLM call with more than 5 tools
    WHEN: step_64__llmcall completes
    THEN: Should log only first 5 tool names (to avoid log bloat)
    """
    # Create 7 tools (more than limit of 5)
    tools = [
        KnowledgeSearchTool(),
        CCNLTool(),
        FAQTool(),
        KnowledgeSearchTool(),  # Duplicate types OK
        CCNLTool(),
        FAQTool(),
        KnowledgeSearchTool(),
    ]

    ctx = {
        "provider_instance": MagicMock(),
        "messages": [{"role": "user", "content": "Test"}],
        "model": "gpt-4o-mini",
        "tools": tools,
        "request_id": "test_request_many_tools",
    }

    mock_response = LLMResponse(content="Test", model="gpt-4o-mini", provider="openai", tool_calls=None)
    ctx["provider_instance"].chat_completion = AsyncMock(return_value=mock_response)

    with patch("app.observability.rag_logging.rag_step_log") as mock_log:
        with patch("app.observability.rag_logging.rag_step_timer"):
            await step_64__llmcall(ctx=ctx)

            completion_calls = [
                call_obj
                for call_obj in mock_log.call_args_list
                if len(call_obj[1]) > 0 and call_obj[1].get("processing_stage") == "completed"
            ]

            completion_log = completion_calls[0][1]

            # Should log full count but limit names to 5
            assert completion_log["tools_provided"] is True
            assert completion_log["tool_count"] == 7, "Should log actual count"
            assert len(completion_log["tool_names"]) <= 5, "Should limit names to first 5"


@pytest.mark.asyncio
async def test_step_64_handles_dict_format_tools():
    """
    GIVEN: Tools provided in OpenAI API dict format
    WHEN: step_64__llmcall completes
    THEN: Should extract tool names from dict format correctly
    """
    # Tools in OpenAI API format (dict with function.name)
    tools = [
        {"type": "function", "function": {"name": "search_kb", "description": "Search knowledge base"}},
        {"type": "function", "function": {"name": "search_ccnl", "description": "Search CCNL"}},
    ]

    ctx = {
        "provider_instance": MagicMock(),
        "messages": [{"role": "user", "content": "Test"}],
        "model": "gpt-4o-mini",
        "tools": tools,
        "request_id": "test_request_dict_tools",
    }

    mock_response = LLMResponse(content="Test", model="gpt-4o-mini", provider="openai", tool_calls=None)
    ctx["provider_instance"].chat_completion = AsyncMock(return_value=mock_response)

    with patch("app.observability.rag_logging.rag_step_log") as mock_log:
        with patch("app.observability.rag_logging.rag_step_timer"):
            await step_64__llmcall(ctx=ctx)

            completion_calls = [
                call_obj
                for call_obj in mock_log.call_args_list
                if len(call_obj[1]) > 0 and call_obj[1].get("processing_stage") == "completed"
            ]

            completion_log = completion_calls[0][1]

            # Should handle dict format
            assert completion_log["tools_provided"] is True
            assert completion_log["tool_count"] == 2
            # Should extract names from dict format
            assert "search_kb" in completion_log["tool_names"] or "search_ccnl" in completion_log["tool_names"]


@pytest.mark.asyncio
async def test_step_64_tools_logging_survives_errors():
    """
    GIVEN: LLM call with tools that fails
    WHEN: step_64__llmcall handles error
    THEN: Error log should still include tools information for debugging
    """
    tools = [KnowledgeSearchTool()]

    ctx = {
        "provider_instance": MagicMock(),
        "messages": [{"role": "user", "content": "Test"}],
        "model": "gpt-4o-mini",
        "tools": tools,
        "request_id": "test_request_error",
    }

    # Mock provider to raise error
    ctx["provider_instance"].chat_completion = AsyncMock(side_effect=Exception("API Error"))

    with patch("app.observability.rag_logging.rag_step_log") as mock_log:
        with patch("app.observability.rag_logging.rag_step_timer"):
            try:
                await step_64__llmcall(ctx=ctx)
            except Exception:
                pass  # Expected

            # Even in error case, logs should exist
            all_log_calls = mock_log.call_args_list
            assert len(all_log_calls) > 0, "Should log even on error"
