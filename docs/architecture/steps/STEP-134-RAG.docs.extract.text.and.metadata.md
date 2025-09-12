# RAG STEP 134 — Extract text and metadata (RAG.docs.extract.text.and.metadata)

**Type:** process  
**Category:** docs  
**Node ID:** `ParseDocs`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ParseDocs` (Extract text and metadata).

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
  `RAG STEP 134 (RAG.docs.extract.text.and.metadata): Extract text and metadata | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.30

Top candidates:
1) app/services/atomic_facts_extractor.py:421 — app.services.atomic_facts_extractor.AtomicFactsExtractor.extract (score 0.30)
   Evidence: Score 0.30, Extract atomic facts from an Italian professional query.

Args:
    query: The u...
2) app/data/ccnl_priority1.py:31 — app.data.ccnl_priority1.get_metalmeccanici_industria_ccnl (score 0.23)
   Evidence: Score 0.23, Get CCNL for Metalmeccanici Industria - largest industrial sector.
3) app/data/ccnl_priority1.py:239 — app.data.ccnl_priority1.get_commercio_terziario_ccnl (score 0.23)
   Evidence: Score 0.23, Get CCNL for Commercio e Terziario - largest commercial sector.
4) app/data/ccnl_priority1.py:337 — app.data.ccnl_priority1.get_edilizia_industria_ccnl (score 0.23)
   Evidence: Score 0.23, Get CCNL for Edilizia Industria - construction industry.
5) app/data/ccnl_priority1.py:434 — app.data.ccnl_priority1.get_pubblici_esercizi_ccnl (score 0.23)
   Evidence: Score 0.23, Get CCNL for Pubblici Esercizi - bars, restaurants, hotels.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->