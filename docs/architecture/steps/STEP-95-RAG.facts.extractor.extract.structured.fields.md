# RAG STEP 95 — Extractor.extract Structured fields (RAG.facts.extractor.extract.structured.fields)

**Type:** process  
**Category:** facts  
**Node ID:** `ExtractDocFacts`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractDocFacts` (Extractor.extract Structured fields).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/facts.py:588` - `step_95__extract_doc_facts()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator extracting structured facts from parsed documents using AtomicFactsExtractor. Identifies monetary amounts, dates, legal entities, and domain-specific fields. Routes to Step 98 (ToToolResults) for result formatting.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (fact extraction, atomic facts processing, context building)
- [x] Integration tests (fact processing flow and context integration)
- [x] Implementation changes (async orchestrator with fact extraction, atomic facts processing, context building)
- [x] Observability: add structured log line
  `RAG STEP 95 (...): ... | attrs={fact_count, extraction_confidence, context_size}`
- [x] Feature flag / config if needed (fact extraction settings and confidence thresholds)
- [x] Rollout plan (implemented with fact extraction accuracy and context quality safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/orchestrators/facts.py:588 — app.orchestrators.facts.step_95__extract_doc_facts (score 0.32)
   Evidence: Score 0.32, RAG STEP 95 — Extractor.extract Structured fields
ID: RAG.facts.extractor.extrac...
2) app/services/atomic_facts_extractor.py:421 — app.services.atomic_facts_extractor.AtomicFactsExtractor.extract (score 0.32)
   Evidence: Score 0.32, Extract atomic facts from an Italian professional query.

Args:
    query: The u...
3) app/services/atomic_facts_extractor.py:581 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_dates (score 0.31)
   Evidence: Score 0.31, Extract dates, durations, and time-related facts from the query.
4) app/services/atomic_facts_extractor.py:461 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_monetary_amounts (score 0.31)
   Evidence: Score 0.31, Extract monetary amounts and percentages from the query.
5) app/services/atomic_facts_extractor.py:716 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_legal_entities (score 0.31)
   Evidence: Score 0.31, Extract legal entities, tax codes, and document types.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->