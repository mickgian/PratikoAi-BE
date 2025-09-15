# RAG STEP 118 — POST /api/v1/knowledge/feedback (RAG.kb.post.api.v1.knowledge.feedback)

**Type:** process  
**Category:** kb  
**Node ID:** `KnowledgeFeedback`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KnowledgeFeedback` (POST /api/v1/knowledge/feedback).

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
  `RAG STEP 118 (RAG.kb.post.api.v1.knowledge.feedback): POST /api/v1/knowledge/feedback | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.38

Top candidates:
1) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.38)
   Evidence: Score 0.38, Convert internal SearchResponse to API model.
2) app/services/vector_providers/pinecone_provider.py:113 — app.services.vector_providers.pinecone_provider.PineconeProvider.upsert (score 0.37)
   Evidence: Score 0.37, Upsert vectors into Pinecone index.
3) app/services/vector_providers/pinecone_provider.py:161 — app.services.vector_providers.pinecone_provider.PineconeProvider.query (score 0.37)
   Evidence: Score 0.37, Query vectors from Pinecone index.
4) app/models/knowledge.py:13 — app.models.knowledge.KnowledgeItem (score 0.36)
   Evidence: Score 0.36, Knowledge base item with full-text search support.

This model stores processed ...
5) app/models/knowledge.py:112 — app.models.knowledge.KnowledgeQuery (score 0.36)
   Evidence: Score 0.36, Query model for knowledge search requests

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->