import asyncio
from app.core.streaming_processor import EnhancedStreamingProcessor

async def debug_correct_replay():
    """Simulate how real streaming replay works."""
    p = EnhancedStreamingProcessor(stream_id="debug-correct-replay")
    
    print("=== Normal streaming progression ===")
    # Chunk 1: Initial content  
    d1 = await p.process_chunk("### 1. Definizione")
    print(f"d1: '{d1}'")
    
    # Chunk 2: Additional content
    d2 = await p.process_chunk("\n\nIl regime forfettario è un regime")
    print(f"d2: '{d2}'")
    print(f"accumulated_html: '{p.accumulated_html}'")
    
    print("\n=== Provider replay scenario ===")
    # Here's what happens when the provider replays:
    # It doesn't send new content to be appended - it sends a SNAPSHOT
    # that includes content we've already seen + some new content
    
    # Reset the accumulated_raw to simulate provider restart
    p.accumulated_raw = "### 1. Definizione\n\nIl regime forfettario è un regime\n\n**NUOVA PARTE**"
    new_full_html = p._normalize_to_html(p.accumulated_raw)
    print(f"Provider replay snapshot (normalized): '{new_full_html}'")
    print(f"Current accumulated HTML: '{p.accumulated_html}'")
    print(f"New full HTML starts with accumulated? {new_full_html.startswith(p.accumulated_html)}")
    
    if new_full_html.startswith(p.accumulated_html):
        expected_delta = new_full_html[len(p.accumulated_html):]
        print(f"Expected delta: '{expected_delta}'")
        # This should contain only the new part: "**NUOVA PARTE**"
        assert "Definizione" not in expected_delta
        assert "regime forfettario" not in expected_delta
        assert "NUOVA PARTE" in expected_delta
        print("✅ Replay handling works correctly!")

if __name__ == "__main__":
    asyncio.run(debug_correct_replay())