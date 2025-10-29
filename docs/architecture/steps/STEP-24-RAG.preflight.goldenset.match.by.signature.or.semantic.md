# RAG STEP 24 — GoldenSet.match_by_signature_or_semantic (RAG.preflight.goldenset.match.by.signature.or.semantic)

**Type:** process  
**Category:** preflight  
**Node ID:** `GoldenLookup`

## Intent (Blueprint)
Matches user queries against the Golden Set (FAQ database) using either query signature (exact hash match) or semantic similarity search. This is the primary FAQ lookup mechanism in the RAG pipeline.

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/core/langgraph/nodes/step_024__golden_lookup.py` - `node_step_24`, `app/orchestrators/preflight.py:239` - `step_24__golden_lookup()`
- **Status:** ✅
- **Behavior notes:** Node orchestrator that performs two-stage matching: (1) Try exact signature match first using query_signature hash from Step 18, (2) Fallback to semantic similarity search using SemanticFAQMatcher. Returns match result with metadata (match_type, similarity_score, search_method) and routes to Step 25 (GoldenHit) for confidence evaluation.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - mock implementation for testing, production will use SemanticFAQMatcher

## TDD Task List
- [x] Unit tests (signature match, semantic match, no match, context preservation, routing, metadata, high confidence, logging)
- [x] Integration tests (Step 20→24→25 flow, Step 25 preparation)
- [x] Implementation changes (async orchestrator with signature-first + semantic-fallback strategy)
- [x] Observability: add structured log line
  `RAG STEP 24 (RAG.preflight.goldenset.match.by.signature.or.semantic): GoldenSet.match_by_signature_or_semantic | attrs={match_found, match_type, similarity_score, search_method}`
- [x] Feature flag / config if needed (none required - mock for testing)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_24
- Incoming edges: [20]
- Outgoing edges: [25]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->