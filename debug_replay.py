import asyncio
from app.core.streaming_processor import EnhancedStreamingProcessor

async def debug_replay():
    p = EnhancedStreamingProcessor(stream_id="debug-replay")
    
    print("=== Step 1: Process first chunk ===")
    d1 = await p.process_chunk("<h3>1. Definizione</h3>")
    print(f"d1: '{d1}'")
    print(f"accumulated_html: '{p.accumulated_html}'")
    print(f"accumulated_raw: '{p.accumulated_raw}'")
    
    print("\n=== Step 2: Process second chunk ===")
    d2 = await p.process_chunk("\n\n<p>Il regime forfettario è un regime</p>")
    print(f"d2: '{d2}'")
    print(f"accumulated_html: '{p.accumulated_html}'")
    print(f"accumulated_raw: '{p.accumulated_raw}'")
    
    print("\n=== Step 3: Process replay snapshot ===")
    replay = "<h3>1. Definizione</h3>\n\n<p>Il regime forfettario è un regime</p><p>TAIL_ONLY</p>"
    print(f"replay chunk: '{replay}'")
    
    # Manually trace what should happen:
    p.accumulated_raw += replay  # This would be done in process_chunk
    new_full_html = p._normalize_to_html(p.accumulated_raw)
    print(f"new_full_html: '{new_full_html}'")
    print(f"acc length: {len(p.accumulated_html)}")
    print(f"new_full_html starts with acc? {new_full_html.startswith(p.accumulated_html)}")
    
    if new_full_html.startswith(p.accumulated_html):
        theoretical_delta = new_full_html[len(p.accumulated_html):]
        print(f"theoretical_delta (startswith): '{theoretical_delta}'")
    else:
        last_idx = new_full_html.rfind(p.accumulated_html)
        print(f"rfind result: {last_idx}")
        if last_idx != -1:
            theoretical_delta = new_full_html[last_idx + len(p.accumulated_html):]
            print(f"theoretical_delta (rfind): '{theoretical_delta}'")
    
    # Reset accumulated_raw for actual test
    p.accumulated_raw = p.accumulated_raw[:-len(replay)]
    
    d3 = await p.process_chunk(replay)
    print(f"actual d3: '{d3}'")

if __name__ == "__main__":
    asyncio.run(debug_replay())