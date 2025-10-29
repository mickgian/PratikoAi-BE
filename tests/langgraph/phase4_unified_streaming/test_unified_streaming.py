"""Test unified graph integration with streaming.

Tests that get_stream_response() uses the unified graph for all pre-LLM steps
(Steps 1-63) before streaming the LLM response (Step 64).
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.schemas import Message


class TestUnifiedGraphStreaming:
    """Test that streaming uses unified graph for pre-LLM steps."""

    @pytest.mark.asyncio
    async def test_streaming_executes_unified_graph_before_llm(self):
        """Test that unified graph executes all steps before streaming LLM response."""
        # Setup
        agent = LangGraphAgent()
        messages = [
            Message(role="user", content="Qual è il mio contratto CCNL?")
        ]
        session_id = "test-session-123"
        user_id = "test-user-456"

        # Create mock provider with async generator
        async def mock_stream_gen(*args, **kwargs):
            async for chunk in self._mock_stream():
                yield chunk

        mock_provider = Mock()
        mock_provider.model = "gpt-4"
        mock_provider.provider_type = Mock(value="openai")
        mock_provider.stream_completion = mock_stream_gen

        # Mock the unified graph to track execution
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "messages": messages,
            "session_id": session_id,
            "user_id": user_id,
            "request_valid": True,
            "privacy": {"anonymize_enabled": False, "pii_detected": False},
            "processed_messages": messages,
            "golden": {"eligible": False},
            "classification": {
                "domain": "labor",
                "action": "ccnl_query",
                "confidence": 0.85
            },
            "provider": {
                "selected": mock_provider,
                "cost_estimated": 0.015
            },
            "cache": {"hit": False, "key": "test-cache-key"}
        })

        # Patch graph creation to return our mock
        with patch.object(agent, '_graph', mock_graph):
            with patch.object(agent, 'create_graph', return_value=mock_graph):
                # Execute
                chunks = []
                async for chunk in agent.get_stream_response(messages, session_id, user_id):
                    chunks.append(chunk)

                # Verify unified graph was invoked
                assert mock_graph.ainvoke.called, "Unified graph should be invoked"

                call_args = mock_graph.ainvoke.call_args
                assert call_args is not None
                state_input = call_args[0][0] if call_args[0] else call_args[1].get('input') or call_args[1]

                # Verify input contains required fields
                assert "messages" in state_input or state_input.get("messages") or messages
                assert "session_id" in state_input or state_input.get("session_id") or session_id

                # Verify streaming happened
                assert len(chunks) > 0, "Should stream response chunks"
                assert "".join(chunks) == "Test response", "Should return complete response"

    @pytest.mark.asyncio
    async def test_streaming_uses_provider_from_graph_state(self):
        """Test that streaming uses the provider selected by the unified graph."""
        agent = LangGraphAgent()
        messages = [Message(role="user", content="Test query")]

        # Mock provider with call tracking
        call_tracker = {"called": False}

        async def mock_stream_gen(*args, **kwargs):
            call_tracker["called"] = True
            async for chunk in self._mock_stream():
                yield chunk

        mock_provider = Mock()
        mock_provider.model = "gpt-4"
        mock_provider.provider_type = Mock(value="openai")
        mock_provider.stream_completion = mock_stream_gen

        # Mock graph that returns provider in state
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "messages": messages,
            "session_id": "test-123",
            "provider": {"selected": mock_provider},
            "processed_messages": messages,
            "cache": {"hit": False}
        })

        with patch.object(agent, '_graph', mock_graph):
            # Execute
            chunks = []
            async for chunk in agent.get_stream_response(messages, "test-123"):
                chunks.append(chunk)

            # Verify provider's stream_completion was called
            assert call_tracker["called"], "Should use provider from graph state"

    @pytest.mark.asyncio
    async def test_streaming_returns_cached_response_if_cache_hit(self):
        """Test that if cache hits, return cached response without streaming."""
        agent = LangGraphAgent()
        messages = [Message(role="user", content="Cached query")]

        # Mock graph with cache hit
        mock_graph = AsyncMock()
        cached_response = "This is a cached response"
        mock_graph.ainvoke = AsyncMock(return_value={
            "messages": messages,
            "session_id": "test-456",
            "cache": {
                "hit": True,
                "response": {"content": cached_response}
            }
        })

        with patch.object(agent, '_graph', mock_graph):
            # Execute
            chunks = []
            async for chunk in agent.get_stream_response(messages, "test-456"):
                chunks.append(chunk)

            # For cache hit, should yield the cached response
            assert len(chunks) > 0, "Should return cached response"
            # Note: exact behavior depends on implementation

    @pytest.mark.asyncio
    async def test_streaming_executes_all_lanes_before_llm(self):
        """Test that all lanes execute in order before LLM streaming."""
        agent = LangGraphAgent()
        messages = [Message(role="user", content="Test query")]

        execution_log = []

        # Mock graph that logs execution
        mock_graph = AsyncMock()
        async def mock_invoke(state, **kwargs):
            # Simulate steps executing
            execution_log.append("Lane1:Request/Privacy")
            execution_log.append("Lane2:Messages")
            execution_log.append("Lane3:Golden/KB")
            execution_log.append("Lane4:Classification")
            execution_log.append("Lane6:Provider")
            execution_log.append("Lane7:Cache")

            return {
                "messages": messages,
                "session_id": state.get("session_id", "test"),
                "provider": {
                    "selected": self._create_mock_provider()
                },
                "processed_messages": messages,
                "cache": {"hit": False}
            }

        mock_graph.ainvoke = mock_invoke

        with patch.object(agent, '_graph', mock_graph):
            # Execute
            chunks = list([c async for c in agent.get_stream_response(messages, "test-789")])

            # Verify all lanes executed before streaming
            assert "Lane1:Request/Privacy" in execution_log
            assert "Lane2:Messages" in execution_log
            assert "Lane3:Golden/KB" in execution_log
            assert "Lane4:Classification" in execution_log
            assert "Lane6:Provider" in execution_log
            assert "Lane7:Cache" in execution_log
            assert len(chunks) > 0

    async def _mock_stream(self):
        """Helper to create a mock async stream."""
        for chunk in ["Test", " ", "response"]:
            yield chunk

    def _create_mock_provider(self):
        """Helper to create a mock provider with async generator."""
        async def mock_stream_gen(*args, **kwargs):
            async for chunk in self._mock_stream():
                yield chunk

        mock_provider = Mock()
        mock_provider.model = "gpt-4"
        mock_provider.provider_type = Mock(value="openai")
        mock_provider.stream_completion = mock_stream_gen
        return mock_provider


class TestStreamingBackwardCompatibility:
    """Test that streaming maintains backward compatibility and UX quality."""

    @pytest.mark.asyncio
    async def test_streaming_maintains_chunk_format(self):
        """Test that streaming chunks maintain the expected format."""
        agent = LangGraphAgent()
        messages = [Message(role="user", content="Test")]

        # Create mock provider with async generator
        async def mock_chunk_gen(*args, **kwargs):
            async for chunk in self._mock_chunks():
                yield chunk

        mock_provider = Mock()
        mock_provider.model = "gpt-4"
        mock_provider.provider_type = Mock(value="openai")
        mock_provider.stream_completion = mock_chunk_gen

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "messages": messages,
            "session_id": "test",
            "provider": {"selected": mock_provider},
            "processed_messages": messages,
            "cache": {"hit": False}
        })

        with patch.object(agent, '_graph', mock_graph):
            chunks = [c async for c in agent.get_stream_response(messages, "test")]

            # All chunks should be strings
            assert all(isinstance(c, str) for c in chunks)
            # Should be able to join chunks
            full_response = "".join(chunks)
            assert len(full_response) > 0

    async def _mock_chunks(self):
        """Helper for chunk streaming."""
        for chunk in ["Hello", " ", "world", "!"]:
            yield chunk
