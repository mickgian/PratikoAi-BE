"""
Test integration of HTML formatting with streaming system
"""

import sys
import asyncio
sys.path.append('/Users/micky/PycharmProjects/PratikoAi-BE')

from app.core.content_formatter import StreamingHTMLProcessor

async def test_streaming_html_processor():
    """Test the StreamingHTMLProcessor with realistic token stream."""
    print("Testing StreamingHTMLProcessor...")
    
    processor = StreamingHTMLProcessor()
    
    # Simulate token stream for "### 1. Definizione"
    tokens = ["###", " ", "1", ".", " ", "D", "e", "f", "i", "n", "i", "z", "i", "o", "n", "e", "\n"]
    
    result_chunks = []
    
    for token in tokens:
        html_chunk = await processor.process_token(token)
        if html_chunk:
            result_chunks.append(html_chunk)
            print(f"Got chunk: {html_chunk}")
    
    # Finalize
    final_chunk = await processor.finalize()
    if final_chunk:
        result_chunks.append(final_chunk)
        print(f"Final chunk: {final_chunk}")
    
    # Verify results
    full_result = ''.join(result_chunks)
    print(f"Full result: {full_result}")
    
    # Should contain proper HTML
    assert "<h3>" in full_result
    assert "Definizione" in full_result
    # Should not contain markdown
    assert "###" not in full_result
    
    print("✅ StreamingHTMLProcessor test passed!")

async def test_complete_tax_response():
    """Test processing a complete tax response."""
    print("\nTesting complete tax response...")
    
    processor = StreamingHTMLProcessor()
    
    # Simulate streaming response
    response_text = """### 1. Definizione

Il regime forfettario è **semplificato**.

- Primo punto
- Secondo punto

Calcolo: 50000 × 15% = 7500"""
    
    result_chunks = []
    
    for char in response_text:
        html_chunk = await processor.process_token(char)
        if html_chunk:
            result_chunks.append(html_chunk)
    
    # Finalize
    final_chunk = await processor.finalize()
    if final_chunk:
        result_chunks.append(final_chunk)
    
    full_result = ''.join(result_chunks)
    print(f"Complete result:\n{full_result}")
    
    # Verify all elements are properly formatted
    assert "<h3>1. Definizione</h3>" in full_result
    assert "<strong>semplificato</strong>" in full_result
    assert "<ul>" in full_result
    assert "<li>Primo punto</li>" in full_result
    assert '<div class="calculation">' in full_result
    
    # Critical: no markdown syntax
    forbidden = ["###", "**", "*", "- "]
    for syntax in forbidden:
        if syntax == "- " and "<li>" in full_result:
            continue  # Allow if converted to list
        assert syntax not in full_result, f"Found forbidden syntax: {syntax}"
    
    print("✅ Complete tax response test passed!")

async def test_sse_formatting():
    """Test SSE message formatting."""
    print("\nTesting SSE formatting...")
    
    processor = StreamingHTMLProcessor()
    
    html_content = "<h3>Test Heading</h3>"
    sse_message = processor.format_sse_message(html_content, done=False)
    
    print(f"SSE message: {sse_message}")
    
    # Should be proper SSE format
    assert sse_message.startswith('data: ')
    assert sse_message.endswith('\n\n')
    assert '"content":' in sse_message
    assert '"done": false' in sse_message
    
    # Test completion message
    completion_message = processor.format_sse_message("", done=True)
    assert '"done": true' in completion_message
    
    print("✅ SSE formatting test passed!")

async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Testing HTML Formatting Integration")
    print("=" * 60)
    
    try:
        await test_streaming_html_processor()
        await test_complete_tax_response()
        await test_sse_formatting()
        
        print("\n" + "=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ HTML formatting is working correctly")
        print("✅ Streaming integration is functional") 
        print("✅ SSE formatting is proper")
        print("✅ Ready for backend deployment")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())