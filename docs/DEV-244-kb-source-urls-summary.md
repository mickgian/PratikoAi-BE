# DEV-244: KB Source URLs Display Fix - Summary

**Issue:** GitHub #TBD
**Status:** ✅ FIXED - Field mapping bug resolved
**Started:** January 14, 2026
**Last Updated:** January 19, 2026 (09:30)

---

## Problem Statement

KB source URLs (Fonti) were not displaying in the frontend despite the backend correctly sending them via SSE events. Additionally, specific authoritative sources (ADeR) were missing from retrieval, and Gazzetta Ufficiale URLs were broken.

**Example Query:** "Parlami della rottamazione quinquies"

| Feature | Before | After |
|---------|--------|-------|
| Fonti section visible | ❌ Not displayed | ✅ Displayed |
| Gazzetta URL works | ❌ Empty page | ✅ Loads law content |
| ADeR link included | ❌ Missing | ✅ Retrieved |

---

## Root Cause Analysis

### Issue 1: Frontend SSE Timing Bug

**File:** `src/app/chat/hooks/useChatState.ts`

**Problem:** The `kb_source_urls` SSE event is sent DURING streaming, but the reducer updated `sessionMessages`. During streaming, the message lives in `activeStreaming`, so the update was silently lost.

**Event Sequence (Bug):**
```
1. Content chunks → UPDATE_STREAMING_CONTENT (message in activeStreaming)
2. KB source URLs → SET_MESSAGE_KB_SOURCES (tries to update sessionMessages - FAILS!)
3. Done → COMPLETE_STREAMING (moves message to sessionMessages - WITHOUT kb_source_urls)
```

**Why it was hard to detect:** The backend logs showed `sources_count=1` correctly, and browser console showed the SSE event being received. But the React state update was writing to the wrong location.

### Issue 2: ADeR Missing from SOURCE_AUTHORITY

**File:** `app/services/parallel_retrieval.py`

**Problem:** The ADeR document (id=2578, "Rottamazione Quinquies - Regole Ufficiali AdER") existed in `knowledge_items` with `source=agenzia_entrate_riscossione`, but this source was NOT in the `SOURCE_AUTHORITY` dict.

**Effect:** Without authority boost, ADeR documents ranked lower than expected, often falling below the retrieval threshold.

### Issue 3: Wrong Document Code in RSS Feed

**Root Cause (CORRECTED):** The `eli/id` URL format **DOES work**. The real issue was a wrong document code stored from the RSS feed.

**Investigation Results:**
- **Wrong code:** `25G00217` (stored in database, returns empty page)
- **Correct code:** `25G00212` (actual Legge 199/2025)

**Verification:**
```
❌ https://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00217/sg → Empty page
✅ https://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00212/SG → Legge 199/2025 content
```

**NOTE:** Initial fix attempted URL format transformation (`eli/id` → `atto/serie_generale`), but this was incorrect. The `eli/id` format works fine - the issue was the document code itself.

---

## Completed Changes

### Fix 1: Frontend SSE State Management

**File:** `src/app/chat/hooks/useChatState.ts`

**Solution:** Store pending KB sources in `activeStreaming`, apply in `COMPLETE_STREAMING`.

**1. Modified `SET_MESSAGE_KB_SOURCES` reducer:**
```typescript
case 'SET_MESSAGE_KB_SOURCES': {
  const { messageId, kb_source_urls } = action as {
    type: 'SET_MESSAGE_KB_SOURCES';
    messageId: string;
    kb_source_urls: KBSourceUrl[];
  };

  // DEV-244 FIX: If message is currently streaming, store in activeStreaming
  const s = (state as any).activeStreaming;
  if (s && s.messageId === messageId) {
    return {
      ...state,
      activeStreaming: {
        ...s,
        pendingKbSources: kb_source_urls,  // Store for later
      },
    };
  }

  // Otherwise update sessionMessages (for non-streaming updates)
  return {
    ...state,
    sessionMessages: state.sessionMessages.map(msg =>
      msg.id === messageId ? { ...msg, kb_source_urls } : msg
    ),
  };
}
```

**2. Modified `COMPLETE_STREAMING` to apply pending KB sources:**
```typescript
case 'COMPLETE_STREAMING': {
  const s = (state as any).activeStreaming;
  if (!s) return state;

  // Apply any pending KB sources collected during streaming
  const aiMessage: Message = {
    id: s.messageId,
    type: 'ai',
    content: finalContent,
    timestamp: new Date().toISOString(),
    ...(s.pendingKbSources && { kb_source_urls: s.pendingKbSources }),  // DEV-244
  };
  // ...
}
```

---

### Fix 2: Add ADeR to SOURCE_AUTHORITY

**File:** `app/services/parallel_retrieval.py` (line ~55)

```python
SOURCE_AUTHORITY = {
    "gazzetta_ufficiale": 1.3,
    "agenzia_entrate": 1.2,
    "agenzia_entrate_riscossione": 1.2,  # DEV-244: ADeR official source
    "inps": 1.2,
    "corte_cassazione": 1.15,
    "ministero_economia_documenti": 0.9,
    "ministero_lavoro_news": 0.9,
}
```

---

### Fix 3: URL Transformation REVERTED

**Initial (Wrong) Approach:**
Added `_transform_gazzetta_url()` to convert `eli/id` → `atto/serie_generale` format.

**Why It Was Wrong:**
The `eli/id` format works fine. The problem was the wrong document code, not the URL format.

**Correction Applied:**
1. **Removed** `_transform_gazzetta_url()` function from `document_ingestion.py`
2. **Reverted** 9,496 URLs back to `eli/id` format using `scripts/revert_gazzetta_urls.py`

---

### Fix 4: Document Code Correction

**File:** `scripts/fix_legge_199_code.py` (NEW)

Fixed wrong document code for Legge 199/2025:

```python
# Replace wrong code with correct code
new_url = old_url.replace("25G00217", "25G00212")
# Also fix case: sg -> SG
new_url = new_url.replace("/sg", "/SG")
```

**Migration Results (Dev Database):**
- knowledge_items: 38 URLs fixed
- knowledge_chunks: 0 URLs (chunks didn't have wrong code)
- **Total: 38 URLs fixed**

**Correct URL now stored:**
```
https://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00212/SG
```

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `src/app/chat/hooks/useChatState.ts` | SSE timing bug fix - pendingKbSources pattern | ~20 |
| `app/services/parallel_retrieval.py` | Add `agenzia_entrate_riscossione` to SOURCE_AUTHORITY | 1 |
| `app/core/document_ingestion.py` | REVERTED - Removed `_transform_gazzetta_url()` | -25 |
| `scripts/revert_gazzetta_urls.py` | NEW - Revert migration script | 155 |
| `scripts/fix_legge_199_code.py` | NEW - Fix document code script | 130 |

---

## New Component: KBSourceUrls

**File:** `src/components/chat/KBSourceUrls.tsx`

Displays KB-deterministic source URLs:
- Collapsible "Fonti" section
- Shows title, URL, type, and date for each source
- PratikoAI color palette (#2A5D67 primary)
- Accessible markup with ARIA attributes

---

## Deployment Checklist

- [x] Code changes committed locally
- [x] Reverted URL transformation (9,496 URLs reverted to eli/id format)
- [x] Fixed document code 25G00217 → 25G00212 (38 URLs fixed)
- [ ] Deploy to QA (code + run migrations)
- [ ] Deploy to Prod (code + run migrations)

### Migration Commands (QA/Prod)
```bash
# 1. Revert any transformed URLs back to eli/id format
docker-compose exec app bash -c ". .venv/bin/activate && python scripts/revert_gazzetta_urls.py"

# 2. Fix wrong document code for Legge 199/2025
docker-compose exec app bash -c ". .venv/bin/activate && python scripts/fix_legge_199_code.py"
```

---

## Success Criteria

Response to "Parlami della rottamazione quinquies" must show:
- ✅ **Fonti section visible** below AI response
- ✅ **Gazzetta URL works** (loads law content when clicked)
- ✅ **ADeR URL included** (if relevant document exists)
- ✅ **Console log**: `📚 [StreamingHandler] Received KB source URLs: N`

---

## Architectural Lessons Learned

### 1. SSE Streaming State Management
**Pattern:** Events sent during streaming must update the streaming state (`activeStreaming`), not the final state (`sessionMessages`). Store pending data in streaming state, apply when streaming completes.

### 2. Source Authority Configuration
**Rule:** Always add new document sources to `SOURCE_AUTHORITY` dict when onboarding. Missing sources get no authority boost, leading to lower retrieval ranking.

### 3. Verify Before Transforming URLs
**Lesson:** Before implementing URL transformations, verify the actual cause of broken links:
- **Don't assume** format is wrong just because a link doesn't work
- **Test both formats** manually before implementing changes
- **Check document codes** - the content may be at a different URL than expected

**In this case:** The `eli/id` URL format was fine. The actual issue was the RSS feed provided a wrong document code (25G00217 instead of 25G00212).

### 4. RSS Feed Data Quality
**Rule:** RSS feed data cannot be trusted 100%. Implement verification for critical URLs:
- Spot-check high-value documents
- Consider fetching actual content to verify URLs work
- Log and alert on unexpected HTTP responses

---

## Issue 5: Slot Reservation Regression (NEW - January 15, 2026)

### Symptoms

After implementing slot reservation for official sources:

1. **ADeR link missing in ALL 4 responses** - `https://www.agenziaentrateriscossione.gov.it/...` no longer appears
2. **Response quality regression** - Detailed operational info missing

**Before (detailed response):**
- Specific dates: "30 aprile 2026", "31 luglio 2026"
- Rate details: "54 rate bimestrali", "100 euro minimum"
- 5-day tolerance note: "non sono previsti i 5 giorni di tolleranza"

**After (vaguer response):**
- Generic: "entro il termine stabilito"
- Missing: specific euro amounts, tolerance note
- Less actionable information

### Root Cause Analysis (Hypothesis)

The slot reservation fix in `_get_top_k()` reserves 3 slots for HIGH_AUTHORITY_SOURCES. But the implementation has a flaw:

**Current Logic:**
```python
official.sort(key=sort_key)  # Sort by score
top_official = official[:3]  # Take top 3 by score
```

**Problem:** If there are 5 chunks from `gazzetta_ufficiale` with higher scores than the 1 chunk from `agenzia_entrate_riscossione`, all 3 reserved slots go to Gazzetta chunks!

```
Example retrieval:
1. gazzetta_ufficiale chunk A (score 0.08) → RESERVED SLOT
2. gazzetta_ufficiale chunk B (score 0.07) → RESERVED SLOT
3. gazzetta_ufficiale chunk C (score 0.06) → RESERVED SLOT
4. agenzia_entrate_riscossione chunk (score 0.05) → NO SLOT (pushed out!)
5. ministero_lavoro_news chunk (score 0.09) → Gets remaining slot
```

**Why ADeR content is critical:**
The ADeR document contains operational details (dates, amounts, procedures) that the formal law text in Gazzetta doesn't have. Losing this document = losing detailed response quality.

### Fix Applied ✅

Reserved slots **per source type**, not just for highest-scoring official chunks:

**File:** `app/services/parallel_retrieval.py` (Lines 657-708)

```python
def _get_top_k(self, docs, k=10):
    # Step 1: Find BEST chunk per official source type (ensures diversity)
    source_best: dict[str, dict] = {}
    other: list[dict] = []

    for doc in docs:
        source = doc.get("source", "").lower()
        if source in HIGH_AUTHORITY_SOURCES:
            # Keep only the highest-scoring chunk per source type
            if source not in source_best:
                source_best[source] = doc
            elif doc.get("rrf_score", 0) > source_best[source].get("rrf_score", 0):
                source_best[source] = doc
        else:
            other.append(doc)

    # Step 2: Get diverse official sources sorted by score
    official_diverse = sorted(source_best.values(), key=sort_key)

    # Step 3: Reserve up to MAX_RESERVED_SLOTS for diverse official sources
    reserved_slots = min(MAX_RESERVED_SLOTS, len(official_diverse), k)
    top_official = official_diverse[:reserved_slots]

    # ... fill remaining with other sources
```

This ensures diversity: 1 Gazzetta + 1 ADeR + 1 INPS (if exists) instead of 3 Gazzetta chunks.

**Tests Added:**
- `test_top_k_ensures_source_diversity` - verifies ADeR is included even when multiple Gazzetta chunks have higher scores

### Fix 6: Supplemental Authority Search ✅

**File:** `app/services/parallel_retrieval.py`

**Problem:** Issue 5 fix (source diversity in `_get_top_k()`) only worked if documents reached that point. ADeR documents were being filtered out earlier in the BM25 search (didn't rank high enough in pure FTS).

**Solution:** Added a 4th parallel search that explicitly fetches from HIGH_AUTHORITY_SOURCES:

```python
# New search type weight
SEARCH_WEIGHTS = {
    "bm25": 0.3,
    "vector": 0.4,
    "hyde": 0.3,
    "authority": 0.1,  # DEV-244: Supplemental authority source search
}

# New method: _search_authority_sources()
# Runs parallel FTS queries filtered by each HIGH_AUTHORITY_SOURCE
# Returns top 2 results per source (Gazzetta, ADeR, INPS, etc.)
# Results enter RRF fusion alongside BM25/vector/HyDE

# Modified _execute_parallel_searches() to include 4th task
# Modified _rrf_fusion() to handle 4 search types
```

**Result:** Official sources like ADeR are now ALWAYS retrieved and considered, regardless of pure FTS ranking

---

## Related Issues

- **DEV-242**: Response Quality & Completeness (added SOURCE_AUTHORITY, context building fixes)
- **Phase 54**: Source URL loss during document grouping (fixed in context_builder_merge.py)

---

## Fix 7: Field Mapping Bug (January 19, 2026)

**File:** `app/core/langgraph/nodes/step_040__build_context.py` (Line 234)

**Problem:** `_build_kb_sources_metadata()` was looking for `doc.get("url")`, but `parallel_retrieval.py` stores URLs in the `source_url` field.

**Root Cause:**
```python
# parallel_retrieval.py stores:
{
    "source_url": result.source_url,  # ← Correct field name
    "metadata": {"source_url": result.source_url},
}

# step_040__build_context.py was reading:
"url": doc.get("url"),  # ← Wrong field name (always None!)
```

**Fix Applied:**
```python
# Now checks multiple fields for backwards compatibility
"url": doc.get("source_url") or doc.get("url") or doc.get("metadata", {}).get("source_url"),
```

**Effect:** KB source URLs (Gazzetta Ufficiale, ADeR, etc.) now correctly appear in the `kb_source_urls` SSE event and display in the frontend Fonti section.

---

## Fix 8: Frontend Citation Badge Styling (January 19, 2026)

**File:** `src/components/chat/KBSourceUrls.tsx`

**Problem:** KB source URLs in the "Fonti" section rendered as plain links, not with the styled `SourceCitation` badge format used elsewhere in the app.

**Fix Applied:**
```tsx
// Import citation utilities
import { SourceCitation } from '@/components/ui/source-citation';
import { isCitationUrl } from '@/config/citation-sources';

// In render loop:
const isInstitutional = isCitationUrl(source.url);

{isInstitutional ? (
  <SourceCitation citation={source.title} href={source.url} size="sm" />
) : (
  <a href={source.url}>...</a>
)}
```

**Effect:**
- Institutional sources (Gazzetta Ufficiale, ADeR, INPS, etc.) display with styled badge format
- Non-institutional sources (web articles) display as regular links
- Consistent UI across AI responses and Fonti section
