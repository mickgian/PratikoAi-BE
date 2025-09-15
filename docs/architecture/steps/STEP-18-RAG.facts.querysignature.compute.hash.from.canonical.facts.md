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
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/services/cache.py:82 — app.services.cache.CacheService._generate_query_hash (score 0.27)
   Evidence: Score 0.27, Generate a deterministic hash for query deduplication.

Args:
    messages: List...
2) app/core/performance/database_optimizer.py:382 — app.core.performance.database_optimizer.DatabaseOptimizer._extract_table_from_query (score 0.27)
   Evidence: Score 0.27, Extract primary table name from query.
3) app/core/hash_gate.py:21 — app.core.hash_gate.HashGate.__init__ (score 0.25)
   Evidence: Score 0.25, method: __init__
4) app/models/user.py:55 — app.models.user.User.hash_password (score 0.25)
   Evidence: Score 0.25, Hash a password using bcrypt.
5) app/services/query_service.py:67 — app.services.query_service.QueryService.__init__ (score 0.25)
   Evidence: Score 0.25, Initialize query service.

Args:
    db_session: Optional database session for q...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for QuerySig
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->