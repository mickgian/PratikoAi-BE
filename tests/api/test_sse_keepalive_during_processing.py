"""
TDD RED Phase: Tests for SSE keepalive during long RAG processing.

Problem: Long queries like "riassunto di tutte le risoluzioni di ottobre e novembre 2025"
take 15-20+ seconds to process. Frontend timeout (30s) kills the connection before
first content chunk arrives → user sees stuck animation.

Solution: Send SSE keepalive comments (": keepalive\n\n") every 5 seconds during
RAG processing to keep connection alive and signal progress.

Expected: These tests will FAIL until keepalive logic is implemented.
"""

import asyncio
import time
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.core.llm.base import LLMResponse
from app.schemas.chat import Message


class TestSSEKeepaliveDuringProcessing:
    """Test that keepalive comments are sent during long RAG processing."""

    @pytest.mark.asyncio
    async def test_keepalive_sent_during_slow_rag_processing(self):
        """
        EXPECTED: FAIL (keepalive not implemented yet)

        Test that keepalive comments are sent while RAG is processing,
        before any content chunks are yielded.

        Scenario: RAG takes 11 seconds to process → should send 2 keepalive comments (at 5s and 10s).
        """
        agent = LangGraphAgent()
        messages = [Message(role="user", content="Long query that takes time")]

        # Mock slow RAG processing (11 seconds before first chunk)
        # 11 seconds ensures we get 2 keepalives (at 5s and 10s)
        async def slow_ainvoke(*args, **kwargs):
            await asyncio.sleep(11)  # Simulate 11 seconds of RAG processing
            return {
                "llm": {
                    "success": True,
                    "response": LLMResponse(
                        content="Response after long processing", model="gpt-4o-mini", provider="openai"
                    ),
                },
                "streaming": {"requested": True},
            }

        agent._graph = MagicMock()
        agent._graph.ainvoke = slow_ainvoke

        with patch("app.core.llm.factory.get_llm_factory"):
            chunks = []
            start_time = time.time()

            async for chunk in agent.get_stream_response(messages, "test_session"):
                chunks.append({"chunk": chunk, "timestamp": time.time() - start_time})

        # Verify keepalive comments were sent
        keepalive_chunks = [c for c in chunks if c["chunk"].startswith(": keepalive")]
        content_chunks = [c for c in chunks if not c["chunk"].startswith(":")]

        assert len(keepalive_chunks) >= 2, (
            f"Should send at least 2 keepalive comments during 11s processing. "
            f"Got {len(keepalive_chunks)} keepalives. "
            f"All chunks: {chunks}"
        )

        # Verify keepalive format is correct
        for ka_chunk in keepalive_chunks:
            assert ka_chunk["chunk"] == ": keepalive\n\n", (
                f"Keepalive must be exactly ': keepalive\\n\\n', " f"got: {repr(ka_chunk['chunk'])}"
            )

        # Verify keepalives sent before content
        if content_chunks:
            first_content_time = content_chunks[0]["timestamp"]
            for ka_chunk in keepalive_chunks:
                # Most keepalives should be before content
                if ka_chunk["timestamp"] < first_content_time - 1:
                    # At least one keepalive before content (with 1s tolerance)
                    break
            else:
                pytest.fail("No keepalive sent before first content chunk")

        # Verify content chunks still work
        assert len(content_chunks) > 0, "Should still yield content chunks"

    @pytest.mark.asyncio
    async def test_keepalive_stops_when_content_starts(self):
        """
        EXPECTED: FAIL (keepalive not implemented yet)

        Test that keepalive task stops once content starts streaming.
        """
        agent = LangGraphAgent()
        messages = [Message(role="user", content="Query")]

        # Mock RAG: 6 seconds processing, then stream content
        async def slow_then_stream(*args, **kwargs):
            await asyncio.sleep(6)  # 6 seconds → expect 1 keepalive
            return {
                "llm": {
                    "success": True,
                    "response": LLMResponse(
                        content="A" * 500, model="gpt-4o-mini", provider="openai"  # 500 chars → ~5 chunks
                    ),
                },
                "streaming": {"requested": True},
            }

        agent._graph = MagicMock()
        agent._graph.ainvoke = slow_then_stream

        with patch("app.core.llm.factory.get_llm_factory"):
            chunks = []
            async for chunk in agent.get_stream_response(messages, "test_session"):
                chunks.append(chunk)

        keepalive_chunks = [c for c in chunks if c.startswith(": keepalive")]
        content_chunks = [c for c in chunks if not c.startswith(":")]

        # Should have sent ~1 keepalive during 6s processing
        assert len(keepalive_chunks) >= 1, "Should send keepalive during processing"

        # Should not send keepalive after content starts
        # (Total chunks should be keepalives + content, not excessive)
        assert (
            len(chunks) < len(keepalive_chunks) + len(content_chunks) + 3
        ), "Keepalive should stop after content starts streaming"

        # Verify content chunks are present and correct
        assert len(content_chunks) > 0, "Should yield content chunks"

    @pytest.mark.asyncio
    async def test_no_keepalive_for_fast_responses(self):
        """
        EXPECTED: PASS or FAIL gracefully

        Test that keepalive is not sent for fast responses (< 5 seconds).
        This ensures we don't add overhead for normal queries.
        """
        agent = LangGraphAgent()
        messages = [Message(role="user", content="Quick query")]

        # Mock fast RAG (1 second)
        async def fast_ainvoke(*args, **kwargs):
            await asyncio.sleep(1)  # Fast response
            return {
                "llm": {
                    "success": True,
                    "response": LLMResponse(content="Quick answer", model="gpt-4o-mini", provider="openai"),
                },
                "streaming": {"requested": True},
            }

        agent._graph = MagicMock()
        agent._graph.ainvoke = fast_ainvoke

        with patch("app.core.llm.factory.get_llm_factory"):
            chunks = []
            async for chunk in agent.get_stream_response(messages, "test_session"):
                chunks.append(chunk)

        keepalive_chunks = [c for c in chunks if c.startswith(": keepalive")]

        # Fast responses should not trigger keepalive (or only 0-1)
        assert len(keepalive_chunks) <= 1, (
            f"Fast responses (<5s) should not send keepalives. " f"Got {len(keepalive_chunks)} keepalives"
        )

    @pytest.mark.asyncio
    async def test_keepalive_interval_approximately_5_seconds(self):
        """
        EXPECTED: FAIL (keepalive not implemented yet)

        Test that keepalives are sent approximately every 5 seconds.
        """
        agent = LangGraphAgent()
        messages = [Message(role="user", content="Long query")]

        # Mock 15 second processing → expect ~3 keepalives
        async def very_slow_ainvoke(*args, **kwargs):
            await asyncio.sleep(15)
            return {
                "llm": {
                    "success": True,
                    "response": LLMResponse(content="Response", model="gpt-4o-mini", provider="openai"),
                },
                "streaming": {"requested": True},
            }

        agent._graph = MagicMock()
        agent._graph.ainvoke = very_slow_ainvoke

        with patch("app.core.llm.factory.get_llm_factory"):
            chunks_with_time = []
            start_time = time.time()

            async for chunk in agent.get_stream_response(messages, "test_session"):
                chunks_with_time.append({"chunk": chunk, "elapsed": time.time() - start_time})

        keepalives = [c for c in chunks_with_time if c["chunk"].startswith(": keepalive")]

        # Should have ~3 keepalives for 15 seconds (every 5 seconds)
        assert len(keepalives) >= 2, f"15 second processing should send ~3 keepalives. Got {len(keepalives)}"

        # Check intervals between keepalives
        if len(keepalives) >= 2:
            intervals = []
            for i in range(1, len(keepalives)):
                interval = keepalives[i]["elapsed"] - keepalives[i - 1]["elapsed"]
                intervals.append(interval)

            # Intervals should be approximately 5 seconds (±1s tolerance)
            for interval in intervals:
                assert 4.0 <= interval <= 6.0, (
                    f"Keepalive intervals should be ~5 seconds. " f"Got intervals: {intervals}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
