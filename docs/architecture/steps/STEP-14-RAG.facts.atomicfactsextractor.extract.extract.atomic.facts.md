# RAG STEP 14 — AtomicFactsExtractor.extract Extract atomic facts (RAG.facts.atomicfactsextractor.extract.extract.atomic.facts)

**Type:** process  
**Category:** facts  
**Node ID:** `ExtractFacts`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractFacts` (AtomicFactsExtractor.extract Extract atomic facts).

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
  `RAG STEP 14 (RAG.facts.atomicfactsextractor.extract.extract.atomic.facts): AtomicFactsExtractor.extract Extract atomic facts | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.42

Top candidates:
1) app/services/atomic_facts_extractor.py:421 — app.services.atomic_facts_extractor.AtomicFactsExtractor.extract (score 0.42)
   Evidence: Score 0.42, Extract atomic facts from an Italian professional query.

Args:
    query: The u...
2) app/services/atomic_facts_extractor.py:581 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_dates (score 0.39)
   Evidence: Score 0.39, Extract dates, durations, and time-related facts from the query.
3) app/services/atomic_facts_extractor.py:461 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_monetary_amounts (score 0.37)
   Evidence: Score 0.37, Extract monetary amounts and percentages from the query.
4) app/services/atomic_facts_extractor.py:716 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_legal_entities (score 0.37)
   Evidence: Score 0.37, Extract legal entities, tax codes, and document types.
5) app/services/atomic_facts_extractor.py:779 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_professional_categories (score 0.37)
   Evidence: Score 0.37, Extract professional categories, job levels, and contract types.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->