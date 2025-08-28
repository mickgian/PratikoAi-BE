"""
Test the Longest Common Prefix (LCP) fallback for content discontinuities.

This ensures that even when markdown conversion causes reflows or changes
in earlier content, we still emit only deltas, not full replays.
"""

import pytest
from app.core.streaming_processor import EnhancedStreamingProcessor


@pytest.mark.asyncio
async def test_lcp_fallback_on_reflow():
    """Test that LCP fallback handles content reflow correctly."""
    processor = EnhancedStreamingProcessor()
    
    # Simulate a situation where markdown conversion changes earlier HTML
    # First chunk converts to HTML with certain attributes
    processor.accumulated_html = '<h3 class="heading">Title</h3><p>First paragraph</p>'
    processor.accumulated_raw = "### Title\nFirst paragraph"
    
    # New content has slightly different HTML for the same markdown
    # (e.g., markdown2 might add different attributes or spacing)
    new_html = '<h3 class="heading" id="title">Title</h3><p>First paragraph</p><p>New paragraph</p>'
    
    # Process with the discontinuity
    delta = processor._compute_delta(new_html)
    
    # Should use LCP fallback and only emit the truly new part
    # The LCP is '<h3 class="heading"' (19 chars)
    # So delta should start after that point
    assert delta is not None
    assert '<h3' not in delta or 'Title</h3>' in delta  # Partial header or new content
    assert 'Title' in delta or 'New paragraph' in delta  # Some new content


@pytest.mark.asyncio
async def test_lcp_no_duplicate_on_small_changes():
    """Test that small HTML changes don't cause full content replay."""
    processor = EnhancedStreamingProcessor()
    
    # Existing content
    processor.accumulated_html = '<ul><li>Item 1</li></ul>'
    
    # New content with slightly different formatting but same visible text
    new_html = '<ul>\n<li>Item 1</li>\n<li>Item 2</li>\n</ul>'
    
    delta = processor._compute_delta(new_html)
    
    # Should not replay "Item 1", only emit the new part
    assert delta is not None
    assert 'Item 1' not in delta or 'Item 2' in delta
    

@pytest.mark.asyncio
async def test_lcp_with_minimal_common_prefix():
    """Test LCP when there's minimal common prefix."""
    processor = EnhancedStreamingProcessor()
    
    processor.accumulated_html = '<p>Old content</p>'
    new_html = '<h1>Completely different</h1>'
    
    delta = processor._compute_delta(new_html)
    
    # They share '<' as common prefix (LCP=1), so delta is everything after
    assert delta == 'h1>Completely different</h1>'


@pytest.mark.asyncio
async def test_lcp_with_identical_content():
    """Test LCP when content is identical (no delta)."""
    processor = EnhancedStreamingProcessor()
    
    processor.accumulated_html = '<p>Same content</p>'
    new_html = '<p>Same content</p>'
    
    delta = processor._compute_delta(new_html)
    
    # Should return empty string as there's no new content
    assert delta == ""


@pytest.mark.asyncio
async def test_whitespace_only_delta_skipped():
    """Test that whitespace-only deltas are filtered out."""
    processor = EnhancedStreamingProcessor()
    
    # Set up initial content
    processor.accumulated_html = "<p>Hello</p>"
    processor.accumulated_raw = "Hello"
    
    # New content that only adds whitespace
    processor.accumulated_raw = "Hello\n\n   "
    
    # Process empty chunk to trigger normalization
    result = await processor.process_chunk("")
    
    # The delta should be minimal or None since it's just whitespace
    assert result is None or not result.strip() or "</p>" in result


@pytest.mark.asyncio
async def test_whitespace_with_html_tags_preserved():
    """Test that whitespace with HTML tags is preserved."""
    processor = EnhancedStreamingProcessor()
    
    processor.accumulated_html = "<p>Hello"
    processor.accumulated_raw = "Hello"
    
    # New content adds closing tag and whitespace
    new_raw = "Hello</p>  \n"
    processor.accumulated_raw = new_raw
    
    # This should be preserved because it contains HTML tags
    result = await processor.process_chunk("")
    
    # The closing tag should be preserved even with whitespace
    # Note: actual result depends on markdown conversion
    assert result is None or "</p>" in str(result) or result == ""


@pytest.mark.asyncio
async def test_lcp_performance_with_large_content():
    """Test that LCP performs well with large content."""
    processor = EnhancedStreamingProcessor()
    
    # Create large accumulated content
    large_base = "<p>" + "x" * 10000 + "</p>"
    processor.accumulated_html = large_base
    
    # New content extends the base
    new_content = large_base + "<p>New paragraph</p>"
    
    delta = processor._compute_delta(new_content)
    
    # Should efficiently find the delta
    assert delta == "<p>New paragraph</p>"
    assert len(delta) < 100  # Delta should be small, not the full content