import asyncio
from app.core.streaming_processor import EnhancedStreamingProcessor

async def debug_lcp():
    """Debug the LCP logic to see why replays are still getting through."""
    
    processor = EnhancedStreamingProcessor(stream_id="debug-lcp")
    
    # Build up content progressively
    S1 = "<h3>1. Definizione</h3>\n<p>Intro...</p>"
    S2 = "<h3>2. Normativa</h3>\n<p>Legge 190/2014...</p>"
    FRESH = "<p>In sintesi... [nuovo testo]</p>"
    
    print("=== Step 1: Process S1 ===")
    delta1 = await processor.process_chunk(S1)
    print(f"Delta1: '{delta1}'")
    print(f"Accumulated: '{processor.accumulated_html}'")
    
    print("\n=== Step 2: Process S1+S2 ===")
    delta2 = await processor.process_chunk(S1 + S2)
    print(f"Delta2: '{delta2}'")
    print(f"Accumulated: '{processor.accumulated_html}'")
    
    print("\n=== Step 3: Provider restart S1+S2+FRESH ===")
    restart_content = S1 + S2 + FRESH
    
    print(f"Restart content length: {len(restart_content)}")
    print(f"Accumulated length: {len(processor.accumulated_html)}")
    print(f"Restart starts with accumulated? {restart_content.startswith(processor.accumulated_html)}")
    
    # Check what LCP would find
    lcp_len = 0
    min_len = min(len(processor.accumulated_html), len(restart_content))
    for i in range(min_len):
        if processor.accumulated_html[i] == restart_content[i]:
            lcp_len += 1
        else:
            break
    
    print(f"LCP length: {lcp_len}")
    print(f"LCP == accumulated length? {lcp_len == len(processor.accumulated_html)}")
    
    if lcp_len == len(processor.accumulated_html):
        tail = restart_content[lcp_len:]
        print(f"Would emit tail: '{tail}'")
        print(f"S1 in tail? {'<h3>1. Definizione</h3>' in tail}")
        print(f"S2 in tail? {'<h3>2. Normativa</h3>' in tail}")
    
    # Now actually process it
    delta_restart = await processor.process_chunk(restart_content)
    print(f"\nActual delta_restart: '{delta_restart}'")

if __name__ == "__main__":
    asyncio.run(debug_lcp())