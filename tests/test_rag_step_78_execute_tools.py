"""
Tests for RAG STEP 78 — LangGraphAgent._tool_call Execute tools (RAG.platform.langgraphagent.tool.call.execute.tools)

This process step executes tool calls from the LLM response by invoking the requested tools
and converting results to ToolMessage objects for the next LLM iteration.
"""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, ToolMessage


class TestRAGStep78ExecuteTools:
    """Test suite for RAG STEP 78 - Execute tools."""

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_78_execute_single_tool(self, mock_rag_log):
        """Test Step 78: Execute single tool call."""
        from app.orchestrators.platform import step_78__execute_tools

        # Mock AI message with tool call
        ai_message = AIMessage(
            content="I'll search for information.",
            tool_calls=[
                {
                    'name': 'search_knowledge_base',
                    'args': {'query': 'tax rates'},
                    'id': 'call_123'
                }
            ]
        )

        # Mock tool
        mock_tool = AsyncMock()
        mock_tool.ainvoke.return_value = "Found 5 documents about tax rates"

        tools_by_name = {
            'search_knowledge_base': mock_tool
        }

        ctx = {
            'ai_message': ai_message,
            'tools_by_name': tools_by_name,
            'request_id': 'test-78-single'
        }

        result = await step_78__execute_tools(messages=[], ctx=ctx)

        # Verify execution
        assert isinstance(result, dict)
        assert result['execution_successful'] is True
        assert result['tools_executed'] == 1
        assert len(result['tool_messages']) == 1

        # Verify tool was invoked
        mock_tool.ainvoke.assert_called_once_with({'query': 'tax rates'})

        # Verify ToolMessage structure
        tool_message = result['tool_messages'][0]
        assert isinstance(tool_message, ToolMessage)
        assert tool_message.content == "Found 5 documents about tax rates"
        assert tool_message.name == 'search_knowledge_base'
        assert tool_message.tool_call_id == 'call_123'

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_78_execute_multiple_tools(self, mock_rag_log):
        """Test Step 78: Execute multiple tool calls."""
        from app.orchestrators.platform import step_78__execute_tools

        ai_message = AIMessage(
            content="I'll search multiple sources.",
            tool_calls=[
                {'name': 'search_kb', 'args': {'query': 'tax'}, 'id': 'call_1'},
                {'name': 'search_faq', 'args': {'query': 'deduction'}, 'id': 'call_2'},
                {'name': 'ccnl_query', 'args': {'sector': 'retail'}, 'id': 'call_3'}
            ]
        )

        # Mock tools
        mock_kb = AsyncMock(return_value="KB results")
        mock_faq = AsyncMock(return_value="FAQ results")
        mock_ccnl = AsyncMock(return_value="CCNL results")

        tools_by_name = {
            'search_kb': mock_kb,
            'search_faq': mock_faq,
            'ccnl_query': mock_ccnl
        }

        ctx = {
            'ai_message': ai_message,
            'tools_by_name': tools_by_name,
            'request_id': 'test-78-multiple'
        }

        result = await step_78__execute_tools(messages=[], ctx=ctx)

        # Verify all tools executed
        assert result['execution_successful'] is True
        assert result['tools_executed'] == 3
        assert len(result['tool_messages']) == 3

        # Verify all tools were invoked
        mock_kb.ainvoke.assert_called_once_with({'query': 'tax'})
        mock_faq.ainvoke.assert_called_once_with({'query': 'deduction'})
        mock_ccnl.ainvoke.assert_called_once_with({'sector': 'retail'})

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_78_tool_with_complex_args(self, mock_rag_log):
        """Test Step 78: Tool with complex arguments."""
        from app.orchestrators.platform import step_78__execute_tools

        ai_message = AIMessage(
            content="Searching...",
            tool_calls=[
                {
                    'name': 'search_knowledge_base',
                    'args': {
                        'query': 'contract law',
                        'limit': 5,
                        'filters': {'type': 'legal', 'year': 2024}
                    },
                    'id': 'call_complex'
                }
            ]
        )

        mock_tool = AsyncMock(return_value="Complex search results")

        tools_by_name = {
            'search_knowledge_base': mock_tool
        }

        ctx = {
            'ai_message': ai_message,
            'tools_by_name': tools_by_name,
            'request_id': 'test-78-complex'
        }

        result = await step_78__execute_tools(messages=[], ctx=ctx)

        # Verify complex args passed correctly
        assert result['execution_successful'] is True
        mock_tool.ainvoke.assert_called_once_with({
            'query': 'contract law',
            'limit': 5,
            'filters': {'type': 'legal', 'year': 2024}
        })

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_78_routes_to_chat_node(self, mock_rag_log):
        """Test Step 78: Routes to chat node for next iteration."""
        from app.orchestrators.platform import step_78__execute_tools

        ai_message = AIMessage(
            content="Executing tool.",
            tool_calls=[{'name': 'test_tool', 'args': {}, 'id': 't1'}]
        )

        mock_tool = AsyncMock(return_value="Tool result")

        tools_by_name = {'test_tool': mock_tool}

        ctx = {
            'ai_message': ai_message,
            'tools_by_name': tools_by_name,
            'request_id': 'test-78-route'
        }

        result = await step_78__execute_tools(messages=[], ctx=ctx)

        # Should route back to chat node (Step 64/67 LLM call)
        assert result['execution_successful'] is True
        assert result['next_step'] == 'chat_node'

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_78_tool_not_found(self, mock_rag_log):
        """Test Step 78: Handles tool not found gracefully."""
        from app.orchestrators.platform import step_78__execute_tools

        ai_message = AIMessage(
            content="Calling unknown tool.",
            tool_calls=[{'name': 'unknown_tool', 'args': {}, 'id': 'unknown'}]
        )

        tools_by_name = {}

        ctx = {
            'ai_message': ai_message,
            'tools_by_name': tools_by_name,
            'request_id': 'test-78-not-found'
        }

        result = await step_78__execute_tools(messages=[], ctx=ctx)

        # Should handle gracefully
        assert result['execution_successful'] is False
        assert 'error' in result


class TestRAGStep78Parity:
    """Parity tests proving Step 78 preserves existing tool execution logic."""

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_78_parity_tool_execution(self, mock_rag_log):
        """Test Step 78: Parity with existing _tool_call logic."""
        from app.orchestrators.platform import step_78__execute_tools

        # Original logic from graph.py:814-822
        # for tool_call in state.messages[-1].tool_calls:
        #     tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
        #     outputs.append(
        #         ToolMessage(
        #             content=tool_result,
        #             name=tool_call["name"],
        #             tool_call_id=tool_call["id"],
        #         )
        #     )

        ai_message = AIMessage(
            content="Test",
            tool_calls=[
                {'name': 'test_tool', 'args': {'x': 1}, 'id': 't1'}
            ]
        )

        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value="Test result")
        tools_by_name = {'test_tool': mock_tool}

        ctx = {
            'ai_message': ai_message,
            'tools_by_name': tools_by_name,
            'request_id': 'test-parity'
        }

        result = await step_78__execute_tools(messages=[], ctx=ctx)

        # Original: await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
        mock_tool.ainvoke.assert_called_once_with({'x': 1})

        # Original: ToolMessage(content=..., name=..., tool_call_id=...)
        tool_message = result['tool_messages'][0]
        assert isinstance(tool_message, ToolMessage)
        assert tool_message.content == "Test result"
        assert tool_message.name == 'test_tool'
        assert tool_message.tool_call_id == 't1'

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_78_parity_langchain_import(self, mock_rag_log):
        """Test Step 78: Uses LangChain ToolMessage."""
        from app.orchestrators.platform import step_78__execute_tools

        ai_message = AIMessage(
            content="Test",
            tool_calls=[{'name': 'test', 'args': {}, 'id': '1'}]
        )

        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value="Result")
        tools_by_name = {'test': mock_tool}

        ctx = {
            'ai_message': ai_message,
            'tools_by_name': tools_by_name,
            'request_id': 'test-parity-import'
        }

        result = await step_78__execute_tools(messages=[], ctx=ctx)

        # Should create LangChain ToolMessage instance
        assert isinstance(result['tool_messages'][0], ToolMessage)


class TestRAGStep78Integration:
    """Integration tests for Step 76 → Step 78 → Chat flow."""

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_76_to_78_integration(self, mock_rag_log):
        """Test Step 76 (convert with tools) → Step 78 (execute) integration."""
        from app.orchestrators.platform import step_76__convert_aimsg, step_78__execute_tools
        from app.core.llm.base import LLMResponse

        # Step 76: Convert to AIMessage with tool calls
        tool_calls = [{'name': 'search', 'args': {'q': 'test'}, 'id': 'c1'}]

        llm_response = LLMResponse(
            content="Searching...",
            tool_calls=tool_calls,
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        step_76_ctx = {
            'llm_response': llm_response,
            'request_id': 'test-integration-76-78'
        }

        step_76_result = await step_76__convert_aimsg(messages=[], ctx=step_76_ctx)

        # Should create AIMessage with tool calls
        assert step_76_result['conversion_successful'] is True
        assert step_76_result['has_tool_calls'] is True
        assert step_76_result['next_step'] == 'execute_tools'

        # Step 78: Execute tools
        mock_tool = AsyncMock(return_value="Search results")
        tools_by_name = {'search': mock_tool}

        step_78_ctx = {
            'ai_message': step_76_result['ai_message'],
            'tools_by_name': tools_by_name,
            'request_id': step_76_result['request_id']
        }

        step_78_result = await step_78__execute_tools(messages=[], ctx=step_78_ctx)

        # Should execute successfully
        assert step_78_result['execution_successful'] is True
        assert step_78_result['tools_executed'] == 1
        assert step_78_result['next_step'] == 'chat_node'

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_78_prepares_for_next_llm_iteration(self, mock_rag_log):
        """Test Step 78: Prepares ToolMessages for next LLM iteration."""
        from app.orchestrators.platform import step_78__execute_tools

        ai_message = AIMessage(
            content="Executing tools...",
            tool_calls=[
                {'name': 'tool1', 'args': {'x': 1}, 'id': 't1'},
                {'name': 'tool2', 'args': {'y': 2}, 'id': 't2'}
            ]
        )

        mock_tool1 = AsyncMock(return_value="Result 1")
        mock_tool2 = AsyncMock(return_value="Result 2")

        tools_by_name = {
            'tool1': mock_tool1,
            'tool2': mock_tool2
        }

        ctx = {
            'ai_message': ai_message,
            'tools_by_name': tools_by_name,
            'messages': [{'role': 'user', 'content': 'test'}],
            'request_id': 'test-78-prep'
        }

        result = await step_78__execute_tools(messages=[], ctx=ctx)

        # Should prepare ToolMessages for next chat iteration
        assert result['execution_successful'] is True
        assert len(result['tool_messages']) == 2
        assert result['next_step'] == 'chat_node'

        # Context should contain tool results
        assert 'tool_messages' in result
        assert 'tools_executed' in result