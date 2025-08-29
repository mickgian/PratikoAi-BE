import asyncio
from app.core.streaming_processor import EnhancedStreamingProcessor

async def test_incremental():
    """Test how the processor handles truly incremental chunks."""
    
    processor = EnhancedStreamingProcessor(stream_id="incremental-test")
    
    print("=== Incremental streaming test ===")
    
    # Simulate incremental chunks like a real LLM provider
    chunks = [
        "### 1. Definizione",
        "\n\nIntro text here",  # New content only
        "\n\n### 2. Normativa", # New content only  
        "\n\nLegge 190/2014"   # New content only
    ]
    
    for i, chunk in enumerate(chunks):
        print(f"\n--- Processing chunk {i+1}: '{chunk}' ---")
        delta = await processor.process_chunk(chunk)
        print(f"Delta: '{delta}'")
        print(f"Accumulated: '{processor.accumulated_html}'")
        print(f"Emitted hashes: {len(processor.emitted_hashes)}")
    
    # Now test a replay scenario - same chunk sent again
    print(f"\n--- Replay test: sending chunk 1 again ---")
    replay_delta = await processor.process_chunk(chunks[0])  # Send first chunk again
    
    if replay_delta:
        print(f"REPLAY LEAKED: '{replay_delta}'")
    else:
        print("✅ REPLAY BLOCKED: No delta emitted")

if __name__ == "__main__":
    asyncio.run(test_incremental())