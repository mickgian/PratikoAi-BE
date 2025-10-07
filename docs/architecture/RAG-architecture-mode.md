# RAG Architecture Migration Plan

**Mode: Tiered Graph Hybrid**

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

## Canonical Node Set (~35 promoted)

Everything not listed here remains **Internal**.

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

## Phase 0 — Align & Freeze
**Status:** ✅ Implemented
**Goal:** Lock the Tiered Graph Hybrid target (~35 Nodes, ~100 Internals).
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

**Goal:** Golden fast-path + KB recency checks.

**Nodes:**
```
20 GoldenFastGate → (24 GoldenLookup → 25 GoldenHit → 26 KBContextCheck → 27 KBDelta → 28 ServeGolden → 30 ReturnComplete)
(Branch to KB path when needed.)
```

**Metrics:** golden hit% and KB override% by signature.
**Gate:** Golden answers served with citations; fallbacks verified.

## Phase 9 — Test Suite Hardening (parallel)

**Goal:** Ensure comprehensive testing across all lanes.

**Tasks:**
- Parity tests per lane
- Lane integration tests (prev → this → next)
- Failure injection (cache miss/hit, provider budget fail, tool timeout, stream disconnect)
- Performance budgets: P95 latency caps per lane

**Gate:** CI fast & reliable; red tests are actionable.

## Phase 10 — Rollout & Ops (2–4 days)

**Goal:** Ship safely with toggles.

**Feature flags per lane:**
- `cache_llm_lane`
- `tools_lane`
- `provider_lane`
- `privacy_lane`
- `streaming_lane`
- `golden_lane`

**Canary:** 5% → 25% → 50% → 100%

**Dashboards:** cache hit%, LLM retries, tool error rate, latency by lane, token cost/turn

**On incident:** flip off only the offending lane

**Gate:** All lanes at 100%, SLOs hold.

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