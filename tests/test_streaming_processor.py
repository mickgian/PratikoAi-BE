"""
Tests for the enhanced streaming processor.

Verifies:
- Pure HTML output (no markdown markers)
- Proper deduplication (no content replay)
- Delta-only emission
- Correct SSE frame formatting
"""

import pytest
import json
import asyncio
from app.core.streaming_processor import EnhancedStreamingProcessor


@pytest.mark.asyncio
async def test_markdown_to_html_conversion():
    """Test that markdown is always converted to HTML."""
    processor = EnhancedStreamingProcessor()
    
    # Test header conversion
    chunk = "### This is a heading"
    html_delta = await processor.process_chunk(chunk)
    assert html_delta is not None
    assert "###" not in html_delta
    assert "<h3>" in html_delta or "h3" in html_delta.lower()
    
    # Reset for next test
    processor = EnhancedStreamingProcessor()
    
    # Test bold text
    chunk = "This is **bold** text"
    html_delta = await processor.process_chunk(chunk)
    assert "**" not in html_delta
    assert "<strong>" in html_delta or "<b>" in html_delta
    
    # Reset for next test
    processor = EnhancedStreamingProcessor()
    
    # Test italic text
    chunk = "This is *italic* text"
    html_delta = await processor.process_chunk(chunk)
    assert "*italic*" not in html_delta
    assert "<em>" in html_delta or "<i>" in html_delta
    
    # Reset for next test
    processor = EnhancedStreamingProcessor()
    
    # Test code blocks
    chunk = "```python\nprint('hello')\n```"
    html_delta = await processor.process_chunk(chunk)
    assert "```" not in html_delta
    assert "<code>" in html_delta or "<pre>" in html_delta


@pytest.mark.asyncio
async def test_no_duplicate_content():
    """Test that duplicate content is not emitted."""
    processor = EnhancedStreamingProcessor()
    
    # First chunk
    chunk1 = "Hello "
    delta1 = await processor.process_chunk(chunk1)
    assert delta1 == "Hello "
    
    # Second chunk extends the first
    chunk2 = "world"
    delta2 = await processor.process_chunk(chunk2)
    assert delta2 == "world"
    
    # Simulate receiving the full content again (replay)
    full_content = "Hello world"
    delta3 = await processor.process_chunk("")  # Force reprocess
    processor.accumulated_raw = full_content
    delta3 = await processor.process_chunk("")
    
    # Should not emit anything as it's all duplicate
    assert delta3 is None or delta3 == ""


@pytest.mark.asyncio
async def test_delta_only_emission():
    """Test that only new content (deltas) are emitted."""
    processor = EnhancedStreamingProcessor()
    
    # Simulate incremental streaming
    chunks = ["He", "llo", " wor", "ld!"]
    expected_deltas = ["He", "llo", " wor", "ld!"]
    
    for chunk, expected in zip(chunks, expected_deltas):
        delta = await processor.process_chunk(chunk)
        assert delta == expected
    
    # Verify accumulated content
    assert processor.accumulated_html == "Hello world!"


@pytest.mark.asyncio
async def test_mixed_format_handling():
    """Test handling when format switches between markdown and HTML."""
    processor = EnhancedStreamingProcessor()
    
    # Start with markdown
    chunk1 = "### Heading\n"
    delta1 = await processor.process_chunk(chunk1)
    assert "###" not in delta1
    assert delta1  # Should have content
    
    # Continue with more markdown
    chunk2 = "Some **bold** text"
    delta2 = await processor.process_chunk(chunk2)
    # Should only get the new part, not replay the heading
    assert "Heading" not in delta2
    assert "**" not in delta2


@pytest.mark.asyncio
async def test_sse_frame_formatting():
    """Test SSE frame formatting."""
    processor = EnhancedStreamingProcessor()
    
    # Test content frame
    content_frame = processor.format_sse_frame(content="<p>Hello</p>", done=False)
    assert content_frame.startswith("data: ")
    assert content_frame.endswith("\n\n")
    
    data = json.loads(content_frame[6:-2])  # Remove "data: " and "\n\n"
    assert data["content"] == "<p>Hello</p>"
    assert data["done"] is False
    
    # Test done frame
    done_frame = processor.format_sse_frame(done=True)
    assert done_frame.startswith("data: ")
    assert done_frame.endswith("\n\n")
    
    data = json.loads(done_frame[6:-2])
    assert data["done"] is True
    assert "content" not in data or data.get("content") == ""


@pytest.mark.asyncio
async def test_list_conversion():
    """Test that lists are converted properly."""
    processor = EnhancedStreamingProcessor()
    
    # Test bullet list
    chunk = "- Item 1\n- Item 2\n- Item 3"
    html_delta = await processor.process_chunk(chunk)
    assert "-" not in html_delta or "<li>" in html_delta
    assert "<ul>" in html_delta or "<li>" in html_delta
    
    # Reset processor
    processor = EnhancedStreamingProcessor()
    
    # Test numbered list
    chunk = "1. First\n2. Second\n3. Third"
    html_delta = await processor.process_chunk(chunk)
    assert "1." not in html_delta or "<li>" in html_delta
    assert "<ol>" in html_delta or "<li>" in html_delta


@pytest.mark.asyncio
async def test_incremental_streaming():
    """Test realistic incremental streaming scenario."""
    processor = EnhancedStreamingProcessor()
    
    # Simulate character-by-character streaming of markdown
    markdown_text = "### Title\n\nThis is **bold** and this is *italic*."
    accumulated = ""
    
    for char in markdown_text:
        accumulated += char
        # Process accumulated content
        processor.accumulated_raw = accumulated
        delta = await processor.process_chunk("")
        
        # We might not get output for every character (buffering)
        if delta:
            # But when we do, it should be HTML
            assert "###" not in delta
            assert "**" not in delta
            assert "*italic*" not in delta


@pytest.mark.asyncio
async def test_statistics_tracking():
    """Test that statistics are properly tracked."""
    processor = EnhancedStreamingProcessor()
    
    # Process some chunks
    chunks = ["Hello", " ", "world", "!"]
    for chunk in chunks:
        await processor.process_chunk(chunk)
    
    stats = processor.get_stats()
    assert stats["total_frames"] > 0
    assert stats["total_bytes_emitted"] > 0
    assert stats["accumulated_html_length"] > 0
    assert stats["accumulated_raw_length"] == len("Hello world!")


@pytest.mark.asyncio
async def test_empty_chunk_handling():
    """Test that empty chunks are handled gracefully."""
    processor = EnhancedStreamingProcessor()
    
    # Empty chunk should return None
    delta = await processor.process_chunk("")
    assert delta is None
    
    delta = await processor.process_chunk(None)
    assert delta is None
    
    # Whitespace only
    delta = await processor.process_chunk("   ")
    # Might return the whitespace or None depending on context
    assert delta is None or delta.strip() == ""


@pytest.mark.asyncio
async def test_format_detection():
    """Test format detection logic."""
    processor = EnhancedStreamingProcessor()
    
    # Test HTML detection
    assert processor._detect_format("<p>Hello</p>") == "html"
    assert processor._detect_format("<h1>Title</h1>") == "html"
    
    # Test markdown detection
    assert processor._detect_format("### Heading") == "markdown"
    assert processor._detect_format("**bold**") == "markdown"
    assert processor._detect_format("- list item") == "markdown"
    assert processor._detect_format("`code`") == "markdown"
    
    # Test plain text detection
    assert processor._detect_format("Just plain text") == "plain"
    assert processor._detect_format("No special formatting") == "plain"


@pytest.mark.asyncio
async def test_no_wrapper_tags():
    """Test that HTML output doesn't have unnecessary wrapper tags."""
    processor = EnhancedStreamingProcessor()
    
    # Single line should not be wrapped
    chunk = "Simple text"
    html_delta = await processor.process_chunk(chunk)
    assert html_delta == "Simple text"
    
    # Reset processor
    processor = EnhancedStreamingProcessor()
    
    # Multi-line should be wrapped appropriately
    chunk = "Line 1\nLine 2"
    html_delta = await processor.process_chunk(chunk)
    assert "<p>" in html_delta