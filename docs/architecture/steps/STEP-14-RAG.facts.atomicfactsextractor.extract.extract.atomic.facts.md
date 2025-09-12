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
Status: 🔌  |  Confidence: 0.34

Top candidates:
1) app/services/atomic_facts_extractor.py:421 — app.services.atomic_facts_extractor.AtomicFactsExtractor.extract (score 0.34)
   Evidence: Score 0.34, Extract atomic facts from an Italian professional query.

Args:
    query: The u...
2) app/services/atomic_facts_extractor.py:186 — app.services.atomic_facts_extractor.AtomicFactsExtractor.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the atomic facts extractor with Italian patterns.
3) app/services/atomic_facts_extractor.py:191 — app.services.atomic_facts_extractor.AtomicFactsExtractor._load_patterns (score 0.30)
   Evidence: Score 0.30, Load regex patterns for extracting different types of facts.
4) app/services/atomic_facts_extractor.py:380 — app.services.atomic_facts_extractor.AtomicFactsExtractor._load_canonicalization_rules (score 0.30)
   Evidence: Score 0.30, Load rules for canonicalizing extracted facts.
5) app/services/atomic_facts_extractor.py:461 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_monetary_amounts (score 0.30)
   Evidence: Score 0.30, Extract monetary amounts and percentages from the query.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->