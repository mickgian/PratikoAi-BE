# RAG STEP 33 — Confidence at least threshold? (RAG.classify.confidence.at.least.threshold)

**Type:** process  
**Category:** classify  
**Node ID:** `ConfidenceCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConfidenceCheck` (Confidence at least threshold?).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ✅ Implemented
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
  `RAG STEP 33 (RAG.classify.confidence.at.least.threshold): Confidence at least threshold? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.47

Top candidates:
1) app/orchestrators/classify.py:210 — app.orchestrators.classify.step_31__classify_domain (score 0.47)
   Evidence: Score 0.47, RAG STEP 31 — DomainActionClassifier.classify Rule-based classification
ID: RAG....
2) app/orchestrators/classify.py:544 — app.orchestrators.classify.step_35__llmfallback (score 0.44)
   Evidence: Score 0.44, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...
3) app/orchestrators/classify.py:433 — app.orchestrators.classify.step_33__confidence_check (score 0.44)
   Evidence: Score 0.44, RAG STEP 33 — Confidence at least threshold?
ID: RAG.classify.confidence.at.leas...
4) app/orchestrators/classify.py:317 — app.orchestrators.classify.step_32__calc_scores (score 0.44)
   Evidence: Score 0.44, RAG STEP 32 — Calculate domain and action scores Match Italian keywords
ID: RAG....
5) app/orchestrators/classify.py:677 — app.orchestrators.classify.step_35__llm_fallback (score 0.44)
   Evidence: Score 0.44, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->