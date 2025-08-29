"""
Minimal reproduction tests for streaming duplication bug.

Tests synthetic chunk sequences to identify root cause of duplicate emissions.
Focuses on 3 scenarios that could cause the observed duplication pattern.
"""

import pytest
import asyncio
from app.core.streaming_processor import EnhancedStreamingProcessor
from app.core.hash_gate import HashGate


class TestStreamingDuplication:
    """Test cases to reproduce streaming duplication scenarios."""
    
    @pytest.fixture
    def processor(self):
        """Create a fresh processor for each test."""
        return EnhancedStreamingProcessor(stream_id="test-stream-001", enable_hash_gate=True)
    
    @pytest.fixture 
    def hash_gate(self):
        """Create hash gate for duplicate detection."""
        return HashGate(stream_id="test-stream-001")

    @pytest.mark.asyncio
    async def test_case_a_normal_monotonic_growth(self, processor, hash_gate):
        """
        Test Case A: Normal monotonic growth (should work correctly).
        
        Simulates ideal provider behavior with incremental content additions.
        Expected: No duplicates, clean delta emission.
        """
        chunks = [
            "### Legal Framework\n\n",
            "### Legal Framework\n\n1. **Definizione**: Il decreto",
            "### Legal Framework\n\n1. **Definizione**: Il decreto legislativo",
            "### Legal Framework\n\n1. **Definizione**: Il decreto legislativo n. 231/2001"
        ]
        
        expected_deltas = [
            "<h3>Legal Framework</h3>",
            "<ol>\n<li><strong>Definizione</strong>: Il decreto</li>\n</ol>",
            " legislativo",
            " n. 231/2001"
        ]
        
        emitted_deltas = []
        seq = 0
        
        for i, chunk in enumerate(chunks):
            delta = await processor.process_chunk(chunk)
            if delta:
                seq += 1
                # Check for duplicates using hash gate
                hash_gate.check_delta(delta, seq)
                emitted_deltas.append(delta)
                print(f"Seq {seq}: '{delta[:50]}...'")
        
        # Verify monotonic behavior - each delta should be unique
        assert len(emitted_deltas) > 0, "Should emit at least one delta"
        
        # Verify no exact duplicate deltas
        delta_set = set(emitted_deltas)
        assert len(delta_set) == len(emitted_deltas), f"Duplicate deltas found: {emitted_deltas}"
        
        # Verify accumulated HTML grows monotonically
        assert len(processor.accumulated_html) >= len(chunks[-1]), "HTML should grow with input"

    @pytest.mark.asyncio
    async def test_case_b_provider_restart_scenario(self, processor, hash_gate):
        """
        Test Case B: Provider-style restart (most likely bug source).
        
        Simulates OpenAI provider restarting stream with partial overlap.
        This matches observed pattern: clean start, then sudden restart.
        Expected: Should detect and handle restart gracefully.
        """
        chunks = [
            "### Legal Framework\n\n",
            "### Legal Framework\n\n1. **Definizione**: Il decreto",
            "### Legal Framework\n\n1. **Definizione**: Il decreto legislativo", 
            # RESTART: Provider begins again from earlier point (THIS IS THE BUG)
            "### Legal Framework\n\n1. **Definizione**: Il decreto legislativo completo",
            "### Legal Framework\n\n1. **Definizione**: Il decreto legislativo completo\n\n2. **Normativa**: Nuova sezione"
        ]
        
        emitted_deltas = []
        seq = 0
        duplicate_detected = False
        
        for i, chunk in enumerate(chunks):
            try:
                delta = await processor.process_chunk(chunk)
                if delta:
                    seq += 1
                    # Try to detect duplicates - this should catch the bug
                    hash_gate.check_delta(delta, seq)
                    emitted_deltas.append(delta)
                    print(f"Seq {seq}: '{delta[:50]}...'")
            except RuntimeError as e:
                if "Duplicate hash" in str(e):
                    duplicate_detected = True
                    print(f"DUPLICATE DETECTED at seq {seq}: {e}")
                    break
        
        # This test SHOULD detect the duplicate emission pattern
        print(f"Total deltas emitted: {len(emitted_deltas)}")
        print(f"Duplicate detected by hash gate: {duplicate_detected}")
        
        # Analyze the pattern
        if len(emitted_deltas) >= 2:
            delta1, delta2 = emitted_deltas[0], emitted_deltas[1] 
            if delta1 == delta2:
                print(f"EXACT DUPLICATE FOUND: '{delta1}' == '{delta2}'")
                assert False, "Found exact duplicate delta emission - this is the bug!"

    @pytest.mark.asyncio
    async def test_case_c_format_flip_scenario(self, processor, hash_gate):
        """
        Test Case C: Format flip HTML->Markdown->HTML.
        
        Tests hypothesis that format detection causes state confusion.
        Expected: Should handle format changes gracefully.
        """
        chunks = [
            "<h3>Legal Framework</h3>\n",  # HTML first
            "### Legal Framework\n\n**Bold text**",  # Switch to markdown
            "### Legal Framework\n\n**Bold text**\n\n1. List item"  # More markdown
        ]
        
        emitted_deltas = []
        seq = 0
        
        for i, chunk in enumerate(chunks):
            delta = await processor.process_chunk(chunk)
            if delta:
                seq += 1
                hash_gate.check_delta(delta, seq)
                emitted_deltas.append(delta)
                print(f"Seq {seq}: Format flip - '{delta[:50]}...'")
        
        # Verify all deltas are in HTML format (no markdown leakage)
        for delta in emitted_deltas:
            assert "###" not in delta, f"Markdown header leaked in delta: {delta}"
            assert "**" not in delta or "<strong>" in delta, f"Markdown bold leaked: {delta}"

    @pytest.mark.asyncio 
    async def test_hypothesis_h1_normalization_drift(self, processor):
        """
        H1: Accumulated HTML != normalize(accumulated_raw) causing delta miscalculation.
        
        Test if normalization drift causes the same content to be computed as delta twice.
        """
        # Force a scenario where HTML might drift from raw normalization
        chunk1 = "### Test\n\n**Bold**"
        chunk2 = "\n\nMore content"
        
        # Process first chunk
        delta1 = await processor.process_chunk(chunk1)
        accumulated_after_1 = processor.accumulated_html
        raw_after_1 = processor.accumulated_raw
        
        print(f"After chunk 1:")
        print(f"  Raw: '{raw_after_1}'")
        print(f"  Accumulated HTML: '{accumulated_after_1}'")
        print(f"  Delta: '{delta1}'")
        
        # Process second chunk  
        delta2 = await processor.process_chunk(chunk2)
        accumulated_after_2 = processor.accumulated_html
        raw_after_2 = processor.accumulated_raw
        
        print(f"After chunk 2:")
        print(f"  Raw: '{raw_after_2}'") 
        print(f"  Accumulated HTML: '{accumulated_after_2}'")
        print(f"  Delta: '{delta2}'")
        
        # H1 TEST: Check if normalize(accumulated_raw) == accumulated_html
        normalized_raw = processor._normalize_to_html(processor.accumulated_raw)
        
        print(f"Normalized raw: '{normalized_raw}'")
        print(f"Accumulated HTML: '{processor.accumulated_html}'")
        
        if normalized_raw != processor.accumulated_html:
            print("H1 CONFIRMED: Normalization drift detected!")
            assert False, f"H1 BUG: normalize(raw)='{normalized_raw}' != accumulated='{processor.accumulated_html}'"

    @pytest.mark.asyncio
    async def test_hypothesis_h4_double_writer(self, processor):
        """
        H4: Same delta written twice to socket (double emission).
        
        Test if the same delta gets emitted multiple times.
        """
        chunk = "### Test Content\n\nSome text here."
        
        # Process chunk and capture what would be emitted
        delta = await processor.process_chunk(chunk)
        
        if delta:
            # Simulate the emission path multiple times
            frame1 = processor.format_sse_frame(content=delta, done=False)
            frame2 = processor.format_sse_frame(content=delta, done=False)  # DOUBLE WRITE
            
            print(f"Frame 1: {frame1}")
            print(f"Frame 2: {frame2}")
            
            # Parse JSON to compare
            import json
            data1 = json.loads(frame1.replace("data: ", "").strip())
            data2 = json.loads(frame2.replace("data: ", "").strip())
            
            # H4 TEST: Check if same content gets different seq numbers
            if data1["sha1"] == data2["sha1"] and data1["seq"] != data2["seq"]:
                print(f"H4 CONFIRMED: Same SHA1 {data1['sha1']} with different seq {data1['seq']} vs {data2['seq']}")
                assert False, "H4 BUG: Same content emitted with different sequence numbers!"

    @pytest.mark.asyncio
    async def test_hypothesis_h2_overlap_logic_bug(self, processor):
        """
        H2: Bug in _compute_delta overlap detection logic.
        
        Test if overlap detection incorrectly calculates deltas.
        """
        # Create a scenario where accumulated is contained in new content
        chunk1 = "Start"
        chunk2 = "Start middle end"  # Contains "Start" from chunk1
        
        delta1 = await processor.process_chunk(chunk1)
        print(f"Delta 1: '{delta1}'")
        print(f"Accumulated after 1: '{processor.accumulated_html}'")
        
        delta2 = await processor.process_chunk(chunk2)
        print(f"Delta 2: '{delta2}'")
        print(f"Accumulated after 2: '{processor.accumulated_html}'")
        
        # H2 TEST: Delta2 should be " middle end", not contain "Start" again
        if delta2 and "Start" in delta2:
            assert False, f"H2 BUG: Delta contains already-emitted content: '{delta2}'"

    @pytest.mark.asyncio  
    async def test_hypothesis_h3_concurrent_caller(self, processor):
        """
        H3: Concurrent callers to process_chunk.
        
        Test if concurrent processing causes state corruption.
        """
        import asyncio
        
        # Simulate concurrent processing
        chunk1 = "### First\n\nContent A"
        chunk2 = "### Second\n\nContent B"
        
        async def process_with_delay(chunk, delay):
            await asyncio.sleep(delay)
            return await processor.process_chunk(chunk)
        
        # Start both processes concurrently
        results = await asyncio.gather(
            process_with_delay(chunk1, 0.001),
            process_with_delay(chunk2, 0.002)
        )
        
        print(f"Concurrent results: {results}")
        print(f"Final accumulated: '{processor.accumulated_html}'")
        
        # H3 TEST: State should be consistent (no interleaved corruption)
        # This is hard to test deterministically, but corruption would show mixed content
        if processor.accumulated_html and "FirstSecond" in processor.accumulated_html.replace(" ", ""):
            print("WARNING: H3 possible - concurrent state mixing detected")

    @pytest.mark.asyncio
    async def test_hypothesis_h5_state_update_order(self, processor):
        """
        H5: State update happens before delta computation.
        
        Test if accumulated_html is updated before computing delta, causing miscalculation.
        """
        chunk1 = "### Test\n\nFirst part"
        chunk2 = "### Test\n\nFirst part\n\nSecond part"
        
        # Process first chunk
        delta1 = await processor.process_chunk(chunk1)
        state_after_1 = processor.accumulated_html
        
        print(f"After chunk 1: accumulated='{state_after_1}' delta='{delta1}'")
        
        # Manually inspect what _compute_delta would do for chunk2
        processor.accumulated_raw += "\n\nSecond part"
        new_normalized = processor._normalize_to_html(processor.accumulated_raw)
        
        print(f"Before compute_delta: accumulated='{processor.accumulated_html}'")
        print(f"Would normalize to: '{new_normalized}'")
        
        # If accumulated_html was updated BEFORE delta computation, this would be wrong
        theoretical_delta = processor._compute_delta(new_normalized)
        print(f"Theoretical delta: '{theoretical_delta}'")
        
        # Reset and do actual processing
        processor.accumulated_raw = chunk1  # Reset raw state
        delta2 = await processor.process_chunk("\n\nSecond part")
        
        print(f"Actual delta2: '{delta2}'")
        
        # H5 TEST: Theoretical and actual should match
        if theoretical_delta != delta2:
            print(f"H5 POTENTIAL: theoretical='{theoretical_delta}' != actual='{delta2}'")

if __name__ == "__main__":
    # Run specific test for quick debugging
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "restart":
        # Focus on the restart scenario - most likely root cause
        pytest.main(["-v", "-s", "test_streaming_repro.py::TestStreamingDuplication::test_case_b_provider_restart_scenario"])
    else:
        # Run all tests
        pytest.main(["-v", "-s", "test_streaming_repro.py"])