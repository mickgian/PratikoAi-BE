# RAG Architecture Migration Plan

**← Context**: [RAG_FLOW_IMPLEMENTATION_00_orchestrators.md](./RAG_FLOW_IMPLEMENTATION_00_orchestrators.md) (135 orchestrators implemented)

**Mode: Tiered Graph Hybrid**

## Architecture Summary

**Actual Implementation:**
- **135 Total Orchestrators** (business logic in `app/orchestrators/`)
- **27 Canonical Nodes** (graph boundaries with node wrappers)
- **108 Internal Orchestrators** (called within node boundaries)
- **60 Node Wrappers** (in `app/core/langgraph/nodes/`)

This project uses two layers by design. They are not duplicates—they have different responsibilities:

## 1. Orchestrators (source of business logic)

Orchestrators = UseCases (or Repository methods): where the business rules live

**Where:** `app/orchestrators/…` (e.g., `platform.py`, `providers.py`, …)

**What:** Real business logic for each step (`step_<N>__*` functions).

**Keep:** Validation, branching, parsing, provider selection, cost calc, etc.

**Do not:** Depend on LangGraph types; keep them framework-agnostic.

## 2. Node Wrappers (graph integration shims)

Node Wrappers = the glue you'd put in a ViewModel to call a UseCase and update UI state

**Where:** `app/core/langgraph/nodes/step_<NNN>__*.py`

**What:** Thin functions that:

- Accept/return RAGState
- Call the corresponding orchestrator(s)
- Add `rag_step_log(...)` and `rag_step_timer(...)`
- Optionally copy results into RAGState under stable keys

**Do not:** Add business logic, retries, or new branching

Team Rule: “Never move or rewrite orchestrator logic; Node wrappers in nodes/ always delegate to orchestrators in app/orchestrators/.”

| Concern                        | Orchestrator (`app/orchestrators`) | Node Wrapper (`app/core/langgraph/nodes`) |
| ------------------------------ | ---------------------------------- | ----------------------------------------- |
| Business logic                 | ✅                                  | ❌ (delegate only)                         |
| LangGraph state (`RAGState`)   | ❌                                  | ✅ read/write                              |
| Logging/timing standardization | light (as needed)                  | ✅ `rag_step_log` / `rag_step_timer`       |
| Retries/fallbacks              | where explicitly required by step  | ❌ (never here)                            |
| Public interfaces              | unchanged                          | unchanged                                 |


## Definitions

### Node (runtime boundary)
Explicit runtime step where state crosses a boundary (LLM calls, caching, provider routing, streaming, compliance gates).

- Must be represented as explicit graph nodes
- Have retries, metrics, and feature flags
- Clear inbound/outbound edges

### Internal (pure transform)
Deterministic functions executed inside a Node boundary.

- No retries, no state isolation
- Called directly by a Node wrapper
- Covered by unit tests and Node-level parity tests

## Canonical Node Set (27 implemented)

Everything not listed here remains **Internal** (108 orchestrators).

### Request / Privacy
- 1 ValidateRequest
- 3 ValidCheck
- 6 PrivacyCheck
- 9 PIICheck

### Golden / Cache
- 20 GoldenFastGate
- 24 GoldenLookup
- 26 KBContextCheck
- 59 CheckCache
- 62 CacheHit

### Classification / Routing
- 31 DomainClassification
- 42 ClassificationConfidence
- 48 SelectProvider
- 50 RoutingStrategy
- 55 EstimateCost
- 56 CostCheck

### LLM / Tools
- 64 LLMCall
- 67 LLMSuccess
- 75 ToolCheck
- 79 ToolType
- 80 KBTool
- 81 CCNLTool
- 82 DocumentIngestTool
- 83 FAQTool

### Response / Streaming
- 104 StreamCheck
- 105 StreamSetup
- 109 StreamResponse
- 112 End

## LLM Tool Calling System

### Overview
The system uses OpenAI/Anthropic function calling to enable LLMs to request execution of Python functions for retrieving additional information. **The LLM never executes our code**—it requests function execution, we run it, and return results.

### Available Tools

| Tool | File | Purpose | When LLM Uses It |
|------|------|---------|-----------------|
| `KnowledgeSearchTool` | `app/core/langgraph/tools/knowledge_search_tool.py` | Search knowledge base (Italian labor law, tax, HR policies) | Needs specific regulatory/legal information not in conversation |
| `CCNLTool` | `app/core/langgraph/tools/ccnl_tool.py` | Search Italian collective labor contracts (CCNL database) | Questions about specific collective agreements, wage scales |
| `FAQTool` | `app/core/langgraph/tools/faq_tool.py` | Search frequently asked questions | Common questions with prepared answers |
| `DocumentIngestTool` | `app/core/langgraph/tools/document_ingest_tool.py` | Process uploaded documents (PDF, DOCX, XML, fattura elettronica) | User provides attachments to analyze |
| `DuckDuckGoSearchTool` | `app/core/langgraph/tools/duckduckgo_search.py` | Web search for current information | Needs real-time/recent data not in knowledge base |

### How Tool Calling Works (Round-Trip Flow)

#### Round 1: App → LLM (Request with Tools)

We send tool definitions as JSON schemas describing available functions:

```python
# Example: Sending request to OpenAI API
{
  "messages": [
    {"role": "user", "content": "Quali sono i requisiti CCNL metalmeccanici 2024?"}
  ],
  "tools": [  # ← Tool definitions
    {
      "type": "function",
      "function": {
        "name": "CCNLTool",
        "description": "Search Italian collective labor agreements (CCNL) database. Use for questions about specific contracts, industry agreements, wage scales, and collective bargaining requirements.",  # ← LLM reads this to decide!
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string", "description": "Search query for CCNL database"},
            "contract_type": {"type": "string", "description": "Contract category (e.g., 'metalmeccanici', 'commercio')"},
            "max_results": {"type": "integer", "default": 10}
          },
          "required": ["query"]
        }
      }
    }
  ]
}
```

**Key Point**: The `description` field tells the LLM when to use the tool. The LLM decides based on:
1. **Tool descriptions** (explains what the tool does and when to use it)
2. **System prompt** (can include hints like "Use CCNLTool for labor contract questions")
3. **LLM's training** (GPT-4/Claude trained to recognize when external data is needed)

#### Round 1: LLM → App (Response)

**Option A - Direct Answer (No Tool Needed):**
```json
{
  "role": "assistant",
  "content": "Il regime forfettario è un regime fiscale agevolato per partite IVA..."
}
```

**Option B - Tool Call Request:**
```json
{
  "role": "assistant",
  "content": "",
  "tool_calls": [  # ← LLM requests tool execution
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "CCNLTool",
        "arguments": "{\"query\": \"metalmeccanici requisiti 2024\", \"contract_type\": \"metalmeccanici\"}"
      }
    }
  ]
}
```

**Important**: The LLM does NOT execute the Python function. It returns JSON saying "please call this function for me with these arguments."

#### Round 2: App Executes Tool (Python Side)

```python
# Step 75: Detect tool_calls in response
if response.tool_calls:
    # Step 79: Determine which tool
    for tool_call in response.tool_calls:
        if tool_call.function.name == "CCNLTool":
            # Step 81: Execute YOUR Python function
            tool_result = await ccnl_tool._arun(
                query="metalmeccanici requisiti 2024",
                contract_type="metalmeccanici"
            )
            # tool_result = [{"title": "CCNL Metalmeccanici 2024", "content": "..."}]
```

#### Round 3: App → LLM (Send Tool Results Back)

```python
{
  "messages": [
    {"role": "user", "content": "Quali sono i requisiti CCNL metalmeccanici 2024?"},
    {"role": "assistant", "tool_calls": [...]},  # ← LLM's request from Round 1
    {"role": "tool", "tool_call_id": "call_abc123", "content": "[{\"title\": \"CCNL 2024\", \"content\": \"Requisiti: anzianità 24 mesi, retribuzione €X/mese...\"}]"}  # ← Tool results
  ]
}
```

#### Round 3: LLM → App (Final Answer with Context)

```json
{
  "role": "assistant",
  "content": "Secondo il CCNL Metalmeccanici 2024:\n\n1. Anzianità minima: 24 mesi\n2. Retribuzione base: €X/mese\n3. ...\n\n[Fonte: CCNL Metalmeccanici 2024]"
}
```

### Implementation in RAG Flow

**Step 64 (LLM Call)**: Passes tools parameter to provider

```python
# app/orchestrators/providers.py:step_64__llmcall()
response = await provider.chat_completion(
    messages=messages,
    tools=available_tools,  # ← List of tool definitions
    temperature=0.2
)
```

**Step 75 (Tool Check)**: Detects if LLM requested tools

```python
# app/orchestrators/response.py:step_75__tool_check()
if response.tool_calls:
    # Route to tool execution (Steps 79-83)
    has_tool_calls = True
    next_step = 'convert_with_tool_calls'
else:
    # Route to simple response (Step 77)
    has_tool_calls = False
    next_step = 'convert_simple_message'
```

**Steps 79-83**: Execute requested tools
- Step 79: Determine tool type (KB, CCNL, Document, FAQ)
- Steps 80-83: Execute specific tool
- Step 99: Collect tool results

**Back to Step 64**: Send tool results to LLM for final answer (Round 3)

### Observability & Tracing

Step 64 completion logs include tools information:
- `tools_provided`: boolean (were tools available to LLM?)
- `tool_count`: number of tools provided
- `tool_names`: list of tool names (e.g., `["CCNLTool", "KnowledgeSearchTool"]`)

Step 75 logs include:
- `has_tool_calls`: boolean (did LLM request tools?)
- `tool_call_count`: number of tools requested
- `tool_names`: which specific tools LLM wants to use

Example trace log:
```json
{
  "step": 64,
  "step_id": "RAG.providers.llmprovider.chat.completion.make.api.call",
  "tools_provided": true,
  "tool_count": 3,
  "tool_names": ["CCNLTool", "KnowledgeSearchTool", "FAQTool"],
  "processing_stage": "completed"
}
```

### Why Tool Calling? (vs Always Retrieve)

**Without Tool Calling (Always Retrieve):**
```
User: "What is 2+2?"
→ Search KB for "2+2" (waste of time/resources)
→ LLM answers: "4"

Cost: KB query + LLM call
Time: ~500ms (KB) + 200ms (LLM)
```

**With Tool Calling (LLM Decides):**
```
User: "What is 2+2?"
→ LLM thinks: "I know this, no search needed"
→ LLM answers: "4"

Cost: LLM call only
Time: ~200ms (LLM only)

---

User: "Quali sono i nuovi requisiti CCNL metalmeccanici 2024?"
→ LLM thinks: "I need specific 2024 data from contracts"
→ LLM calls: CCNLTool(query="CCNL metalmeccanici requisiti 2024")
→ Tool returns: [KB articles with 2024 updates]
→ LLM answers: "Ecco i requisiti aggiornati..." (accurate, sourced)

Cost: LLM call + KB query + LLM call (3 steps)
Time: ~200ms + 500ms + 300ms = 1000ms
```

**Benefits:**
- ⚡ Faster responses (no unnecessary searches)
- 💰 Lower costs (fewer KB queries, only when needed)
- 🎯 Better accuracy (only searches when LLM needs external data)
- 📚 Proper citations (can cite KB articles when used)

## Phase 0 — Align & Freeze
**Status:** ✅ Implemented
**Goal:** Lock the Tiered Graph Hybrid target (27 Canonical Nodes, 108 Internal Orchestrators).
**Deliverable:** This doc + team ACK in PR comments.

**Gate:** PR comment from the team: "We're doing Tiered Graph Hybrid."

## Phase 1 — Documentation Sync
**Status:** ✅ Implemented
**Goal:** Make docs reflect reality so audits are meaningful.

Update every `docs/architecture/steps/STEP-*.md`:

- **Role:** Node | Internal
- **Status:**
  - Node → ✅ Implemented / 🔌 Not wired / ❌ Missing
  - Internal → 🔌 Implemented (internal) / ❌ Missing
- **Paths / classes:** 1–3 file:line — symbol entries
- **Behavior notes:** brief; include nearest Node and neighbors if Node

Edit Mermaid nodes to show badges: `[S<step>] {Node|Internal}`

**Example:**
```
ValidateRequest[[S1 Validate request {Node}]]
```

**Run tooling:**
```bash
python scripts/rag_code_graph.py --write
python scripts/rag_audit.py --write
```

**Gate (dashboard):**
- Node steps must be wired
- Internal steps only need to be implemented

## Phase 1A — Initial Node Promotion (complete)

**Status:** ✅ Implemented and active (default).

**Promoted Nodes (9):**
- 1 ValidateRequest
- 3 ValidCheck
- 6 PrivacyCheck
- 9 PIICheck
- 59 CheckCache
- 62 CacheHit
- 64 LLMCall
- 67 LLMSuccess
- 112 End

**Implementation notes:**
- RAGState type created (extends existing GraphState)
- 9 thin Node wrappers calling existing `step_N__*` orchestrators
- Edges wired in `create_graph_phase1a()`
- Now the default implementation (no feature flag needed)
- Tests: unit, integration, parity

## Phase 2 — Audit Rules Update (½ day)

**Goal:** Make audits fair to hybrid mode.

**Rules:**
- If Role=Node → must be wired in LangGraph to pass
- If Role=Internal → pass if implemented & referenced by a Node path

**Gate:** Rerun audit shows green for Internal steps that used to read ❌/🔌.

## Phase 3 — Implementation Scaffolding (complete)

**Status:** ✅ Implemented

**Goal:** Prepare safe wrappers & state.

**Tasks:**
- Finalize RAGState (request/user/session, privacy flags, facts, attachments, golden hit, KB docs, provider choice, cache key, LLM response, tool results, streaming flags, metrics)
- Create Node wrappers (for all ~35 promoted steps) that call existing internal code
- Add `rag_step_log(...)` + `rag_step_timer(...)`
- Parity tests: snapshot real conversations; assert identical outputs with/without wrappers

**Gate:** All parity tests pass.

**Implementation notes:**
- RAGState TypedDict finalized with all required fields in `app/core/langgraph/types.py`
- 14 node wrappers created following thin delegation pattern:
  - Original 9: steps 1, 3, 6, 9, 59, 62, 64, 67, 112
  - Additional 5: steps 2, 11, 12, 13, 48
- `rag_step_log()` and `rag_step_timer()` helpers implemented and integrated
- Parity test suite created in `tests/langgraph/phase3_parity/` - all 16 tests passing
- No behavior changes - full backward compatibility maintained

## Phase 4 — Cache → LLM → Tools Lane (2–3 days)

**Status:** ✅ Implemented

**Goal:** Wire the hot path; keep pure transforms internal.

**Nodes & edges:**
```
59 CheckCache → 62 CacheHit?
  ├─ Yes → 66 ReturnCached → 101/112
  └─ No  → 64 LLMCall → 67 LLMSuccess?
              ├─ Yes → 68 CacheResponse → 74 TrackUsage
              └─ No  → 69 RetryCheck → 70 ProdCheck → (72 Failover | 73 RetrySame)
          → 75 ToolCheck → 79 ToolType → (80 KB | 81 CCNL | 82 Doc | 83 FAQ) → 99 ToolResults
```

**Metrics:** cache hit%, LLM retry rate, tool failure rate.

**Gates:** Parity green; latency & cost stable in canary; audit marks these Nodes as wired ✅.

**Implementation notes:**
- 17 nodes wired in Phase 4 lane (steps 59, 62, 64, 66-70, 72-75, 79-83, 99)
- Full cache → LLM → retry → tools flow operational
- Tests: 41/41 passing in `tests/langgraph/phase4_lane`
- Wiring registered in `app/core/langgraph/wiring_registry.py`

## Phase 5 — Provider Governance Lane (2–3 days)

**Status:** ✅ Implemented

**Goal:** Make routing & cost explicit and observable.

**Nodes:**
```
48 SelectProvider → 49 RouteStrategy → 50 StrategyType → (51/52/53/54) → 55 EstimateCost → 56 CostCheck → (57 CreateProvider | 58 CheaperProvider)
```

**Policies:** per-route budgets, caps, A/B routes, kill switches.
**Metrics:** route distribution, cost/turn, cost rejections.
**Gate:** Cost regression tests pass; decisions observable in logs/dashboards.

**Implementation notes:**
- 11 nodes wired in Phase 5 lane (steps 48-58)
- Provider selection with routing strategies (CHEAP, BEST, BALANCED, PRIMARY)
- Cost estimation and budget enforcement with cheaper provider fallback loop
- Tests: 33/33 passing in `tests/langgraph/phase5_provider_lane`
- Wiring centralized in `app/core/langgraph/wiring_registry.py` (single source of truth)
- Step 50 ID disambiguated: `RAG.platform.routing.strategy.type`

## Phase 6 — Request / Privacy Lane (1–2 days)

**Status:** ✅ Implemented

**Goal:** Enforce compliance gates.

**Nodes:**
```
1 ValidateRequest → 3 ValidCheck → (4 GDPRLog) → 6 PrivacyCheck → (7 AnonymizeText → 9 PIICheck → 10 LogPII) → 8 InitAgent
```

**Policies:** hard reject invalid requests; GDPR evidence logs.
**Gate:** Negative tests pass (bad request, privacy disabled, etc.); audit logs present.

**Implementation notes:**
- 8 nodes wired in Phase 6 lane (steps 1, 3, 4, 6, 7, 8, 9, 10)
- Full request validation and privacy compliance flow operational
- Tests: 9/9 passing in `tests/langgraph/phase6_request_privacy`
- Wiring registered in `app/core/langgraph/wiring_registry.py`

## Phase 7 — Streaming / Response Lane (1–2 days)

**Status:** ✅ Implemented

**Goal:** Isolate streaming from compute.

**Nodes:**
```
104 StreamCheck → (105 StreamSetup → 106 AsyncGen → 107 SinglePass → 108 WriteSSE → 109 StreamResponse → 110 SendDone) → 111 CollectMetrics → 112 End
```

**Gate:** Streaming stability & metrics visible; non-stream path unaffected.

**Implementation notes:**
- 9 nodes wired in Phase 7 lane (steps 104-111, plus 112 End)
- Streaming branch: 104 → 105 → 106 → 107 → 108 → 109 → 110 → 111 → 112
- Non-streaming path: 104 → 111 → 112 (skips SSE nodes 105-110)
- Tests: 6 test files with comprehensive coverage in `tests/langgraph/phase7_streaming`
- Wiring registered in `app/core/langgraph/wiring_registry.py`
- Graph function: `create_graph_phase7_streaming()` in `app/core/langgraph/graph.py`

## Phase 8 — Golden / KB Gates (2–3 days)

**Status:** ✅ Implemented

**Goal:** Golden fast-path + KB recency checks.

**Nodes:**
```
20 GoldenFastGate → (24 GoldenLookup → 25 GoldenHit → 26 KBContextCheck → 27 KBDelta → 28 ServeGolden → 30 ReturnComplete)
(Branch to KB path when needed.)
```

**Metrics:** golden hit% and KB override% by signature.
**Gate:** Golden answers served with citations; fallbacks verified.

**Implementation notes:**
- 7 nodes wired in Phase 8 lane (steps 20, 24, 25, 26, 27, 28, 30)
- Full golden fast-path and KB recency flow operational
- Tests: 15/15 passing in `tests/langgraph/phase8_golden_kb/test_phase8_comprehensive.py`
- Wiring registered in `app/core/langgraph/wiring_registry.py`
- Golden eligibility, lookup/hit decisions, KB context/delta checks all observable
- Metrics logging for golden hit% and KB override% tracking implemented

## Phase 9 — Test Suite Hardening (parallel)

**Status:** 🔄 Partially Implemented (72/147 tests passing - 49%)

**Goal:** Ensure comprehensive testing across all lanes.

**Tasks:**
- Parity tests per lane
- Lane integration tests (prev → this → next)
- Failure injection (cache miss/hit, provider budget fail, tool timeout, stream disconnect)
- Performance budgets: P95 latency caps per lane

**Gate:** CI fast & reliable; red tests are actionable.

**Implementation notes:**
- Test suite structure established across 4 categories (16 test files):
  - **Parity tests (5 files):** 35/39 passing (89.7%) - validates node wrappers delegate correctly to orchestrators
  - **Lane integration (5 files):** 16/40 passing (40%) - validates multi-node flows within each phase lane
  - **Failure injection (4 files):** 3/47 passing (6.4%) - validates error handling and recovery paths
  - **Performance tests (2 files):** 18/21 passing (85.7%) - validates P95 latency budgets per wrapper
- **Remaining work:**
  - 4 parity failures: sync/async orchestrator compatibility (steps 9, 26, 80 + 1 privacy test)
  - 24 lane integration failures: cross-node state propagation and edge conditions
  - 44 failure injection failures: error scenario coverage and fallback paths
  - 3 performance failures: tool wrapper overhead optimization

## PR Discipline (keep it small)

- **PR 1:** Phase 0–1 (docs only)
- **PR 2:** Scaffolding (state + node wrappers, no behavior change)
- **PR 3:** Cache→LLM→Tools lane
- **PR 4:** Provider governance lane
- **PR 5:** Request/Privacy lane
- **PR 6:** Streaming/Response lane
- **PR 7:** Golden/KB gates

*(Tests & dashboards can land alongside each PR.)*

## Success Criteria

- **Conformance:** All Node steps wired ✅; Internal steps marked Implemented (internal)
- **Ops:** ↑ cache hit%, LLM retry% < 2%, tool failures isolated, faster triage
- **Cost:** 5–20% token savings (cache + provider governance)
- **Compliance:** Deterministic logs at request/privacy gates

## Handy Commands

### Refresh graph & audit:
```bash
python scripts/rag_code_graph.py --write
python scripts/rag_audit.py --write
```

### Run parity & integration tests (adapt to your names):
```bash
pytest -k "parity or lane or rag_step"
```

### Run the application with Phase 1A graph (now default):
```bash
uvicorn app.main:app --reload
```

---

## Next Steps

**Status**: Phases 0-8 ✅ Complete (all 8 lanes implemented with 57 nodes)

**Continue to**: [RAG_FLOW_IMPLEMENTATION_02_unified_graph.md](./RAG_FLOW_IMPLEMENTATION_02_unified_graph.md)

This document describes the investigation, discovery, and plan for connecting all 8 lanes into a unified graph that follows the complete diagram flow.