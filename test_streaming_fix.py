#!/usr/bin/env python3
"""
Test script to verify the streaming HTML formatting fix works correctly.
This simulates the LangGraph streaming behavior after our fix.
"""

import asyncio
import sys
sys.path.append('/Users/micky/PycharmProjects/PratikoAi-BE')

from app.core.content_formatter import StreamingHTMLProcessor

class MockToken:
    """Mock token object similar to what LangGraph would produce."""
    def __init__(self, content: str):
        self.content = content

async def simulate_fixed_streaming():
    """Simulate the fixed streaming behavior from get_stream_response."""
    print("🧪 Testing Fixed Streaming Implementation...")
    print("=" * 60)
    
    # Initialize HTML processor like in the actual method
    html_processor = StreamingHTMLProcessor()
    
    # Simulate tokens coming from LangGraph (complete chunks, not individual characters)
    mock_tokens = [
        MockToken("### 1. Regime Forfettario\n\n"),
        MockToken("Il regime forfettario è un regime **fiscale semplificato** "),
        MockToken("per le partite IVA.\n\n"),
        MockToken("## 2. Calcolo dell'imposta\n\n"),
        MockToken("Per un reddito di €50.000:\n\n"),
        MockToken("Calcolo: 50000 × 15% = 7500\n\n"),
        MockToken("### 3. Normativa\n\n"),
        MockToken("Riferimento: *Legge n.190/2014*")
    ]
    
    # Simulate the fixed streaming logic
    yielded_chunks = []
    
    for token in mock_tokens:
        try:
            # Get the content from the token
            content = token.content if hasattr(token, 'content') else str(token)
            
            # Process each character through HTML formatter for proper streaming
            for char in content:
                html_chunk = await html_processor.process_token(char)
                if html_chunk:
                    # This would be yielded in the actual implementation
                    yielded_chunks.append(html_chunk)
                    print(f"📦 HTML Chunk: {repr(html_chunk)}")
                    
        except Exception as token_error:
            print(f"❌ Error processing token: {token_error}")
            continue
    
    # Finalize any remaining content
    final_chunk = await html_processor.finalize()
    if final_chunk:
        yielded_chunks.append(final_chunk)
        print(f"🏁 Final Chunk: {repr(final_chunk)}")
    
    # Combine all chunks to see the final result
    combined_html = ''.join(yielded_chunks)
    
    print("\n" + "=" * 60)
    print("📋 FINAL COMBINED HTML:")
    print("=" * 60)
    print(combined_html)
    
    print("\n" + "=" * 60)
    print("🔍 VERIFICATION:")
    print("=" * 60)
    
    # Verify HTML formatting is correct
    checks = [
        ("<h3>1. Regime Forfettario</h3>" in combined_html, "H3 heading conversion"),
        ("<h2>2. Calcolo dell'imposta</h2>" in combined_html, "H2 heading conversion"),
        ("<strong>fiscale semplificato</strong>" in combined_html, "Bold text conversion"),
        ('<div class="calculation">' in combined_html, "Calculation formatting"),
        ("€ 50.000" in combined_html, "Currency formatting"),
        ('<cite class="legal-ref">Legge n.190/2014</cite>' in combined_html, "Legal reference formatting"),
        ("IVA" in combined_html and '<abbr title=' in combined_html, "Tax term abbreviation"),
        
        # Critical: No markdown syntax should remain
        ("###" not in combined_html, "No ### markers"),
        ("**" not in combined_html, "No ** markers"), 
        ("*Legge" not in combined_html, "No * markers"),
    ]
    
    all_passed = True
    for check_passed, description in checks:
        status = "✅" if check_passed else "❌"
        print(f"{status} {description}")
        if not check_passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Streaming HTML formatting is working correctly")
        print("✅ No markdown syntax remains in output")
        print("✅ Professional Italian formatting applied")
        print("✅ Ready for production use")
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔧 Fix needed before deployment")
    
    print("=" * 60)

async def test_sse_integration():
    """Test SSE message formatting integration."""
    print("\n🌐 Testing SSE Integration...")
    print("=" * 40)
    
    html_processor = StreamingHTMLProcessor()
    
    # Simulate SSE message creation for the chunks
    test_chunk = "<h3>Test Heading</h3>"
    sse_message = html_processor.format_sse_message(test_chunk, done=False)
    
    print(f"📡 SSE Message: {repr(sse_message)}")
    
    # Verify SSE format
    assert sse_message.startswith('data: '), "SSE message should start with 'data: '"
    assert sse_message.endswith('\n\n'), "SSE message should end with double newline"
    assert '"content":' in sse_message, "SSE message should contain content field"
    assert '"done": false' in sse_message, "SSE message should contain done field"
    
    print("✅ SSE integration working correctly")

async def main():
    """Run all streaming fix tests."""
    await simulate_fixed_streaming()
    await test_sse_integration()

if __name__ == "__main__":
    asyncio.run(main())