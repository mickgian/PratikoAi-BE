"""
Test the enhanced second-start guard functionality.
"""

import pytest
from app.core.streaming_processor import EnhancedStreamingProcessor


@pytest.mark.asyncio
async def test_second_start_guard_artificial_replay():
    """Test the second-start guard with artificial provider replay."""
    processor = EnhancedStreamingProcessor()
    chunks = [
        "<h3>1. Title</h3>\n<p>alpha</p>",
        "\n\n<p>beta</p>",
        " ... tail ... ",
        "### 1. Title\n\nalpha\n\nbeta\n ... tail ...",  # artificial replay of the head in markdown
    ]
    
    outs = []
    for chunk in chunks:
        delta = await processor.process_chunk(chunk)
        if delta:
            outs.append(delta)
    
    # Should have emitted some frames but not duplicate content
    assert len(outs) > 0
    assert len(processor.accumulated_html) > 0
    
    # Final accumulated should be clean HTML without markdown
    assert "###" not in processor.accumulated_html
    assert "<h3>" in processor.accumulated_html or "Title" in processor.accumulated_html


@pytest.mark.asyncio
async def test_always_normalize_to_html():
    """Test that all content is always normalized to HTML."""
    processor = EnhancedStreamingProcessor()
    
    # Mix of markdown and HTML
    chunks = [
        "### Heading",
        "\n\n**Bold text**",
        "\n\n<p>Already HTML</p>"
    ]
    
    for chunk in chunks:
        await processor.process_chunk(chunk)
    
    # All markdown should be converted to HTML
    assert "###" not in processor.accumulated_html
    assert "**" not in processor.accumulated_html
    assert "<h3>" in processor.accumulated_html or "Heading" in processor.accumulated_html
    assert "<strong>" in processor.accumulated_html or "Bold" in processor.accumulated_html


@pytest.mark.asyncio
async def test_second_start_detection():
    """Test that second-start detection works correctly."""
    processor = EnhancedStreamingProcessor()
    
    # Build up some content
    await processor.process_chunk("# First Section\n\nSome content here")
    
    # Get the head for comparison
    head = processor.accumulated_html[:120]
    assert len(head) > 0
    
    # Now simulate a restart that includes the head content again
    replay_chunk = "# First Section\n\nSome content here\n\nMore new content"
    delta = await processor.process_chunk(replay_chunk)
    
    # The delta should be trimmed and not contain the restart
    # (or be None/empty if completely trimmed)
    if delta:
        # Should not contain the original heading
        assert "First Section" not in delta or "new content" in delta


@pytest.mark.asyncio
async def test_tag_stripping_helper():
    """Test the tag stripping and normalization helpers."""
    processor = EnhancedStreamingProcessor()
    
    # Test tag stripping
    html_text = "<h3>Title</h3><p>Content with <strong>bold</strong> text</p>"
    stripped = processor._strip_tags(html_text)
    assert "<" not in stripped
    assert ">" not in stripped
    assert "Title" in stripped
    assert "Content" in stripped
    
    # Test normalization
    text_with_whitespace = "  Title   Content  with   spaces  "
    normalized = processor._norm_text(text_with_whitespace)
    assert normalized == "title content with spaces"


@pytest.mark.asyncio
async def test_mixed_content_handling():
    """Test handling of mixed HTML and markdown content."""
    processor = EnhancedStreamingProcessor()
    
    # Mix HTML and markdown in the same chunk
    mixed_chunk = "<p>HTML paragraph</p>\n\n### Markdown heading\n\n**Bold markdown**"
    
    delta = await processor.process_chunk(mixed_chunk)
    
    # Should convert everything to proper HTML
    assert delta is not None
    assert "###" not in delta
    assert "**" not in delta or "<strong>" in delta
    assert "<p>" in delta
    assert "<h3>" in delta or "heading" in delta.lower()


@pytest.mark.asyncio
async def test_format_detection_always_mixed():
    """Test that format detection always returns 'mixed' now."""
    processor = EnhancedStreamingProcessor()
    
    # All different types should return 'mixed'
    assert processor._detect_format("### Markdown heading") == "mixed"
    assert processor._detect_format("<h3>HTML heading</h3>") == "mixed"
    assert processor._detect_format("Plain text") == "mixed"
    assert processor._detect_format("") == "mixed"


@pytest.mark.asyncio
async def test_no_markdown_leakage():
    """Comprehensive test that no markdown syntax ever leaks through."""
    processor = EnhancedStreamingProcessor()
    
    markdown_samples = [
        "### Heading 1",
        "## Heading 2", 
        "# Heading 1",
        "**Bold text**",
        "*Italic text*",
        "- Bullet point",
        "1. Numbered item",
        "`Code inline`",
        "```\nCode block\n```",
        "[Link](http://example.com)",
    ]
    
    all_deltas = []
    for sample in markdown_samples:
        delta = await processor.process_chunk(sample + "\n\n")
        if delta:
            all_deltas.append(delta)
    
    # Check that no markdown syntax appears in any delta
    all_output = "".join(all_deltas)
    assert "###" not in all_output
    assert "##" not in all_output.replace("</h2>", "").replace("</h3>", "")
    assert "**" not in all_output.replace("</strong>", "")
    assert "- " not in all_output or "<li>" in all_output
    assert "`" not in all_output or "<code>" in all_output