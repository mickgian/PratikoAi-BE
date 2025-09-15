# RAG STEP 16 — AtomicFactsExtractor.canonicalize Normalize dates amounts rates (RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates)

**Type:** process  
**Category:** facts  
**Node ID:** `CanonicalizeFacts`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CanonicalizeFacts` (AtomicFactsExtractor.canonicalize Normalize dates amounts rates).

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
  `RAG STEP 16 (RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates): AtomicFactsExtractor.canonicalize Normalize dates amounts rates | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.25

Top candidates:
1) app/services/italian_query_normalizer.py:239 — app.services.italian_query_normalizer.ItalianQueryNormalizer.normalize (score 0.25)
   Evidence: Score 0.25, Normalize an Italian tax/legal query for improved cache hits.

Args:
    query: ...
2) app/core/middleware/prometheus_middleware.py:74 — app.core.middleware.prometheus_middleware.PrometheusMiddleware._normalize_path (score 0.19)
   Evidence: Score 0.19, Normalize path to reduce cardinality in metrics.

Args:
    path: Original reque...
3) app/core/performance/database_optimizer.py:162 — app.core.performance.database_optimizer.DatabaseOptimizer._normalize_query (score 0.19)
   Evidence: Score 0.19, Normalize query for consistent tracking.
4) app/models/subscription.py:122 — app.models.subscription.SubscriptionPlan.iva_amount (score 0.19)
   Evidence: Score 0.19, IVA amount in euros (22% of base price)
5) app/services/ccnl_response_formatter.py:357 — app.services.ccnl_response_formatter.CCNLResponseFormatter._capitalize (score 0.19)
   Evidence: Score 0.19, Capitalize text properly for Italian.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for CanonicalizeFacts
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->