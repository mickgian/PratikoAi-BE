# RAG STEP 39 — KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost (RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost)

**Type:** process  
**Category:** preflight  
**Node ID:** `KBPreFetch`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KBPreFetch` (KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost).

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
  `RAG STEP 39 (RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost): KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.22

Top candidates:
1) load_testing/locust_tests.py:215 — load_testing.locust_tests.PratikoAIUser.knowledge_search (score 0.22)
   Evidence: Score 0.22, Test regulatory knowledge searches
2) app/services/knowledge_integrator.py:22 — app.services.knowledge_integrator.KnowledgeIntegrator.__init__ (score 0.19)
   Evidence: Score 0.19, Initialize knowledge integrator.

Args:
    db_session: Database session for ope...
3) app/services/knowledge_integrator.py:505 — app.services.knowledge_integrator.KnowledgeIntegrator._generate_content_hash (score 0.19)
   Evidence: Score 0.19, Generate SHA256 hash of content.

Args:
    content: Text content
    
Returns:
...
4) app/services/knowledge_integrator.py:519 — app.services.knowledge_integrator.KnowledgeIntegrator._determine_knowledge_category (score 0.19)
   Evidence: Score 0.19, Determine knowledge category based on document data.

Args:
    document_data: D...
5) app/services/knowledge_integrator.py:556 — app.services.knowledge_integrator.KnowledgeIntegrator._determine_knowledge_subcategory (score 0.19)
   Evidence: Score 0.19, Determine knowledge subcategory.

Args:
    document_data: Document information
...

Notes:
- Weak or missing implementation
- Top match is in test files
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for KBPreFetch
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->