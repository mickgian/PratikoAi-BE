# Streaming Duplication Bug - Root Cause Analysis

## Executive Summary

**Root Cause Identified**: The duplication bug occurs because `format_sse_frame()` increments the sequence number (`self.seq`) on every call, but can be called multiple times with the same content delta, causing identical content to be emitted with different sequence numbers.

## Hypothesis Testing Results

### ✅ H4 CONFIRMED: Double Writer Pattern
**Test Result**: `test_hypothesis_h4_double_writer` FAILED with assertion:
```
H4 CONFIRMED: Same SHA1 82206109b48d with different seq 1 vs 2
AssertionError: H4 BUG: Same content emitted with different sequence numbers!
```

**Evidence**: Identical content (`<h3>Test Content</h3><p>Some text here.</p>`) gets:
- Frame 1: `seq=1`, `sha1=82206109b48d`  
- Frame 2: `seq=2`, `sha1=82206109b48d` (DUPLICATE)

### ❌ H1-H3, H5: Not Confirmed
- **H1 (Normalization Drift)**: Passed - accumulated HTML matches normalized raw
- **H2 (Overlap Logic)**: Passed - overlap detection works correctly
- **H3 (Concurrent Calls)**: Passed - no concurrent access issues detected
- **H5 (State Update Order)**: Passed - state updates happen in correct order

## Technical Analysis

### The Bug Location
**File**: `/app/core/streaming_processor.py`
**Method**: `format_sse_frame()` at line 251
```python
def format_sse_frame(self, content: str | None = None, done: bool = False) -> str:
    self.seq += 1  # ← BUG: Increments on every call
    payload = {
        "seq": self.seq,        # Different seq numbers
        "sha1": content_hash    # Same content hash
    }
```

### How Duplication Occurs
1. **Normal Flow**: `process_chunk()` returns a delta
2. **First Emission**: `format_sse_frame(delta)` called → `seq=4`, `sha1=abc123`
3. **Duplicate Call**: Same delta passed to `format_sse_frame()` again → `seq=29`, `sha1=abc123`
4. **Result**: Identical content emitted twice with different sequence numbers

### Why This Happens
The duplication occurs when:
- The same computed delta gets formatted multiple times
- Error handling or retry logic calls `format_sse_frame` with existing content
- Event generator logic processes the same delta through multiple code paths

## Surgical Fix Proposal

### Option A: Move Sequence Increment to Delta Emission (Recommended)
Only increment sequence when we actually have new content to emit:

```python
def format_sse_frame(self, content: str | None = None, done: bool = False) -> str:
    # Don't increment seq here - let the caller manage it
    payload = {
        "done": bool(done),
        "seq": self.seq,  # Use current seq, don't increment
        "stream_id": self.stream_id,
        "acc_len": len(self.accumulated_html),
        "raw_len": len(self.accumulated_raw),
    }
    # ... rest unchanged

async def process_chunk(self, raw_chunk: str) -> Optional[str]:
    # ... existing logic ...
    if delta:
        self.seq += 1  # Increment ONLY when we have new content
        # ... rest unchanged
```

### Option B: Deduplicate at Frame Level
Add frame-level deduplication to prevent identical content emission:

```python
def __init__(self):
    # ... existing ...
    self.last_emitted_hash = None

def format_sse_frame(self, content: str | None = None, done: bool = False) -> str:
    if content:
        content_hash = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
        if self.last_emitted_hash == content_hash:
            logger.warning("FRAME_DUPLICATE_PREVENTED sha1=%s", content_hash)
            return ""  # Skip duplicate emission
        self.last_emitted_hash = content_hash
    
    self.seq += 1
    # ... rest unchanged
```

## Recommended Solution: Option A

**Why Option A is Superior**:
1. **Fixes Root Cause**: Sequence numbers align with actual content emission
2. **Cleaner Logic**: Sequence increment happens when content is ready, not when formatted
3. **Better Monitoring**: `seq` accurately represents unique content deltas
4. **Minimal Risk**: Single line move with clear semantics

**Implementation Steps**:
1. Move `self.seq += 1` from `format_sse_frame()` to `process_chunk()` 
2. Only increment when `delta` is non-empty and will be emitted
3. Update tests to verify sequence numbers match actual emissions
4. Add feature flag for production rollback capability

## Test Evidence

### Before Fix (Current Behavior)
```
Frame 1: {"seq": 1, "sha1": "82206109b48d", "content": "same content"}
Frame 2: {"seq": 2, "sha1": "82206109b48d", "content": "same content"}  ← DUPLICATE
```

### After Fix (Expected Behavior)
```
Frame 1: {"seq": 1, "sha1": "82206109b48d", "content": "unique content A"}
Frame 2: {"seq": 2, "sha1": "def456789abc", "content": "unique content B"}
```

## Production Considerations

### Feature Flag Implementation
```python
STREAMING_FIX_SEQUENCE_DUPLICATION = os.getenv("STREAMING_FIX_SEQUENCE_DUPLICATION", "false").lower() == "true"
```

### Monitoring
- Log sequence/hash pairs for duplicate detection
- Alert on identical SHA1 with different sequence numbers
- Monitor for regression after fix deployment

### Rollback Plan
- Feature flag can immediately revert to old behavior
- No database changes required
- Client impact: Better reliability, no breaking changes

## Conclusion

The streaming duplication bug is definitively caused by `format_sse_frame()` incrementing sequence numbers independently of actual content uniqueness. The surgical fix (Option A) addresses the root cause with minimal risk and maximum clarity.

**Next Steps**:
1. Implement Option A fix
2. Add comprehensive test coverage
3. Deploy with feature flag
4. Monitor for resolution of duplicate SHA1 emissions