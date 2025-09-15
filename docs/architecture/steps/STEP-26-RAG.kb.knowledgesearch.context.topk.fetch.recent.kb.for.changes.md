# RAG STEP 26 — KnowledgeSearch.context_topk fetch recent KB for changes (RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes)

**Type:** process  
**Category:** kb  
**Node ID:** `KBContextCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KBContextCheck` (KnowledgeSearch.context_topk fetch recent KB for changes).

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
  `RAG STEP 26 (RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes): KnowledgeSearch.context_topk fetch recent KB for changes | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.34

Top candidates:
1) app/models/knowledge.py:13 — app.models.knowledge.KnowledgeItem (score 0.34)
   Evidence: Score 0.34, Knowledge base item with full-text search support.

This model stores processed ...
2) app/models/knowledge.py:112 — app.models.knowledge.KnowledgeQuery (score 0.34)
   Evidence: Score 0.34, Query model for knowledge search requests
3) app/models/knowledge.py:125 — app.models.knowledge.KnowledgeSearchResponse (score 0.34)
   Evidence: Score 0.34, Response model for knowledge search results
4) app/services/hybrid_search_engine.py:43 — app.services.hybrid_search_engine.HybridSearchEngine (score 0.31)
   Evidence: Score 0.31, Advanced hybrid search combining keyword and vector search.

Provides sub-300ms ...
5) load_testing/locust_tests.py:215 — load_testing.locust_tests.PratikoAIUser.knowledge_search (score 0.31)
   Evidence: Score 0.31, Test regulatory knowledge searches

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->