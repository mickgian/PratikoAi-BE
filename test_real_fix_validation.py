# Test that validates the REAL fix prevents duplicate content in FE payload
import pytest
import asyncio
from app.core.streaming_processor import EnhancedStreamingProcessor

class TestRealFixValidation:
    """Validate that LCP + HashGate prevents duplicate content emission."""
    
    @pytest.mark.asyncio
    async def test_provider_restart_no_duplication(self):
        """
        Test the exact scenario that caused duplication: provider restart with replay.
        
        With the REAL fix, the duplicate content should NOT leak into FE payload.
        """
        # Use the new fixed processor
        processor = EnhancedStreamingProcessor(stream_id="test-real-fix", enable_hash_gate=False)
        
        # Simulate the same provider restart scenario as before
        S1 = "<h3>1. Definizione</h3>\n<p>Intro...</p>"
        S2 = "<h3>2. Normativa</h3>\n<p>Legge 190/2014...</p>"
        S3 = "<h3>3. Aspetti</h3>\n<p>Coefficiente...</p>"
        S4 = "<h3>4. Esempi</h3>\n<p>Esempio 1...</p>"
        S5 = "<h3>5. Scadenze</h3>\n<p>Dichiarazione...</p>"
        
        FRESH = "<p>In sintesi... [nuovo testo]</p>"
        
        emitted_deltas = []
        
        # Process normal progression
        delta1 = await processor.process_chunk(S1)
        if delta1: emitted_deltas.append(delta1)
        
        delta2 = await processor.process_chunk(S1 + S2)
        if delta2: emitted_deltas.append(delta2)
        
        delta3 = await processor.process_chunk(S1 + S2 + S3)
        if delta3: emitted_deltas.append(delta3)
        
        delta4 = await processor.process_chunk(S1 + S2 + S3 + S4)
        if delta4: emitted_deltas.append(delta4)
        
        delta5 = await processor.process_chunk(S1 + S2 + S3 + S4 + S5)
        if delta5: emitted_deltas.append(delta5)
        
        print(f"Normal progression: {len(emitted_deltas)} deltas emitted")
        
        # Now the critical test: provider restart with replay
        # This should NOT cause duplicate content to be emitted
        restart_content = S1 + S2 + FRESH  # Replays S1+S2, adds FRESH
        delta_restart = await processor.process_chunk(restart_content)
        
        if delta_restart:
            emitted_deltas.append(delta_restart)
            print(f"Restart delta: '{delta_restart[:60]}...'")
            
            # THE KEY ASSERTION: Restart delta should contain ONLY fresh content
            assert S1 not in delta_restart, f"REAL FIX FAILED: S1 replay leaked into delta: {delta_restart}"
            assert S2 not in delta_restart, f"REAL FIX FAILED: S2 replay leaked into delta: {delta_restart}"
            assert FRESH in delta_restart, f"REAL FIX FAILED: Fresh content missing from delta: {delta_restart}"
            
            print("✅ REAL FIX WORKS: No duplicate content in restart delta")
        else:
            print("✅ REAL FIX WORKS: Restart properly rejected (no delta emitted)")
        
        # Verify all emitted deltas are unique
        import hashlib
        delta_hashes = []
        for delta in emitted_deltas:
            delta_hash = hashlib.sha1(delta.encode("utf-8")).hexdigest()[:12]
            delta_hashes.append(delta_hash)
        
        unique_hashes = set(delta_hashes)
        assert len(unique_hashes) == len(delta_hashes), f"Duplicate hashes found: {delta_hashes}"
        
        print(f"✅ All {len(emitted_deltas)} deltas have unique hashes")

    @pytest.mark.asyncio
    async def test_hash_deduplication_blocks_identical_content(self):
        """Test that identical content is blocked by hash deduplication."""
        processor = EnhancedStreamingProcessor(stream_id="test-hash-dedup")
        
        content = "<h3>Test</h3>\n<p>Same content</p>"
        
        # First emission should work (may have different formatting due to markdown processing)
        delta1 = await processor.process_chunk(content)
        assert delta1 is not None, "First emission should return content"
        assert len(delta1) > 0, "First emission should not be empty"
        
        # Second emission of identical content should be blocked
        delta2 = await processor.process_chunk(content)
        assert delta2 is None, "Identical content should be blocked by hash deduplication"
        
        print("✅ Hash deduplication successfully blocks identical content")

    @pytest.mark.asyncio
    async def test_lcp_prevents_replay_edge_cases(self):
        """Test various edge cases where old logic would cause replays."""
        processor = EnhancedStreamingProcessor(stream_id="test-lcp-edge-cases")
        
        # Case 1: Normal continuation (should work)
        delta1 = await processor.process_chunk("Start")
        assert delta1 == "Start"
        
        delta2 = await processor.process_chunk("Start middle")
        assert delta2 == " middle"
        
        # Case 2: Exact replay attempt (should be blocked)
        delta3 = await processor.process_chunk("Start")
        assert delta3 is None or delta3 == "", "Exact replay should be blocked"
        
        # Case 3: Partial replay with new content (old logic would leak replay)
        delta4 = await processor.process_chunk("Start different ending")
        # With LCP logic, this should either be blocked or emit only the new part
        if delta4:
            assert "Start" not in delta4, f"Replay content leaked: {delta4}"
        
        print("✅ LCP algorithm handles edge cases correctly")

if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])