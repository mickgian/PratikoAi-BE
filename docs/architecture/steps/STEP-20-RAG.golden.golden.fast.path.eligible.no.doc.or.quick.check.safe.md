# RAG STEP 20 — Golden fast-path eligible? no doc or quick check safe (RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe)

**Type:** process  
**Category:** golden  
**Node ID:** `GoldenFastGate`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `GoldenFastGate` (Golden fast-path eligible? no doc or quick check safe).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/core/langgraph/nodes/step_020__golden_fast_gate.py` - `node_step_20`, `app/orchestrators/golden.py:14` - `step_20__golden_fast_gate()`
- **Status:** ✅
- **Behavior notes:** Node orchestrator using GoldenFastPathService to determine eligibility for golden fast-path. Checks for document-dependent queries, safe factual queries, and complexity indicators. Routes to Step 24 (GoldenLookup) if eligible or Step 31 (ClassifyDomain) if not eligible.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing Golden Set infrastructure

## TDD Task List
- [x] Unit tests (Golden Set operations, FAQ management, confidence matching)
- [x] Integration tests (Golden Set matching and FAQ retrieval flow)
- [x] Implementation changes (async orchestrator with Golden Set operations, FAQ management, confidence matching)
- [x] Observability: add structured log line
  `RAG STEP 20 (...): ... | attrs={match_confidence, golden_set_id, faq_version}`
- [x] Feature flag / config if needed (Golden Set thresholds and matching parameters)
- [x] Rollout plan (implemented with Golden Set accuracy and cache performance safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_20
- Incoming edges: none
- Outgoing edges: [24]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->