# RAG STEP 24 — GoldenSet.match_by_signature_or_semantic (RAG.preflight.goldenset.match.by.signature.or.semantic)

**Type:** process  
**Category:** preflight  
**Node ID:** `GoldenLookup`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `GoldenLookup` (GoldenSet.match_by_signature_or_semantic).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 24 (RAG.preflight.goldenset.match.by.signature.or.semantic): GoldenSet.match_by_signature_or_semantic | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.28

Top candidates:
1) app/orchestrators/preflight.py:237 — app.orchestrators.preflight.step_24__golden_lookup (score 0.28)
   Evidence: Score 0.28, RAG STEP 24 — GoldenSet.match_by_signature_or_semantic
ID: RAG.preflight.goldens...
2) app/api/v1/search.py:58 — app.api.v1.search.semantic_search (score 0.26)
   Evidence: Score 0.26, Perform semantic search on Italian knowledge base.

Args:
    request: FastAPI r...
3) app/orchestrators/golden.py:50 — app.orchestrators.golden.step_25__golden_hit (score 0.26)
   Evidence: Score 0.26, RAG STEP 25 — High confidence match? score at least 0.90
ID: RAG.golden.high.con...
4) app/orchestrators/golden.py:68 — app.orchestrators.golden.step_27__kbdelta (score 0.26)
   Evidence: Score 0.26, RAG STEP 27 — KB newer than Golden as of or conflicting tags?
ID: RAG.golden.kb....
5) app/orchestrators/golden.py:86 — app.orchestrators.golden.step_28__serve_golden (score 0.26)
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