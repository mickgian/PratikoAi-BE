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
Status: 🔌  |  Confidence: 0.33

Top candidates:
1) app/services/atomic_facts_extractor.py:581 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_dates (score 0.33)
   Evidence: Score 0.33, Extract dates, durations, and time-related facts from the query.
2) app/services/atomic_facts_extractor.py:882 — app.services.atomic_facts_extractor.AtomicFactsExtractor._canonicalize_number (score 0.33)
   Evidence: Score 0.33, Convert Italian number format to decimal.
3) app/services/atomic_facts_extractor.py:911 — app.services.atomic_facts_extractor.AtomicFactsExtractor._canonicalize_date (score 0.33)
   Evidence: Score 0.33, Convert Italian date format to ISO format (YYYY-MM-DD).
4) app/services/atomic_facts_extractor.py:934 — app.services.atomic_facts_extractor.AtomicFactsExtractor._canonicalize_entity (score 0.33)
   Evidence: Score 0.33, Canonicalize legal entity text.
5) app/services/atomic_facts_extractor.py:461 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_monetary_amounts (score 0.32)
   Evidence: Score 0.32, Extract monetary amounts and percentages from the query.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->