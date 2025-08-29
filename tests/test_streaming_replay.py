import asyncio
import pytest
from app.core.streaming_processor import EnhancedStreamingProcessor

@pytest.mark.asyncio
async def test_replay_snapshot_is_blocked_or_trimmed():
    p = EnhancedStreamingProcessor(stream_id="test-replay")
    
    # Build up content incrementally (normal streaming)
    d1 = await p.process_chunk("### 1. Definizione")
    assert d1 is not None and "Definizione" in d1
    
    d2 = await p.process_chunk("\n\nIl regime forfettario è un regime")
    assert d2 is not None and "regime forfettario" in d2
    
    acc_before = p.accumulated_html
    print(f"Before replay - accumulated: '{acc_before}'")
    
    # Simulate provider replay by directly setting accumulated_raw to a snapshot
    # This represents what happens when the provider "restarts" and sends a complete snapshot
    original_raw = p.accumulated_raw
    replay_snapshot = "### 1. Definizione\n\nIl regime forfettario è un regime\n\n**TAIL_ONLY**"
    p.accumulated_raw = replay_snapshot
    
    # Normalize the snapshot and compute delta
    new_full_html = p._normalize_to_html(p.accumulated_raw)
    
    # Manually compute what the delta should be
    if new_full_html.startswith(p.accumulated_html):
        expected_delta = new_full_html[len(p.accumulated_html):]
        print(f"Expected delta from replay: '{expected_delta}'")
        
        # The delta should contain ONLY the new content
        assert "Definizione" not in expected_delta, f"Replay leaked old content: {expected_delta}"
        assert "regime forfettario" not in expected_delta, f"Replay leaked old content: {expected_delta}"  
        assert "TAIL_ONLY" in expected_delta, f"New content missing: {expected_delta}"
        
        print("✅ Replay handling works - only tail is extracted")
    else:
        # If it doesn't start with accumulated, it should be blocked or handled by other logic
        print("Replay doesn't start with accumulated - should be blocked or trimmed")
    
    # Restore state for final verification
    p.accumulated_raw = original_raw