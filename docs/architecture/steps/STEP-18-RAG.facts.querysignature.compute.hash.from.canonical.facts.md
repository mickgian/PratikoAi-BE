# RAG STEP 18 — QuerySignature.compute Hash from canonical facts (RAG.facts.querysignature.compute.hash.from.canonical.facts)

**Type:** process  
**Category:** facts  
**Node ID:** `QuerySig`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `QuerySig` (QuerySignature.compute Hash from canonical facts).

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
  `RAG STEP 18 (RAG.facts.querysignature.compute.hash.from.canonical.facts): QuerySignature.compute Hash from canonical facts | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/facts.py:50 — app.orchestrators.facts.step_18__query_sig (score 0.31)
   Evidence: Score 0.31, RAG STEP 18 — QuerySignature.compute Hash from canonical facts
ID: RAG.facts.que...
2) app/services/cache.py:82 — app.services.cache.CacheService._generate_query_hash (score 0.27)
   Evidence: Score 0.27, Generate a deterministic hash for query deduplication.

Args:
    messages: List...
3) app/orchestrators/facts.py:68 — app.orchestrators.facts.step_29__pre_context_from_golden (score 0.27)
   Evidence: Score 0.27, RAG STEP 29 — ContextBuilder.merge facts and KB docs and doc facts if present
ID...
4) app/core/performance/database_optimizer.py:382 — app.core.performance.database_optimizer.DatabaseOptimizer._extract_table_from_query (score 0.27)
   Evidence: Score 0.27, Extract primary table name from query.
5) app/core/hash_gate.py:21 — app.core.hash_gate.HashGate.__init__ (score 0.25)
   Evidence: Score 0.25, method: __init__

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->