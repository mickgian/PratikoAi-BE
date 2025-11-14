"""Test that streaming uses buffered response instead of making duplicate LLM call.

This test suite validates the fix for duplicate LLM API calls during streaming:
- Problem: Streaming requests made 2 LLM calls (Step 64 + fallback)
- Solution: Check for buffered response from Step 64 before making fallback call
- Expected: Only 1 LLM API call per streaming request
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message
from app.core.llm.base import LLMResponse


@pytest.mark.asyncio
async def test_streaming_uses_buffered_response_no_duplicate_call():
    """
    GIVEN: Graph execution completed with LLM response in state
    WHEN: get_stream_response is called
    THEN: Should stream buffered content without making second LLM API call

    This is the primary test validating the fix for duplicate LLM calls.
    """
    agent = LangGraphAgent()
    messages = [Message(role="user", content="Test query")]

    # Create a realistic LLMResponse object (as returned by Step 64)
    buffered_response = LLMResponse(
        content="Complete LLM response from Step 64 that should be streamed to frontend",
        model="gpt-4o-mini",
        provider="openai",
        tokens_used=50,
        cost_estimate=0.0001
    )

    # Mock graph to return state with completed LLM response
    mock_state = {
        "llm": {
            "success": True,
            "response": buffered_response
        },
        "streaming": {"requested": True},
        "messages": [
            {"role": "user", "content": "Test query"},
            {"role": "assistant", "content": buffered_response.content}
        ]
    }

    with patch.object(agent._graph, 'ainvoke', return_value=mock_state) as mock_ainvoke:
        # Mock provider to track if second call made
        with patch('app.core.llm.factory.get_llm_factory') as mock_factory_getter:
            mock_factory = MagicMock()
            mock_provider = AsyncMock()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_getter.return_value = mock_factory

            # Collect streamed chunks
            chunks = []
            async for chunk in agent.get_stream_response(messages, "test_session"):
                chunks.append(chunk)

            # Assertions
            assert len(chunks) > 0, "Should yield chunks"
            full_response = "".join(chunks)
            assert "Complete LLM response from Step 64" in full_response, \
                "Streamed content should match buffered response"

            # Critical: Provider's stream_completion should NOT be called (no duplicate call)
            mock_provider.stream_completion.assert_not_called()

            # Graph should be invoked exactly once
            mock_ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_chunks_buffered_response_properly():
    """
    GIVEN: Buffered response with known content
    WHEN: Streaming is requested
    THEN: Content should be chunked and yielded properly
    """
    agent = LangGraphAgent()
    messages = [Message(role="user", content="Test")]

    test_content = "12345678901234567890"  # 20 chars
    buffered_response = LLMResponse(
        content=test_content,
        model="gpt-4o-mini",
        provider="openai"
    )

    mock_state = {
        "llm": {"success": True, "response": buffered_response},
        "streaming": {"requested": True}
    }

    with patch.object(agent._graph, 'ainvoke', return_value=mock_state):
        with patch('app.core.llm.factory.get_llm_factory'):
            chunks = []
            async for chunk in agent.get_stream_response(messages, "test_session"):
                chunks.append(chunk)

            # Verify chunking behavior
            assert len(chunks) > 1, "Should produce multiple chunks"
            full_response = "".join(chunks)
            assert full_response == test_content, "Reassembled content should match original"


@pytest.mark.asyncio
async def test_streaming_handles_dict_format_response():
    """
    GIVEN: Buffered response in dict format (legacy compatibility)
    WHEN: Streaming is requested
    THEN: Should extract content from dict and stream it
    """
    agent = LangGraphAgent()
    messages = [Message(role="user", content="Test")]

    # Some parts of codebase might return dict format
    mock_state = {
        "llm": {
            "success": True,
            "response": {"content": "Response in dict format"}
        },
        "streaming": {"requested": True}
    }

    with patch.object(agent._graph, 'ainvoke', return_value=mock_state):
        with patch('app.core.llm.factory.get_llm_factory'):
            chunks = []
            async for chunk in agent.get_stream_response(messages, "test_session"):
                chunks.append(chunk)

            full_response = "".join(chunks)
            assert "Response in dict format" in full_response


@pytest.mark.asyncio
async def test_streaming_falls_back_when_no_buffered_response():
    """
    GIVEN: Graph execution did not produce LLM response (edge case)
    WHEN: get_stream_response is called
    THEN: Should fall back to provider.stream_completion

    This ensures the fallback path still works for edge cases.
    """
    agent = LangGraphAgent()
    messages = [Message(role="user", content="Test query")]

    # Mock graph with no LLM response (failure case)
    mock_state = {
        "llm": {"success": False},
        "streaming": {"requested": True},
        "messages": [{"role": "user", "content": "Test query"}]
    }

    with patch.object(agent._graph, 'ainvoke', return_value=mock_state):
        with patch('app.core.llm.factory.get_llm_factory') as mock_factory_getter:
            mock_factory = MagicMock()
            mock_provider = AsyncMock()

            # Mock streaming response
            async def mock_stream(*args, **kwargs):
                yield "fallback"
                yield "chunks"

            mock_provider.stream_completion.return_value = mock_stream()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_getter.return_value = mock_factory

            chunks = []
            async for chunk in agent.get_stream_response(messages, "test_session"):
                chunks.append(chunk)

            # Fallback should be called when no buffered response
            mock_provider.stream_completion.assert_called_once()
            assert "fallback" in chunks or "fallbackchunks" in "".join(chunks)


@pytest.mark.asyncio
async def test_streaming_handles_empty_buffered_content():
    """
    GIVEN: Buffered response exists but content is empty
    WHEN: Streaming is requested
    THEN: Should fall back to provider streaming
    """
    agent = LangGraphAgent()
    messages = [Message(role="user", content="Test")]

    # Edge case: response object exists but content is empty
    mock_state = {
        "llm": {
            "success": True,
            "response": LLMResponse(
                content="",  # Empty content
                model="gpt-4o-mini",
                provider="openai"
            )
        },
        "streaming": {"requested": True}
    }

    with patch.object(agent._graph, 'ainvoke', return_value=mock_state):
        with patch('app.core.llm.factory.get_llm_factory') as mock_factory_getter:
            mock_factory = MagicMock()
            mock_provider = AsyncMock()

            async def mock_stream(*args, **kwargs):
                yield "fallback_content"

            mock_provider.stream_completion.return_value = mock_stream()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_getter.return_value = mock_factory

            chunks = []
            async for chunk in agent.get_stream_response(messages, "test_session"):
                chunks.append(chunk)

            # Should fall back when content is empty
            mock_provider.stream_completion.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_logs_buffered_response_usage():
    """
    GIVEN: Buffered response is used for streaming
    WHEN: Streaming occurs
    THEN: Should log that buffered response was used (for observability)
    """
    agent = LangGraphAgent()
    messages = [Message(role="user", content="Test")]

    buffered_response = LLMResponse(
        content="Test content",
        model="gpt-4o-mini",
        provider="openai"
    )

    mock_state = {
        "llm": {"success": True, "response": buffered_response},
        "streaming": {"requested": True}
    }

    with patch.object(agent._graph, 'ainvoke', return_value=mock_state):
        with patch('app.core.llm.factory.get_llm_factory'):
            with patch('app.core.langgraph.graph.logger') as mock_logger:
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Should log that buffered response is being used
                log_calls = [call for call in mock_logger.info.call_args_list
                           if 'buffered' in str(call).lower()]
                assert len(log_calls) > 0, "Should log buffered response usage"
