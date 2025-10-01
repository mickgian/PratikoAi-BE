# RAG Architecture Migration Plan

**Mode: Tiered Graph Hybrid**

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

## Phase 3 — Implementation Scaffolding (1–2 days, no behavior change)

**Goal:** Prepare safe wrappers & state.

**Tasks:**
- Finalize RAGState (request/user/session, privacy flags, facts, attachments, golden hit, KB docs, provider choice, cache key, LLM response, tool results, streaming flags, metrics)
- Create Node wrappers (for all ~35 promoted steps) that call existing internal code
- Add `rag_step_log(...)` + `rag_step_timer(...)`
- Parity tests: snapshot real conversations; assert identical outputs with/without wrappers

**Gate:** All parity tests pass.

## Phase 4 — Cache → LLM → Tools Lane (2–3 days)

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

## Phase 5 — Provider Governance Lane (2–3 days)

**Goal:** Make routing & cost explicit and observable.

**Nodes:**
```
48 SelectProvider → 49 RouteStrategy → 50 StrategyType → (51/52/53/54) → 55 EstimateCost → 56 CostCheck → (57 CreateProvider | 58 CheaperProvider)
```

**Policies:** per-route budgets, caps, A/B routes, kill switches.
**Metrics:** route distribution, cost/turn, cost rejections.
**Gate:** Cost regression tests pass; decisions observable in logs/dashboards.

## Phase 6 — Request / Privacy Lane (1–2 days)

**Goal:** Enforce compliance gates.

**Nodes:**
```
1 ValidateRequest → 3 ValidCheck → (4 GDPRLog) → 6 PrivacyCheck → (7 AnonymizeText → 9 PIICheck → 10 LogPII) → 8 InitAgent
```

**Policies:** hard reject invalid requests; GDPR evidence logs.
**Gate:** Negative tests pass (bad request, privacy disabled, etc.); audit logs present.

## Phase 7 — Streaming / Response Lane (1–2 days)

**Goal:** Isolate streaming from compute.

**Nodes:**
```
104 StreamCheck → (105 StreamSetup → 106 AsyncGen → 107 SinglePass → 108 WriteSSE → 109 StreamResponse → 110 SendDone) → 111 CollectMetrics → 112 End
```

**Gate:** Streaming stability & metrics visible; non-stream path unaffected.

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