"""
Integration tests for the complete streaming flow.

Tests the full pipeline from API endpoint through to SSE output.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.api.v1.chatbot import router
from app.core.streaming_processor import EnhancedStreamingProcessor


@pytest.mark.asyncio
async def test_streaming_endpoint_pure_html():
    """Test that streaming endpoint returns only HTML, never markdown."""
    
    # Create a mock agent that yields markdown content
    mock_agent = AsyncMock()
    
    # Simulate LLM yielding markdown chunks
    async def mock_stream():
        chunks = [
            "###",
            " Welcome",
            "\n\n",
            "This is **bold**",
            " and this is ",
            "*italic*",
            " text.\n\n",
            "- Item 1\n",
            "- Item 2"
        ]
        for chunk in chunks:
            yield chunk
    
    mock_agent.get_stream_response.return_value = mock_stream()
    
    # Patch the agent
    with patch('app.api.v1.chatbot.agent', mock_agent):
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/chatbot")
        
        with TestClient(app) as client:
            # Create mock session
            with patch('app.api.v1.chatbot.get_current_session') as mock_session:
                mock_session.return_value = MagicMock(
                    id="test-session",
                    user_id="test-user"
                )
                
                # Make streaming request
                response = client.post(
                    "/api/v1/chatbot/chat/stream",
                    json={"messages": [{"role": "user", "content": "Hello"}]},
                    headers={"Authorization": "Bearer test-token"},
                    stream=True
                )
                
                # Collect all frames
                frames = []
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        frame_data = line[6:]  # Remove "data: " prefix
                        frames.append(json.loads(frame_data))
                
                # Verify no markdown in any frame
                for frame in frames[:-1]:  # Exclude done frame
                    if "content" in frame:
                        content = frame["content"]
                        # No markdown markers should be present
                        assert "###" not in content
                        assert "**" not in content
                        assert "*italic*" not in content
                        assert "- Item" not in content or "<li>" in content
                
                # Verify last frame is done without content
                assert frames[-1] == {"done": True}


@pytest.mark.asyncio
async def test_no_duplicate_emission_in_stream():
    """Test that content is never duplicated in the stream."""
    
    # Create a mock agent that yields content with potential duplication
    mock_agent = AsyncMock()
    
    async def mock_stream_with_replay():
        # Simulate a scenario where the LLM might replay content
        yield "Hello"
        yield " world"
        yield "Hello world"  # Full replay
        yield "!"
    
    mock_agent.get_stream_response.return_value = mock_stream_with_replay()
    
    processor = EnhancedStreamingProcessor()
    accumulated = ""
    
    async for chunk in mock_stream_with_replay():
        delta = await processor.process_chunk(chunk)
        if delta:
            # Ensure delta is not already in accumulated
            assert delta not in accumulated
            accumulated += delta
    
    # Final accumulated should be "Hello world!"
    assert accumulated == "Hello world!"


@pytest.mark.asyncio
async def test_format_switching_handling():
    """Test handling when LLM switches between markdown and HTML mid-stream."""
    
    processor = EnhancedStreamingProcessor()
    
    # Simulate format switching
    chunks = [
        "### Heading\n",  # Markdown
        "<p>This is HTML</p>",  # HTML
        "**Bold text**",  # Back to markdown
    ]
    
    all_output = ""
    for chunk in chunks:
        processor.accumulated_raw = all_output + chunk
        delta = await processor.process_chunk(chunk)
        if delta:
            all_output += delta
            # Verify output is always HTML
            assert "###" not in delta
            assert "**" not in delta


@pytest.mark.asyncio
async def test_sse_frame_structure():
    """Test that SSE frames have correct structure."""
    
    processor = EnhancedStreamingProcessor()
    
    # Test content frame
    content_frame = processor.format_sse_frame(content="<p>Test</p>", done=False)
    assert content_frame.startswith("data: ")
    assert content_frame.endswith("\n\n")
    
    data = json.loads(content_frame[6:-2])
    assert "content" in data
    assert "done" in data
    assert data["done"] is False
    assert data["content"] == "<p>Test</p>"
    
    # Test done frame
    done_frame = processor.format_sse_frame(done=True)
    data = json.loads(done_frame[6:-2])
    assert data == {"done": True}


@pytest.mark.asyncio
async def test_statistics_and_logging():
    """Test that statistics are properly tracked for monitoring."""
    
    processor = EnhancedStreamingProcessor()
    
    # Process several chunks
    test_content = "This is a test with **bold** and *italic* text."
    for char in test_content:
        await processor.process_chunk(char)
    
    stats = processor.get_stats()
    
    # Verify statistics
    assert stats["total_frames"] > 0
    assert stats["total_bytes_emitted"] > 0
    assert stats["accumulated_html_length"] > 0
    assert stats["accumulated_raw_length"] == len(test_content)


@pytest.mark.asyncio  
async def test_error_handling():
    """Test that errors are handled gracefully."""
    
    processor = EnhancedStreamingProcessor()
    
    # Test with None
    result = await processor.process_chunk(None)
    assert result is None
    
    # Test with empty string
    result = await processor.process_chunk("")
    assert result is None
    
    # Test finalization when empty
    processor.finalize()
    stats = processor.get_stats()
    assert stats["total_frames"] == 0


@pytest.mark.asyncio
async def test_italian_tax_content():
    """Test handling of Italian tax-specific content."""
    
    processor = EnhancedStreamingProcessor()
    
    # Italian tax calculation example
    tax_markdown = """
### Calcolo IRPEF

Reddito: €50.000
Aliquota: 23%

**Totale**: €11.500
"""
    
    result = await processor.process_chunk(tax_markdown)
    
    # Should be converted to HTML
    assert "###" not in result
    assert "**" not in result
    assert "<h3>" in result or "Calcolo IRPEF" in result
    
    # Currency should be preserved
    assert "€" in result or "&euro;" in result