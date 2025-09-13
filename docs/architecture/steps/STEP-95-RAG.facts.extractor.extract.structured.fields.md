# RAG STEP 95 — Extractor.extract Structured fields (RAG.facts.extractor.extract.structured.fields)

**Type:** process  
**Category:** facts  
**Node ID:** `ExtractDocFacts`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractDocFacts` (Extractor.extract Structured fields).

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
  `RAG STEP 95 (RAG.facts.extractor.extract.structured.fields): Extractor.extract Structured fields | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/services/atomic_facts_extractor.py:421 — app.services.atomic_facts_extractor.AtomicFactsExtractor.extract (score 0.32)
   Evidence: Score 0.32, Extract atomic facts from an Italian professional query.

Args:
    query: The u...
2) app/services/atomic_facts_extractor.py:581 — app.services.atomic_facts_extractor.AtomicFactsExtractor._extract_dates (score 0.25)
   Evidence: Score 0.25, Extract dates, durations, and time-related facts from the query.
3) deployment-orchestration/adaptive_deployment_engine.py:502 — deployment-orchestration.adaptive_deployment_engine.DeploymentMLOptimizer.extract_features (score 0.25)
   Evidence: Score 0.25, Extract feature vector from deployment context for ML prediction.

Features incl...
4) app/services/atomic_facts_extractor.py:24 — app.services.atomic_facts_extractor.ExtractionSpan.length (score 0.24)
   Evidence: Score 0.24, method: length
5) app/models/cassazione_data.py:180 — app.models.cassazione_data.LegalPrinciple._extract_keywords (score 0.24)
   Evidence: Score 0.24, Extract keywords from principle text.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->