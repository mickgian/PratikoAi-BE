# RAG STEP 25 — High confidence match? score at least 0.90 (RAG.golden.high.confidence.match.score.at.least.0.90)

**Type:** process  
**Category:** golden  
**Node ID:** `GoldenHit`

## Intent (Blueprint)
Evaluates the confidence score of a Golden Set match from Step 24 to determine routing. If the similarity score is >= 0.90 (high confidence), routes to Step 26 for KB freshness validation. Otherwise routes to Step 30 (ClassifyDomain) for standard RAG flow.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/core/langgraph/nodes/step_025__golden_hit.py` - `node_step_25`, `app/orchestrators/golden.py:260` - `step_25__golden_hit()`
- **Status:** 🔌
- **Behavior notes:** Node orchestrator that performs threshold comparison (0.90) on `similarity_score` from Step 24. Routes to KB context check (Step 26) if high confidence, or ClassifyDomain (Step 30) if low confidence. Includes decision metadata for observability.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - simple threshold comparison with clear decision logic

## TDD Task List
- [x] Unit tests (high confidence, low confidence, exact threshold, no match, context preservation, decision metadata, logging, missing score)
- [x] Integration tests (Step 24→25→26 high confidence flow, Step 24→25→30 low confidence flow, Step 25→26 context preparation)
- [x] Implementation changes (async orchestrator with 0.90 threshold decision logic)
- [x] Observability: add structured log line
  `RAG STEP 25 (RAG.golden.high.confidence.match.score.at.least.0.90): High confidence match? score at least 0.90 | attrs={high_confidence_match, similarity_score, confidence_threshold, next_step}`
- [x] Feature flag / config if needed (none required - threshold hardcoded per Mermaid spec)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_25
- Incoming edges: [24]
- Outgoing edges: [26]

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->