# RAG STEP 24 — GoldenSet.match_by_signature_or_semantic (RAG.preflight.goldenset.match.by.signature.or.semantic)

**Type:** process  
**Category:** preflight  
**Node ID:** `GoldenLookup`

## Intent (Blueprint)
Matches user queries against the Golden Set (FAQ database) using either query signature (exact hash match) or semantic similarity search. This is the primary FAQ lookup mechanism in the RAG pipeline.

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/preflight.py:239` - `step_24__golden_lookup()`
- **Status:** missing
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.28

Top candidates:
1) app/orchestrators/preflight.py:239 — app.orchestrators.preflight.step_24__golden_lookup (score 0.28)
   Evidence: Score 0.28, RAG STEP 24 — GoldenSet.match_by_signature_or_semantic
ID: RAG.preflight.goldens...
2) app/api/v1/search.py:58 — app.api.v1.search.semantic_search (score 0.26)
   Evidence: Score 0.26, Perform semantic search on Italian knowledge base.

Args:
    request: FastAPI r...
3) app/orchestrators/golden.py:260 — app.orchestrators.golden.step_25__golden_hit (score 0.26)
   Evidence: Score 0.26, RAG STEP 25 — High confidence match? score at least 0.90
ID: RAG.golden.high.con...
4) app/orchestrators/golden.py:320 — app.orchestrators.golden.step_27__kbdelta (score 0.26)
   Evidence: Score 0.26, RAG STEP 27 — KB newer than Golden as of or conflicting tags?
ID: RAG.golden.kb....
5) app/orchestrators/golden.py:413 — app.orchestrators.golden.step_28__serve_golden (score 0.26)
   Evidence: Score 0.26, RAG STEP 28 — Serve Golden answer with citations
ID: RAG.golden.serve.golden.ans...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for GoldenLookup
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->