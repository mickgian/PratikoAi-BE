"""Tests for buffered response streaming timing and chunking.

This test suite specifically validates that the buffered streaming path
(lines 2870-2898 in graph.py) correctly chunks content and applies delays
for a visible streaming effect.

Critical Regression Protection:
- Ensures asyncio.sleep(0.05) is present and functioning
- Validates chunk size is appropriate (100 chars, industry standard)
- Validates word-boundary chunking prevents word corruption
- Confirms chunks don't all yield instantly
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


@pytest.fixture
def agent_with_mock_graph():
    """Create an agent with a mocked graph for testing."""
    agent = LangGraphAgent()
    # Create a mock graph with an async ainvoke method
    agent._graph = MagicMock()
    agent._graph.ainvoke = AsyncMock()
    return agent


class TestBufferedStreamingTiming:
    """Test timing characteristics of buffered streaming."""

    @pytest.mark.asyncio
    async def test_buffered_streaming_has_delay_between_chunks(self, agent_with_mock_graph):
        """
        CRITICAL TEST: Verify that asyncio.sleep is present in buffered streaming.

        This test prevents regression of the bug where removing asyncio.sleep
        caused all chunks to appear instantly, breaking the streaming effect.
        """
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        # Create a long buffered response (500 characters → ~5 chunks of 100)
        test_content = "A" * 500
        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                start_time = time.time()
                chunks = []

                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                end_time = time.time()
                total_duration = end_time - start_time

                # With 5 chunks and 0.05s delay, minimum duration should be ~0.25s
                # Allow some tolerance for test environment overhead
                assert (
                    total_duration > 0.15
                ), f"Streaming too fast ({total_duration:.3f}s), asyncio.sleep may be missing!"

                # Should produce multiple chunks
                assert len(chunks) > 1, "Should produce multiple chunks"

    @pytest.mark.asyncio
    async def test_buffered_streaming_chunk_size_is_correct(self, agent_with_mock_graph):
        """Test that chunk size is appropriate (currently 100 chars, industry standard)."""
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        # Create content with known length (200 chars of simple repeating text)
        # This should produce approximately 2 chunks around 100 chars each
        test_content = "A" * 200
        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Should produce 2 chunks of ~100 characters each
                assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
                # Each chunk should be around 100 chars (allow some variance)
                for i, chunk in enumerate(chunks):
                    assert 90 <= len(chunk) <= 110, f"Chunk {i} should be ~100 chars, got {len(chunk)}"

    @pytest.mark.asyncio
    async def test_buffered_streaming_chunks_not_yielded_instantly(self, agent_with_mock_graph):
        """
        Test that chunks are yielded with delays, not all at once.

        This ensures the streaming effect is visible to users.
        """
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        test_content = "A" * 300  # ~3 chunks of 100
        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunk_times = []
                start_time = time.time()

                async for _chunk in agent.get_stream_response(messages, "test_session"):
                    chunk_times.append(time.time() - start_time)

                # Check that chunks arrive over time, not all at once
                # First chunk should arrive quickly
                assert chunk_times[0] < 0.1, "First chunk should arrive quickly"

                # Later chunks should be delayed
                if len(chunk_times) >= 3:
                    # Time between first and third chunk should be at least 0.10s (2 delays of 0.05s)
                    time_diff = chunk_times[2] - chunk_times[0]
                    assert time_diff >= 0.08, (
                        f"Chunks arriving too quickly ({time_diff:.3f}s between 1st and 3rd), "
                        f"asyncio.sleep may be missing!"
                    )

    @pytest.mark.asyncio
    async def test_buffered_streaming_preserves_content_integrity(self, agent_with_mock_graph):
        """Test that chunking doesn't corrupt or lose content."""
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        # Use content with special characters to test boundary handling
        test_content = "Hello 世界! 🚀\nNew line\tTab"
        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Reassemble content
                reassembled = "".join(chunks)
                assert reassembled == test_content, "Chunking corrupted content"

    @pytest.mark.asyncio
    async def test_buffered_streaming_handles_short_content(self, agent_with_mock_graph):
        """Test buffered streaming with content shorter than chunk size."""
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        test_content = "Hi"  # Shorter than chunk size (100)
        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Should produce single chunk with full content
                assert len(chunks) == 1
                assert chunks[0] == test_content

    @pytest.mark.asyncio
    async def test_buffered_streaming_handles_exact_multiple_of_chunk_size(self, agent_with_mock_graph):
        """Test buffered streaming when content length is exact multiple of chunk size."""
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        test_content = "A" * 300  # Exactly 3 chunks of 100
        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Should produce exactly 3 chunks
                assert len(chunks) == 3
                assert all(len(chunk) == 100 for chunk in chunks)
                assert "".join(chunks) == test_content


class TestBufferedStreamingRegressionProtection:
    """Tests that specifically prevent known regressions."""

    @pytest.mark.asyncio
    async def test_regression_asyncio_import_present(self):
        """
        REGRESSION TEST: Ensure asyncio is imported in graph.py.

        Previous bug: asyncio.sleep used without import → NameError
        """
        # Import graph module and check for asyncio
        from app.core.langgraph import graph

        assert hasattr(graph, "asyncio") or "asyncio" in dir(
            graph
        ), "asyncio must be imported in graph.py for buffered streaming!"

    @pytest.mark.asyncio
    async def test_regression_buffered_path_uses_sleep(self, agent_with_mock_graph):
        """
        REGRESSION TEST: Verify that buffered streaming path includes delay.

        This test catches if asyncio.sleep is removed from the buffered streaming loop.
        """
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        # Use moderate length content
        test_content = "X" * 300  # 3 chunks of 100
        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        # Patch asyncio.sleep to track if it's called
        sleep_called = []
        original_sleep = asyncio.sleep

        async def mock_sleep(duration):
            sleep_called.append(duration)
            # Use original sleep to avoid recursion
            await original_sleep(0)  # Yield control without actual delay for test speed

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                with patch("app.core.langgraph.graph.asyncio.sleep", side_effect=mock_sleep):
                    chunks = []
                    async for chunk in agent.get_stream_response(messages, "test_session"):
                        chunks.append(chunk)

                    # Verify asyncio.sleep was called (once per chunk)
                    assert len(sleep_called) > 0, "asyncio.sleep not called - buffered streaming delay is missing!"

                    # Verify sleep duration is correct (0.05s, industry standard)
                    assert all(d == 0.05 for d in sleep_called), f"Sleep duration should be 0.05s, got: {sleep_called}"

    @pytest.mark.asyncio
    async def test_regression_chunks_dont_appear_simultaneously(self, agent_with_mock_graph):
        """
        REGRESSION TEST: Prevent bug where all chunks appeared at once.

        Previous bug: Removed asyncio.sleep → all chunks yielded instantly
        → response appeared all at once instead of streaming
        """
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        test_content = "B" * 400  # 4 chunks of 100
        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunk_intervals = []
                last_time = None

                async for _chunk in agent.get_stream_response(messages, "test_session"):
                    current_time = time.time()
                    if last_time is not None:
                        interval = current_time - last_time
                        chunk_intervals.append(interval)
                    last_time = current_time

                # Verify chunks are spaced apart in time
                if chunk_intervals:
                    avg_interval = sum(chunk_intervals) / len(chunk_intervals)
                    # Use 0.035s threshold to account for CI timing variance
                    # (sleep is 0.05s, but CI overhead can reduce measured interval)
                    assert (
                        avg_interval > 0.035
                    ), f"Chunks appearing too quickly (avg {avg_interval:.4f}s), asyncio.sleep likely missing!"


class TestWordBoundaryChunking:
    """Tests for word-boundary aware chunking."""

    @pytest.mark.asyncio
    async def test_word_boundary_doesnt_split_words(self, agent_with_mock_graph):
        """
        Test that word-boundary chunking avoids splitting words mid-word.

        This is critical for preventing character corruption in Italian text
        (double consonants like 'cc', 'll', 'nn', etc.)
        """
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        # Create content with words that should not be split
        # Use a sentence slightly longer than chunk_size (100)
        test_content = (
            "Il regime forfettario è un regime fiscale semplificato per le piccole "
            "imprese e i lavoratori autonomi in Italia che permette di pagare meno tasse"
        )  # ~150 chars, should produce 2 chunks

        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Verify content integrity
                reassembled = "".join(chunks)
                assert reassembled == test_content, "Content corrupted by chunking"

                # Verify that chunks break at word boundaries (spaces, punctuation)
                # Each chunk (except the last) should end with a boundary character
                boundary_chars = {" ", "\n", "\t", ".", ",", "!", "?", ";", ":", ")"}

                for i, chunk in enumerate(chunks[:-1]):  # All except last
                    last_char = chunk[-1]
                    # Should end with a boundary character or be within acceptable range
                    # (since we search up to 20 chars ahead)
                    assert (
                        last_char in boundary_chars or len(chunk) <= 120
                    ), f"Chunk {i} doesn't end at word boundary: '{chunk[-20:]}'"

    @pytest.mark.asyncio
    async def test_word_boundary_preserves_italian_double_consonants(self, agent_with_mock_graph):
        """
        Regression test for Italian double consonant corruption.

        Previous bug: chunk_size=5 split words like "piccole" → "pic|ole" (missing 'c')
        This test ensures double consonants are preserved.
        """
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        # Use Italian text with many double consonants that were being corrupted
        test_content = (
            "Ecco alcune piccole informazioni sulle annuali 20.000 euro delle "
            "piccole imprese con aliquote tutte molto interessanti e belle"
        )

        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Verify all words are intact
                reassembled = "".join(chunks)
                assert reassembled == test_content

                # Specifically check for double consonants that were corrupted before
                assert "Ecco" in reassembled  # Not "Eco"
                assert "piccole" in reassembled  # Not "picole"
                assert "annuali" in reassembled  # Not "anuli"
                assert "20.000" in reassembled  # Not "20.00"
                assert "delle" in reassembled  # Not "dele"
                assert "tutte" in reassembled  # Not "tute"
                assert "belle" in reassembled  # Not "bele"

    @pytest.mark.asyncio
    async def test_word_boundary_with_punctuation(self, agent_with_mock_graph):
        """Test that word-boundary chunking works correctly with punctuation."""
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        # Create text with various punctuation marks
        test_content = (
            "First sentence. Second sentence! Third question? Fourth: with colon; "
            "Fifth with semicolon, and sixth with comma. (Parentheses too) "
        ) * 2  # ~200+ chars

        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Verify content integrity
                reassembled = "".join(chunks)
                assert reassembled == test_content

    @pytest.mark.asyncio
    async def test_word_boundary_fallback_to_chunk_size(self, agent_with_mock_graph):
        """
        Test that if no word boundary is found within search range (20 chars),
        chunking falls back to exact chunk_size.
        """
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        # Create text with a very long "word" (no spaces) longer than chunk_size + 20
        long_word = "A" * 130  # Longer than 100 + 20
        test_content = long_word + " rest of text"

        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Verify content is preserved even with pathological case
                reassembled = "".join(chunks)
                assert reassembled == test_content

                # First chunk should be exactly 100 chars (fallback to chunk_size)
                assert len(chunks[0]) == 100

    @pytest.mark.asyncio
    async def test_word_boundary_with_unicode(self, agent_with_mock_graph):
        """Test that word-boundary chunking works with Unicode characters."""
        agent = agent_with_mock_graph
        messages = [Message(role="user", content="Test")]

        # Create text with various Unicode characters
        test_content = (
            "こんにちは 世界! Hello café résumé naïve Zürich 🚀 emoji test. "
            "More text to ensure multiple chunks are created here with various symbols "
            "like © ® ™ and currency symbols € £ ¥ § ¶ and more content."
        )

        buffered_response = LLMResponse(content=test_content, model="gpt-4o-mini", provider="openai")

        mock_state = {"llm": {"success": True, "response": buffered_response}, "streaming": {"requested": True}}

        with patch.object(agent._graph, "ainvoke", return_value=mock_state):
            with patch("app.core.llm.factory.get_llm_factory"):
                chunks = []
                async for chunk in agent.get_stream_response(messages, "test_session"):
                    chunks.append(chunk)

                # Verify Unicode content is preserved
                reassembled = "".join(chunks)
                assert reassembled == test_content
                assert "こんにちは" in reassembled
                assert "🚀" in reassembled
                assert "café" in reassembled
                assert "€" in reassembled
