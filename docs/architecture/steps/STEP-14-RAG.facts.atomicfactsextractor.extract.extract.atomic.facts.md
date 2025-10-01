# RAG STEP 14 — AtomicFactsExtractor.extract Extract atomic facts (RAG.facts.atomicfactsextractor.extract.extract.atomic.facts)

**Type:** process  
**Category:** facts  
**Node ID:** `ExtractFacts`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractFacts` (AtomicFactsExtractor.extract Extract atomic facts).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/facts.py:14` - `step_14__extract_facts()`
- **Role:** Internal
- **Status:** missing
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (monetary amounts, dates, legal entities, professional categories, geographic info, empty query, complex query, routing)
- [x] Integration tests (Step 13→14→16 flow, context preservation)
- [x] Implementation changes (thin async orchestrator in app/orchestrators/facts.py)
- [x] Observability: add structured log line
  `RAG STEP 14 (RAG.facts.atomicfactsextractor.extract.extract.atomic.facts): AtomicFactsExtractor.extract Extract atomic facts | attrs={...}`
- [x] Feature flag / config if needed (none required - core functionality)
- [x] Rollout plan (implemented with comprehensive tests)

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