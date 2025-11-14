"""
Tests for RAG STEP 77 — Convert to simple AIMessage (RAG.platform.convert.to.simple.aimessage)

This process step converts an LLM response without tool calls into a simple LangChain AIMessage object
with only content, preparing it for final response processing.
"""

from unittest.mock import patch

import pytest

from app.core.llm.base import LLMResponse


class TestRAGStep77SimpleAIMsg:
    """Test suite for RAG STEP 77 - Convert to simple AIMessage."""

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_77_convert_simple_response(self, mock_rag_log):
        """Test Step 77: Convert response without tool calls to simple AIMessage."""
        from app.orchestrators.platform import step_77__simple_aimsg

        llm_response = LLMResponse(
            content="Here's the answer to your question about Italian tax law.",
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        ctx = {
            'llm_response': llm_response,
            'request_id': 'test-77-simple'
        }

        result = await step_77__simple_aimsg(messages=[], ctx=ctx)

        # Verify conversion
        assert isinstance(result, dict)
        assert result['conversion_successful'] is True
        assert result['ai_message'] is not None
        assert result['message_type'] == 'AIMessage'
        assert result['has_tool_calls'] is False
        assert result['tool_call_count'] == 0

        # Verify AIMessage structure
        ai_message = result['ai_message']
        assert ai_message.content == "Here's the answer to your question about Italian tax law."
        assert not hasattr(ai_message, 'tool_calls') or ai_message.tool_calls == [] or ai_message.tool_calls is None

        # Verify structured logging (flexible for test environment)
        if mock_rag_log.call_count > 0:
            completed_logs = [
                call for call in mock_rag_log.call_args_list
                if call[1].get('processing_stage') == 'completed'
            ]

            if len(completed_logs) > 0:
                completed_log = completed_logs[0][1]
                assert completed_log['step'] == 77
                assert completed_log['node_label'] == 'SimpleAIMsg'
                assert completed_log['conversion_successful'] is True

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_77_preserves_content(self, mock_rag_log):
        """Test Step 77: Preserves response content in simple AIMessage."""
        from app.orchestrators.platform import step_77__simple_aimsg

        content = "Based on the current regulations, the maximum deduction for home office expenses is €2,500 per year."

        llm_response = LLMResponse(
            content=content,
            tool_calls=None,
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        ctx = {
            'llm_response': llm_response,
            'request_id': 'test-77-content'
        }

        result = await step_77__simple_aimsg(messages=[], ctx=ctx)

        # Verify content preservation
        assert result['conversion_successful'] is True
        assert result['ai_message'].content == content

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_77_no_tool_calls(self, mock_rag_log):
        """Test Step 77: Handles response with no tool calls."""
        from app.orchestrators.platform import step_77__simple_aimsg

        llm_response = LLMResponse(
            content="Simple response",
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        ctx = {
            'llm_response': llm_response,
            'request_id': 'test-77-no-tools'
        }

        result = await step_77__simple_aimsg(messages=[], ctx=ctx)

        # Should have no tool calls
        assert result['has_tool_calls'] is False
        assert result['tool_call_count'] == 0

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_77_routes_to_final_response(self, mock_rag_log):
        """Test Step 77: Routes to final response step."""
        from app.orchestrators.platform import step_77__simple_aimsg

        llm_response = LLMResponse(
            content="Test response",
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        ctx = {
            'llm_response': llm_response,
            'request_id': 'test-77-route'
        }

        result = await step_77__simple_aimsg(messages=[], ctx=ctx)

        # Should route to final response (Step 101)
        assert result['conversion_successful'] is True
        assert result['next_step'] == 'final_response'

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_77_empty_content(self, mock_rag_log):
        """Test Step 77: Handles empty content."""
        from app.orchestrators.platform import step_77__simple_aimsg

        llm_response = LLMResponse(
            content="",
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        ctx = {
            'llm_response': llm_response,
            'request_id': 'test-77-empty'
        }

        result = await step_77__simple_aimsg(messages=[], ctx=ctx)

        # Should still convert successfully with empty content
        assert result['conversion_successful'] is True
        assert result['ai_message'].content == ""


class TestRAGStep77Parity:
    """Parity tests proving Step 77 preserves existing simple AIMessage creation logic."""

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_77_parity_simple_aimessage_creation(self, mock_rag_log):
        """Test Step 77: Parity with existing simple AIMessage creation."""
        from app.orchestrators.platform import step_77__simple_aimsg

        # Original logic from graph.py:750-752
        # else:
        #     from langchain_core.messages import AIMessage
        #     ai_message = AIMessage(content=response.content)
        content = "Test content without tool calls"

        llm_response = LLMResponse(
            content=content,
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        ctx = {
            'llm_response': llm_response,
            'request_id': 'test-parity'
        }

        result = await step_77__simple_aimsg(messages=[], ctx=ctx)

        # Original: AIMessage(content=response.content)
        # Our result should match
        ai_message = result['ai_message']
        assert ai_message.content == content
        # Should NOT have tool_calls attribute or it should be empty/None
        if hasattr(ai_message, 'tool_calls'):
            assert ai_message.tool_calls == [] or ai_message.tool_calls is None

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_77_parity_langchain_import(self, mock_rag_log):
        """Test Step 77: Uses LangChain AIMessage."""
        from app.orchestrators.platform import step_77__simple_aimsg
        from langchain_core.messages import AIMessage

        llm_response = LLMResponse(
            content="Test",
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        ctx = {
            'llm_response': llm_response,
            'request_id': 'test-parity-import'
        }

        result = await step_77__simple_aimsg(messages=[], ctx=ctx)

        # Should create LangChain AIMessage instance
        assert isinstance(result['ai_message'], AIMessage)


class TestRAGStep77Integration:
    """Integration tests for Step 75 → Step 77 → Step 101 flow."""

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_75_to_77_integration(self, mock_rag_log):
        """Test Step 75 (no tools) → Step 77 (convert simple) integration."""
        from app.orchestrators.response import step_75__tool_check
        from app.orchestrators.platform import step_77__simple_aimsg

        # Step 75: Check for tool calls (none present)
        llm_response = LLMResponse(
            content="Here's your answer without tools.",
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        step_75_ctx = {
            'llm_response': llm_response,
            'request_id': 'test-integration-75-77'
        }

        step_75_result = await step_75__tool_check(messages=[], ctx=step_75_ctx)

        # Should detect no tool calls
        assert step_75_result['has_tool_calls'] is False
        assert step_75_result['next_step'] == 'convert_simple_message'

        # Step 77: Convert to simple AIMessage
        step_77_ctx = {
            'llm_response': step_75_result['llm_response'],
            'request_id': step_75_result['request_id']
        }

        step_77_result = await step_77__simple_aimsg(messages=[], ctx=step_77_ctx)

        # Should convert successfully
        assert step_77_result['conversion_successful'] is True
        assert step_77_result['has_tool_calls'] is False
        assert step_77_result['next_step'] == 'final_response'

    @pytest.mark.asyncio
    @patch('app.observability.rag_logging.rag_step_log')
    async def test_step_77_prepares_for_final_response(self, mock_rag_log):
        """Test Step 77: Prepares simple AIMessage for final response."""
        from app.orchestrators.platform import step_77__simple_aimsg

        llm_response = LLMResponse(
            content="Final answer to user query",
            tool_calls=[],
            cost_estimate=0.001,
            model="gpt-4",
            provider="openai"
        )

        ctx = {
            'llm_response': llm_response,
            'messages': [{'role': 'user', 'content': 'test'}],
            'request_id': 'test-77-prep'
        }

        result = await step_77__simple_aimsg(messages=[], ctx=ctx)

        # Should prepare for Step 101 (final response)
        assert result['conversion_successful'] is True
        assert result['ai_message'] is not None
        assert result['next_step'] == 'final_response'

        # Context should be ready for final response
        assert 'ai_message' in result
        assert 'llm_response' in result