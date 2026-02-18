# SSE Streaming - Complete Implementation Guide

**Date:** November 12, 2025
**Status:** ✅ FULLY FIXED AND TESTED

---

## Overview

This document consolidates all SSE streaming fixes applied to resolve issues where responses appeared only after page refresh or got stuck on "Sto pensando..." animation.

---

## Timeline of Issues & Fixes

### Issue 1: Connection Timeout (Fixed Nov 11)
**Problem:** No response until page refresh
**Root Cause:** FastAPI StreamingResponse timeout during 7-8 second blocking `ainvoke()`
**Fix:** Added SSE keepalive comment `": starting\n\n"` in graph.py:2556
**Documentation:** `SSE_STREAMING_TDD_FIX_FINAL.md`

### Issue 2: Frontend Stuck on "Sto pensando..." (Fixed Nov 12)
**Problem:** Frontend stuck showing typing indicator with no content
**Root Cause:** SSE comment detection too permissive - caught content starting with `:`
**Fix:** Strict SSE comment detection: `chunk.startswith(': ') and chunk.endswith('\n\n')`
**Documentation:** `SSE_STREAMING_FIX_COLON_CONTENT.md`

---

## Complete Architecture

### Backend Flow

```
1. graph.py:2556
   → yield ": starting\n\n"

2. graph.py:2559
   → await ainvoke() (blocks 7-8 seconds)

3. graph.py:2872
   → yield content chunks (buffered, ~100 chars each)

4. chatbot.py:427
   → Detect SSE comments vs content
   → is_sse_comment = chunk.startswith(': ') and chunk.endswith('\n\n')

5. chatbot.py:432 (SSE comment)
   → yield chunk unchanged

6. chatbot.py:437-439 (content)
   → Wrap as SSE data event: data: {"content":"...","done":false}\n\n
```

### Frontend Flow

```
1. api.ts:788
   → Skip SSE comments (lines starting with ':')

2. api.ts:756
   → Parse SSE data events: data: {...}\n\n

3. api.ts:780
   → Call onChunk(frame) directly (no re-serialization)

4. StreamingHandler.ts:238
   → Dispatch UPDATE_STREAMING_CONTENT

5. useChatState.ts:204
   → Reconcile chunks (deduplication disabled during streaming)

6. AIMessageV2.tsx
   → Typewriter animation display
```

---

## Critical Code Sections

### 1. SSE Keepalive (graph.py:2556)

```python
# CRITICAL: Yield SSE comment immediately to establish connection
# This prevents timeout during the 7-8 second graph execution in ainvoke()
# SSE spec allows comment lines (starting with ":") which clients ignore
yield ": starting\n\n"
```

**Why:** Prevents FastAPI StreamingResponse timeout during blocking operations.

---

### 2. SSE Comment Detection (chatbot.py:427)

```python
# ============================================================================
# SSE Comment vs Content Distinction
# ============================================================================
# The graph yields two types of chunks:
#
# 1. SSE COMMENTS (Keepalives):
#    Format: ": <text>\n\n"
#    Example: ": starting\n\n"
#    Must be: colon + SPACE + text + double newline
#
# 2. CONTENT CHUNKS:
#    Format: Plain text strings (no SSE formatting)
#    Example: "Ecco le informazioni richieste..."
#    Must be: Wrapped as SSE data events for frontend
#
# CRITICAL: Content starting with ":" (e.g., ": Ecco...") is NOT an SSE comment.
# ============================================================================

# Check if this is an SSE comment (keepalive) using strict format check
is_sse_comment = chunk.startswith(': ') and chunk.endswith('\n\n')

if is_sse_comment:
    # Pass through unchanged - frontend will skip it (api.ts:788)
    yield chunk
else:
    # Wrap as proper SSE data event: data: {"content":"...","done":false}\n\n
    stream_response = StreamResponse(content=chunk, done=False)
    sse_event = format_sse_event(stream_response)
    yield write_sse(None, sse_event, request_id=request_id)
```

**Why:** Distinguishes SSE keepalives from content that happens to start with `:`.

---

### 3. Frontend SSE Parser (api.ts:788)

```typescript
// Handle SSE comments / keepalives
if (line.startsWith(':')) {
  console.log('⏭️ [API] Skipping SSE comment/keepalive:', line);
  continue;
}
```

**Why:** SSE comments are protocol-level keepalives and should not appear as content.

---

### 4. Direct Frame Processing (StreamingHandler.ts:238)

```typescript
(frame: SseFrame) => {
  if (typeof frame.content === 'string' && frame.content.length > 0) {
    this.dispatch({
      type: 'UPDATE_STREAMING_CONTENT',
      payload: {
        messageId: this.currentStreamId!,
        content: frame.content
      }
    });
  }

  if (frame.done === true && !this.hasCompleted) {
    this.hasCompleted = true;
    this.dispatch({ type: 'COMPLETE_STREAMING' });
    this.isActive = false;
  }
}
```

**Why:** Process frames directly without re-serialization to avoid nested JSON.

---

### 5. Deduplication Disabled During Streaming (useChatState.ts:204)

```typescript
// DON'T dedupe during streaming - only reconcile
// Deduplication blocks legitimate chunks and causes incomplete responses
// const deduped = collapseDuplicatesAll(merged)  // DISABLED DURING STREAMING

if (merged === prevFull) return state

return {
  ...state,
  activeStreaming: {
    ...s,
    content: merged,  // Use merged directly, not deduped
    visibleLen: newVisibleLen
  }
}
```

**Why:** Aggressive deduplication during streaming blocks legitimate chunks.

---

## Test Coverage

### Backend Tests (59 tests)
- ✅ `tests/api/test_sse_formatter.py` (11 tests) - SSE format validation
- ✅ `tests/api/test_sse_comment_detection.py` (13 tests) - Comment vs content
- ✅ `tests/api/test_sse_keepalive_timing.py` (9 tests) - Timing and regression
- ✅ `tests/unit/core/test_sse_write_helper.py` (19 tests) - Logging helper
- ✅ `tests/api/test_chatbot_streaming_real.py` (7 tests) - Integration tests

### Frontend Tests
- ✅ `src/lib/__tests__/api.sse.test.ts` (10 tests) - SSE parser
- ✅ `src/app/chat/handlers/__tests__/StreamingHandler.test.ts` (11 tests) - Handler
- ✅ `e2e/streaming.spec.ts` (7 tests) - End-to-end

### Pre-Commit Hook
```yaml
- id: streaming-tests
  entry: python -m pytest tests/api/test_sse_formatter.py tests/api/test_sse_comment_detection.py tests/api/test_sse_keepalive_timing.py tests/unit/core/test_sse_write_helper.py -v --tb=line -x --timeout=30
```

**Execution Time:** ~3 seconds
**Purpose:** Prevent streaming regressions on every commit

---

## Failure Modes & Prevention

### Failure Mode 1: Connection Timeout
**Symptom:** No response until page refresh
**Cause:** No data yielded during blocking operation
**Prevention:** SSE keepalive must be sent immediately
**Test:** `test_keepalive_sent_before_blocking_operation()`

### Failure Mode 2: Content Treated as SSE Comment
**Symptom:** Frontend stuck on "Sto pensando..."
**Cause:** Content starting with `:` detected as SSE comment
**Prevention:** Strict comment detection (requires `: ` and `\n\n`)
**Test:** `test_old_buggy_logic_vs_new_fixed_logic()`

### Failure Mode 3: Re-serialization Bug
**Symptom:** Invalid nested JSON
**Cause:** `JSON.stringify(frame)` on already-parsed object
**Prevention:** Process frames directly
**Test:** Frontend StreamingHandler tests

### Failure Mode 4: Aggressive Deduplication
**Symptom:** Incomplete responses
**Cause:** KMP algorithm blocking legitimate chunks
**Prevention:** Disable deduplication during streaming
**Test:** useChatState tests

---

## Verification Checklist

- [x] Backend sends SSE keepalive `": starting\n\n"` immediately
- [x] Connection established within 10 seconds
- [x] All chunks delivered without drops
- [x] Frontend displays "Sto pensando..." during wait
- [x] Streaming starts immediately after first chunk
- [x] No character-by-character delays
- [x] Links render with icon (not raw text)
- [x] Complete response visible without refresh
- [x] No console errors
- [x] All backend tests pass (59/59)
- [x] All frontend tests pass
- [x] Pre-commit hook prevents regressions

---

## Related Documentation

- **Latest Fix:** `SSE_STREAMING_FIX_COLON_CONTENT.md` - Colon content bug fix
- **Original TDD Fix:** `SSE_STREAMING_TDD_FIX_FINAL.md` - Initial TDD implementation
- **Test Status:** `TESTING_IMPLEMENTATION_STATUS.md` - Current test coverage

---

## Quick Commands

### Run All Streaming Tests
```bash
# Backend tests
pytest tests/api/test_sse_*.py tests/unit/core/test_sse_write_helper.py -v

# Frontend tests
cd web
npm test -- --testPathPattern=streaming

# E2E tests
npm run test:e2e -- streaming.spec.ts
```

### Debug Streaming Issues
```bash
# Watch backend SSE logs
tail -f logs/streaming.log | grep SSE

# Monitor frontend chunks
# Open browser DevTools → Console → Filter: "[API]"
```

---

## Best Practices

1. **Always Send Keepalive:** Before any blocking operation > 1 second
2. **Strict SSE Comment Detection:** Use `startswith(': ')` AND `endswith('\n\n')`
3. **No Re-serialization:** Process parsed frames directly
4. **Disable Deduplication During Streaming:** Enable only after COMPLETE_STREAMING
5. **Comprehensive Comments:** Document why each check exists to prevent regressions
6. **Test Everything:** Unit, integration, and E2E tests for all critical paths

---

**Status:** Production-ready ✅
**Last Updated:** November 12, 2025
**Maintainer:** Development Team
