# RAG Flow Analysis & Fix Plan

**← Prerequisites**: [RAG_FLOW_IMPLEMENTATION_01_hybrid_architecture.md](./RAG_FLOW_IMPLEMENTATION_01_hybrid_architecture.md) (Phases 0-8 complete)

---

## 📋 EXECUTIVE SUMMARY

**PROBLEM**: RAG execution flow doesn't match `@docs/architecture/diagrams/pratikoai_rag.mmd` diagram.

**ROOT CAUSE**:
1. Frontend uses `/chat/stream` which bypasses ALL graphs
2. 59 nodes ARE wired but in SEPARATE isolated lane graphs
3. Lanes are NOT connected together in execution flow order

**ARCHITECTURE**: Tiered Graph Hybrid (nodes + orchestrators)
- ✅ 59 nodes wired in unified graph (all lanes connected)
- ✅ 135 orchestrators implemented (steps 1-135, 100% coverage)
- ✅ 27 canonical nodes defined, 27 implemented (100%)
- ✅ Lanes connected in single execution flow (1→2→3→4→5→6→7→8)

**SOLUTION**:
1. ✅ Create node wrappers for steps 31, 42 (2 files, 45 min) - COMPLETED
2. ✅ Connect all 8 lanes into unified graph (2.5 hours) - COMPLETED
3. Make `/chat/stream` use unified graph with streaming (1-2 hours)

**STATUS**: Phases 2-3 ✅ COMPLETED. Ready for Phase 4 (streaming integration).

---

## 🔴 PROBLEM IDENTIFIED

The current execution **DOES NOT** follow the `@docs/architecture/diagrams/pratikoai_rag.mmd` flow diagram.

## 📊 Expected Flow (per Diagram)

```
S001: ValidateRequest
↓
S002-S010: GDPR, Privacy, PII
↓
S011-S019: Convert messages, extract facts, canonicalize, query signature
↓
S020: Golden Fast Path Gate ← EARLY
↓
S031-S039: Classification, domain scoring, KB prefetch
↓
S041-S047: Prompt selection
↓
S048-S050: Provider selection
↓
S059-S062: Cache check
↓
S064: LLM Call ← LAST
```

## ❌ Current Execution (from trace)

```
Unknown entry point
↓
Step 64: LLM Call (14:58:20.972) - FIRST! ❌
↓
Step 20: Golden gate (14:58:20.975) - AFTER LLM! ❌
↓
Steps 41-47: Prompt selection (14:58:20.976-983) - AFTER LLM! ❌
↓
Steps 48-50: Provider selection (14:58:20.983-986) - AFTER LLM! ❌
```

**Steps 1-19, 31-39 are MISSING entirely.**

## 🔍 ROOT CAUSE ANALYSIS

### 1. TWO EXECUTION PATHS EXIST

#### Path A: Phase 1A Graph (INTENDED)
- **Entry**: `/api/v1/chat` → `agent.get_response()` → `self._graph.ainvoke()`
- **Nodes**: ValidateRequest(1) → ValidCheck(3) → PrivacyCheck(6) → PIICheck(9) → CheckCache(59) → CacheHit(62) → LLMCall(64) → LLMSuccess(67) → End(112)
- **Missing**: Steps 11-19, 20, 31-50 are NOT in the graph
- **File**: `app/core/langgraph/graph.py:1085-1137` (create_graph_phase1a)

#### Path B: Direct LLM Streaming (BEING USED)
- **Entry**: `direct_llm_stream()` or `_stream_with_direct_llm()`
- **Flow**:
  1. `_classify_user_query()` (no logging)
  2. `_check_golden_fast_path_eligibility()` → logs Step 20
  3. `_get_system_prompt()` → logs Steps 41-47
  4. `_get_optimal_provider()` → logs Steps 48-50
  5. `provider.chat_completion()` → logs Step 64
- **Missing**: Steps 1-19, 31-39
- **File**: `app/core/langgraph/graph.py:1777-1819` (_stream_with_direct_llm)

### 2. TRACE SHOWS PATH B IS EXECUTING

Evidence:
- Step 64 appears FIRST (with latency 2723ms from provider)
- Steps 20, 41-50 appear AFTER step 64
- Steps 1-19, 31-39 never appear
- Execution order: 64 → 20 → 41-47 → 48-50

**Why Step 64 appears FIRST (timestamp inversion)**:
- `rag_step_timer()` logs when context EXITS (after LLM call completes)
- Steps 20, 41-50 log IMMEDIATELY when called
- But Step 64's timer STARTS first (before calling LLM)
- Async execution + file buffering causes Step 64 log to appear first in file
- Actual execution order is: 20 → 41-50 → START Step 64 → (2.7s LLM call) → END Step 64

### 3. WHY PATH B IS BEING USED

**✅ MYSTERY SOLVED**: Frontend uses `/chat/stream` which bypasses ALL graphs!

**Evidence**:
- `/chat/stream` endpoint (line 192 in chatbot.py) calls `agent.get_stream_response()`
- `get_stream_response()` (line 1716 in graph.py) BYPASSES the LangGraph entirely
- It directly calls internal methods, not graph nodes
- Default graph is Phase 1A (only 9 nodes), not unified flow

**Why steps are missing**:
- Lane 1 (1-10): Not executed (no graph call)
- Lane 2 (11-19): Not executed
- Lane 3 (20-30): `_check_golden_fast_path_eligibility()` logs Step 20 only
- Lane 4 (31-40): `_classify_user_query()` internal, no logging
- Lane 5 (41-47): `_get_system_prompt()` logs Steps 41-47
- Lane 6 (48-58): `_get_optimal_provider()` logs Steps 48-50
- Lane 7 (59-99): Provider logs Step 64
- Lane 8 (104-112): Not executed

**Actual graph state**:
- 57 nodes wired in separate `create_graph_phaseX_lane()` functions
- Phase 1A graph (9 nodes) is default but not used by `/chat/stream`
- Lanes exist but are NOT connected together

## 🎯 KEY INSIGHTS

**1. Tiered Graph Hybrid Architecture** (per `docs/architecture/RAG-architecture-mode.md`)
- **Nodes** = Runtime boundaries (59 implemented across 8 lanes)
- **Orchestrators** = Business logic (135 steps 1-135, 100% coverage)
- **Internal** = Pure transforms inside nodes (no separate nodes)
- **Canonical Set** = 27 nodes defined, 27 implemented (100%)

**2. Current State**
- ✅ 59 nodes wired in SEPARATE lane graphs (27/27 canonical + 32 internal)
- ✅ 135 orchestrators exist for steps 1-135 (100% complete)
- ✅ All 27 canonical node wrappers complete (Phase 2 done)
- ❌ Lanes NOT connected (isolated graphs)
- ❌ `/chat/stream` bypasses ALL graphs

**3. The Solution**
- ✅ Create 2 missing canonical node wrappers (steps 31, 42) - COMPLETED
- Connect all 8 lanes into unified graph
- Make `/chat/stream` use unified graph with streaming

## 🔧 FIX PLAN

### Phase 1: Identify Routing Logic ✅ COMPLETED
**Goal**: Understand why `get_response()` is using Path B instead of Path A

**Tasks**:
1. ✅ Read `app/core/langgraph/graph.py:1637-1682` (get_response method)
2. ✅ Trace what happens when Phase 1A graph's "LLMCall" node executes
3. ✅ Check if node_step_64 is calling the legacy _chat() or _stream_with_direct_llm()
4. ✅ Check if there's any conditional routing that bypasses the graph

**FINDINGS**:
- Frontend uses `/chat/stream` which calls `get_stream_response()` (line 1716)
- `get_stream_response()` completely BYPASSES the LangGraph
- It calls methods directly: classify → golden check → direct LLM stream
- Phase 1A graph is ONLY used by `/chat` (non-streaming) which frontend doesn't use
- **FIX STRATEGY**: Modify `get_stream_response()` to use the graph with streaming

### Phase 2: Create Missing Canonical Node Wrappers ✅ COMPLETED

**Status**: ✅ Implemented

**Goal**: Complete canonical node set (27 nodes) to 100%

**Final state**:
- ✅ 135 orchestrators exist (steps 1-135, 100% coverage)
- ✅ 27/27 canonical nodes implemented (100%)
- ✅ All canonical node wrappers complete

**Tasks**:
1. ✅ Create `step_031__classify_domain.py`
   - Calls `step_31__classify_domain()` from `app/orchestrators/classify.py:210`
   - Adds rag_step_log/timer, updates RAGState
   - Follow pattern from `step_048__select_provider.py`

2. ✅ Create `step_042__class_confidence.py`
   - Calls `step_42__class_confidence()` from `app/orchestrators/classify.py:562`
   - Adds rag_step_log/timer, updates RAGState
   - Follow pattern from `step_048__select_provider.py`

3. ✅ Register in `app/core/langgraph/nodes/__init__.py`

**Note**: Steps 32-41, 43-47 are **Internal** per architecture (no node wrappers needed)

**Implementation notes**:
- Created `app/core/langgraph/nodes/step_031__classify_domain.py` with 4 test cases (all passing)
- Created `app/core/langgraph/nodes/step_042__class_confidence.py` with 4 test cases (all passing)
- Created `tests/langgraph/test_step_031__classify_domain.py` - 4/4 tests passing
- Created `tests/langgraph/test_step_042__class_confidence.py` - 4/4 tests passing
- Updated `app/core/langgraph/nodes/__init__.py` with imports and exports
- Both nodes follow established pattern: thin delegation, rag_step_log/timer, proper RAGState mapping
- TDD methodology used: tests written first, then implementation
- Test results: 8/8 passing

**Actual time**: 45 minutes

### Phase 3: Create Unified Graph ✅ COMPLETED

**Status**: ✅ Implemented

**Goal**: Connect all 8 lanes into single execution flow

**Final state**:
- ✅ Lane graphs exist separately (Phases 4-8)
- ✅ All lanes connected in unified graph
- ✅ 59 nodes wired with conditional edges

**Tasks**:
1. ✅ Create `create_graph_unified()` function
2. ✅ Wire all lanes in EXECUTION ORDER:
   ```
   Lane 1: Request/Privacy (1→3→4→6→7→9→10→8)
     ↓
   Lane 2: Messages (11→12→13)
     ↓
   Lane 3: Golden/KB (20→24→25→26→27→28→30)
     ↓
   Lane 4: Classification (31, 42) [steps 32-40 are internal]
     ↓
   Lane 5: Prompts [steps 41, 43-47 are internal in SelectProvider]
     ↓
   Lane 6: Provider (48→49→50→51/52/53/54→55→56→57/58)
     ↓
   Lane 7: Cache/LLM (59→62→64→67→68/69→70→72/73→74→75→79→80/81/82/83→99)
     ↓
   Lane 8: Streaming (104→105→106→107→108→109→110→111→112)
   ```
3. ✅ Add conditional edges between lanes (10 new routing functions)
4. ✅ Change default: line 2011 → `create_graph_unified()`

**Implementation notes**:
- Created `create_graph_unified()` at `app/core/langgraph/graph.py:1642-1924`
- Added 13 node imports (Lane 2, 3, and 4 nodes)
- Wired all 59 existing nodes with proper conditional edges
- Added 10 new routing functions for unified flow:
  - `_route_from_privacy_check_unified`
  - `_route_from_pii_check_unified`
  - `_route_from_golden_fast_gate`
  - `_route_from_golden_hit`
  - `_route_from_kb_delta`
  - `_route_from_strategy_type`
  - `_route_from_cost_check`
  - `_route_from_cache_hit_unified`
  - `_route_from_llm_success_unified`
  - `_route_from_stream_check`
- Updated default graph in `create_graph()` to use unified graph
- Verified syntax compilation

**Actual time**: 2.5 hours

### Phase 4: Enable Streaming with Unified Graph ⚠️ PRIORITY 3
**Goal**: Make `/chat/stream` use unified graph with streaming (Option B - Hybrid)

**Current issue**:
- `/chat/stream` calls `get_stream_response()` which bypasses ALL graphs
- Line 1716: directly calls internal methods

**Fix Strategy (Option B - Hybrid)**:
1. ⬜ Modify `get_stream_response()`:
   ```python
   async def get_stream_response(self, messages, session_id, user_id):
       # Execute unified graph up to Step 64
       state = await self._graph.ainvoke({
           "messages": messages,
           "session_id": session_id,
       })

       # Stream Step 64 directly (existing proven code)
       provider = state["provider"]["selected"]
       async for chunk in provider.stream_completion(state["processed_messages"]):
           yield chunk
   ```
2. ⬜ Keep existing streaming logic (proven, less risky)
3. ⬜ Test streaming maintains UX quality

**Why Option B (not Option A)**:
- Matches Tiered Hybrid architecture
- Reuses proven streaming code
- Less risky than pure LangGraph streaming
- Faster implementation

**Time estimate**: 1-2 hours

### Phase 5: Remove Duplicate Logging
**Goal**: Stop double-logging Step 64 (AFTER streaming works)

**Current issue**:
- `OpenAIProvider.chat_completion()` logs Step 64 with timer (line 163)
- `step_64__llmcall()` also logs Step 64 with timer (line 1156)

**Fix**:
1. ⬜ Remove `rag_step_timer` from OpenAIProvider.chat_completion()
2. ⬜ Keep logging only in step_64__llmcall orchestrator
3. ⬜ OR: Provider logs "llm_api_call_started" and "llm_api_call_completed" as sub-steps

### Phase 6: Add Missing Step Logging
**Goal**: Log steps 1-10 in chatbot controller (AFTER streaming works)

**Current issue**:
- Lines 61-96 in chatbot.py use `logger.info()` instead of `rag_step_log()`
- Steps 1, 4, 7, 10 don't appear in trace

**Fix**:
```python
# app/api/v1/chatbot.py

from app.observability.rag_logging import rag_step_log

# Step 1: Validate request (line ~62)
rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
            node_label='ValidateRequest', processing_stage='completed')

# Step 4: GDPR (line ~71)
rag_step_log(step=4, step_id='RAG.privacy.gdprcompliance.record.processing.log.data.processing',
            node_label='GDPRLog', processing_stage='completed')

# Step 7: Anonymize (line ~78)
rag_step_log(step=7, step_id='RAG.privacy.anonymizer.anonymize.text.anonymize.pii',
            node_label='AnonymizeText', processing_stage='completed')

# Step 10: Log PII (line ~89)
rag_step_log(step=10, step_id='RAG.platform.logger.info.log.pii.anonymization',
            node_label='LogPII', processing_stage='completed')
```

## 📋 INVESTIGATION QUESTIONS

Before implementing fixes, we need to answer:

1. ✅ **Why is Path B being used when `/chat` endpoint calls `get_response()`?**
   - **ANSWER**: Frontend uses `/chat/stream` not `/chat`!
   - `/chat/stream` calls `get_stream_response()` which bypasses the graph
   - Phase 1A graph is only used by non-streaming `/chat` endpoint

2. ⬜ **Where does the 19-second delay come from?**
   - Trace shows: Step 64 at 20.97s, Request complete at 39.89s
   - What happens between step 64 completion and request completion?

3. ⬜ **Why aren't nodes 11-50 in Phase 1A graph?**
   - Are they implemented but not wired?
   - Or are they intentionally excluded?

4. ⬜ **What is "Phase 1A" vs Full Architecture?**
   - Is Phase 1A a minimal viable flow?
   - When will phases 2-7 be integrated?

## ✅ IMPLEMENTATION CHECKLIST

### Investigation (COMPLETED ✅)
1. ✅ Trace code path → `/chat/stream` bypasses all graphs
2. ✅ Check existing nodes → 59 nodes wired in separate lanes
3. ✅ Verify orchestrators → 135 steps 1-135 (100% coverage)
4. ✅ Verify canonical nodes → 27/27 implemented (100%)
5. ✅ Identify gaps → lanes not connected

### Implementation (IN PROGRESS)
1. ✅ **Create 2 canonical node wrappers** (steps 31, 42) - 45 minutes - COMPLETED
2. ✅ **Create unified graph** (connect 8 lanes) - 2.5 hours - COMPLETED
3. ⬜ **Enable streaming** (hybrid approach) - 1-2 hours - NEXT
4. ⬜ **Test with trace** to verify all steps execute in diagram order

### Verification
- ⬜ Run test query, capture trace
- ⬜ Verify steps appear in order: 1→3→...→20→...→31→...→112
- ⬜ Verify streaming UX maintained
- ⬜ Verify 107 diagram steps execute correctly

**Total Effort**: 5-7 hours over 1-2 days
**Completed**: 3 hours 15 minutes (Phases 2-3)
**Remaining**: 1-2 hours (Phase 4 streaming integration)

## 📁 FILES TO CREATE/MODIFY

### Priority 1: Create Canonical Node Wrappers (Phase 2) ✅ COMPLETED
**Created 2 new files** in `app/core/langgraph/nodes/`:
- ✅ `step_031__classify_domain.py` - Canonical node for domain classification
- ✅ `step_042__class_confidence.py` - Canonical node for confidence check

**Created test files**:
- ✅ `tests/langgraph/test_step_031__classify_domain.py` - 4/4 tests passing
- ✅ `tests/langgraph/test_step_042__class_confidence.py` - 4/4 tests passing

**Updated**:
- ✅ `app/core/langgraph/nodes/__init__.py` - Imported and exported 2 new nodes

**Actual time**: 45 minutes

### Priority 2: Unified Graph (Phase 3) ✅ COMPLETED
**Modified** `app/core/langgraph/graph.py`:
- ✅ Added `create_graph_unified()` function at lines 1642-1924 (283 lines)
- ✅ Wired all 59 nodes with conditional edges across 8 lanes
- ✅ Added 13 node imports (Lane 2, 3, 4 nodes)
- ✅ Added 10 new routing functions (lines 1103-1177)
- ✅ Changed default at line 2011 from `create_graph_phase1a()` to `create_graph_unified()`
- ✅ Verified syntax compilation

**Actual time**: 2.5 hours

### Priority 3: Streaming (Phase 4)
**Modify** `app/core/langgraph/graph.py`:
- Line 1716-1775: Rewrite `get_stream_response()` to use unified graph
- Implement hybrid streaming (graph up to Step 64, then direct stream)

**Time**: 1-2 hours

### Priority 4: Cleanup (Phase 5-6) - OPTIONAL
- `app/api/v1/chatbot.py` line 61-96: Add rag_step_log for steps 1, 4, 7, 10
- Remove duplicate Step 64 logging in providers

## 🎯 SUCCESS CRITERIA

After implementing fixes, a new trace should show:

```
✅ Step 1: ValidateRequest (logged)
✅ Steps 2-10: GDPR, Privacy, PII (logged)
✅ Steps 11-19: Message processing, facts, query sig (logged)
✅ Step 20: GoldenFastGate (logged EARLY)
✅ Steps 31-39: Classification, KB prefetch (logged)
✅ Steps 41-47: Prompt selection (logged)
✅ Steps 48-50: Provider selection (logged)
✅ Steps 59-62: Cache check (logged)
✅ Step 64: LLM Call (logged LAST)
```

**Execution order matches diagram exactly.**

---

**Document created**: 2025-10-11
**Last updated**: 2025-10-12
**Author**: Analysis of RAG trace execution flow
**Status**: Phases 2-3 Complete (59 nodes wired in unified graph ✅). Ready for Phase 4 (Streaming Integration).
