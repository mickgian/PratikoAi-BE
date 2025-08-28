# Streaming Instrumentation Implementation - Complete

## Overview
Implemented comprehensive SSE streaming instrumentation to track and identify duplicate chunk emissions. The system now provides full traceability from LLM provider through to client socket.

## Implementation Details

### TASK A - Stream Instrumentation ✅
**Enhanced `EnhancedStreamingProcessor`** (`app/core/streaming_processor.py`):
- Added `stream_id` and `seq` counter to track each stream uniquely
- Enhanced SSE frames with metadata:
  ```json
  {
    "done": false,
    "seq": 1,
    "stream_id": "session-123-timestamp",
    "acc_len": 120,
    "raw_len": 85,
    "content": "<h3>Heading</h3>",
    "sha1": "a1b2c3d4e5f6"
  }
  ```
- Added `EMIT` debug logs for every frame: 
  ```
  DEBUG EMIT seq=1 sha1=a1b2c3d4e5f6 done=False acc=120 raw=85
  ```

### TASK B - Double Iteration Guards ✅
**Created `SinglePassStream`** (`app/core/streaming_guard.py`):
```python
class SinglePassStream:
    def __aiter__(self):
        if self._used:
            raise RuntimeError("original_stream iterated twice - this would cause duplication!")
        self._used = True
        return self._agen
```

**Updated chatbot endpoint** (`app/api/v1/chatbot.py`):
- Wrapped original LLM stream with `SinglePassStream`
- Added specific exception handling for double iteration
- Ensures single code path for all streaming

### TASK C - Socket Write Logging ✅
**Created `write_sse`** (`app/core/sse_write.py`):
- Logs every frame that leaves the backend:
  ```
  DEBUG SOCKET_WRITE seq=1 sha1=a1b2c3d4e5f6 done=False acc=120 raw=85
  ```
- Parses and validates SSE frame structure
- Provides socket-level visibility

### TASK D - Wire Capture Tools ✅
**Created test scripts**:
- `test_wire_capture.sh`: Captures live SSE stream with curl
- `monitor_logs.sh`: Monitors backend logs for instrumentation
- Automated analysis of sequence numbers, checksums, and duplicate detection

## Key Detection Features

### 1. **Sequence Tracking**
- Every frame has incrementing `seq` number
- Gaps or duplicates immediately visible
- Stream-specific `stream_id` for isolation

### 2. **Content Checksums** 
- SHA1 hash of each content chunk (first 12 chars)
- Identical content produces identical hashes
- Easy duplicate detection: `sha1=abc123def456` appearing multiple times

### 3. **Accumulation Metrics**
- `acc_len`: Total HTML accumulated and emitted
- `raw_len`: Total raw input processed  
- Tracks processing vs emission ratios

### 4. **Duplicate Content Guards**
- Second-start guard logs: `Second-start detected in delta; trimming duplicate restart`
- Content discontinuity warnings
- Double iteration protection

## Monitoring Capabilities

### Real-time Stream Analysis
```bash
# Monitor live backend logs
./monitor_logs.sh

# Capture and analyze full stream  
./test_wire_capture.sh
```

### Post-Stream Analysis
```bash
# Extract frame sequence
jq -r '[.seq, .done, .sha1] | @tsv' /tmp/frames.jsonl | nl -ba

# Find duplicate content markers  
grep -n "Definizione\|Normativa" /tmp/stream.contents.html

# Verify no markdown leaked
grep -E "(###|\*\*|\*[^<])" /tmp/stream.contents.html
```

## Diagnostic Workflow

### If Duplicates Detected:
1. **Check EMIT vs SOCKET_WRITE logs**: Identify if duplication happens before or after processor
2. **Analyze sequence numbers**: Look for seq gaps or repeated sha1 hashes  
3. **Check RuntimeError**: If "iterated twice" appears, found the root cause
4. **Review content markers**: Multiple occurrences of "Definizione" etc indicate replay

### Expected Log Pattern (Normal):
```
DEBUG EMIT seq=1 sha1=abc123 done=False acc=45 raw=38
DEBUG SOCKET_WRITE seq=1 sha1=abc123 done=False acc=45 raw=38
DEBUG EMIT seq=2 sha1=def456 done=False acc=89 raw=72  
DEBUG SOCKET_WRITE seq=2 sha1=def456 done=False acc=89 raw=72
```

### Duplicate Detection Pattern:
```
DEBUG EMIT seq=5 sha1=abc123 done=False acc=200 raw=180  # Same sha1 as seq=1
WARNING Second-start detected in delta; trimming duplicate restart
```

## Benefits

### 1. **Complete Traceability**
- Every byte from LLM → Client socket tracked
- Exact sequence and content verification
- Stream isolation and identification

### 2. **Immediate Problem Detection**
- Double iteration raises exception instantly
- Content replay logged with specific details
- SHA1 mismatches show data corruption

### 3. **Performance Insights**  
- Processing efficiency (raw vs acc lengths)
- Frame generation patterns
- Streaming bottleneck identification

### 4. **Production Ready**
- DEBUG level logs (not visible in production WARNING level)
- Low overhead instrumentation
- Comprehensive error handling

## Container Status
- ✅ **Built and running**: pratikoai-be-app-1 container active
- ✅ **API healthy**: `/api/v1/health` responds correctly  
- ✅ **Instrumentation active**: All logging and guards in place
- ✅ **Ready for testing**: Full wire capture and analysis capability

## Next Steps for Testing
1. **Create authenticated session** for `/api/v1/chatbot/chat/stream`
2. **Run wire capture** with problematic prompt that previously caused duplication
3. **Analyze results** using the frame sequence and content analysis tools
4. **Compare EMIT vs SOCKET_WRITE** logs to pinpoint duplication source

The instrumentation is now complete and ready to conclusively identify any duplicate chunk emissions in the SSE streaming pipeline.