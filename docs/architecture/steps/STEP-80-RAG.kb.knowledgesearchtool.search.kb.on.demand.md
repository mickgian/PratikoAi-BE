# RAG STEP 80 — KnowledgeSearchTool.search KB on demand (RAG.kb.knowledgesearchtool.search.kb.on.demand)

**Type:** process  
**Category:** kb  
**Node ID:** `KBQueryTool`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KBQueryTool` (KnowledgeSearchTool.search KB on demand).

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
  `RAG STEP 80 (RAG.kb.knowledgesearchtool.search.kb.on.demand): KnowledgeSearchTool.search KB on demand | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.35

Top candidates:
1) load_testing/locust_tests.py:215 — load_testing.locust_tests.PratikoAIUser.knowledge_search (score 0.35)
   Evidence: Score 0.35, Test regulatory knowledge searches
2) app/models/knowledge.py:13 — app.models.knowledge.KnowledgeItem (score 0.35)
   Evidence: Score 0.35, Knowledge base item with full-text search support.

This model stores processed ...
3) app/models/knowledge.py:112 — app.models.knowledge.KnowledgeQuery (score 0.35)
   Evidence: Score 0.35, Query model for knowledge search requests
4) app/models/knowledge.py:125 — app.models.knowledge.KnowledgeSearchResponse (score 0.35)
   Evidence: Score 0.35, Response model for knowledge search results
5) app/services/vector_service.py:354 — app.services.vector_service.VectorService.store_italian_regulation (score 0.33)
   Evidence: Score 0.33, Store Italian regulation in vector database for semantic search.

Args:
    regu...

Notes:
- Implementation exists but may not be wired correctly
- Top match is in test files
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->