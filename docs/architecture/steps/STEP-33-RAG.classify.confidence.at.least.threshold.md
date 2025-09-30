# RAG STEP 33 — Confidence at least threshold? (RAG.classify.confidence.at.least.threshold)

**Type:** process  
**Category:** classify  
**Node ID:** `ConfidenceCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConfidenceCheck` (Confidence at least threshold?).

## Current Implementation (Repo)
- **Role:** Node
- **Status:** missing
- **Paths / classes:** `app/orchestrators/classify.py:433` - `step_33__confidence_check()`
- **Behavior notes:** Runtime boundary; validates classification confidence against thresholds; routes to step 34 or fallback.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing classification infrastructure

## TDD Task List
- [x] Unit tests (classification logic, domain/action scoring, Italian keywords)
- [x] Integration tests (classification flow and domain routing)
- [x] Implementation changes (async orchestrator with classification logic, domain/action scoring, Italian keywords)
- [x] Observability: add structured log line
  `RAG STEP 33 (...): ... | attrs={domain, action, confidence_score}`
- [x] Feature flag / config if needed (classification thresholds and keyword mappings)
- [x] Rollout plan (implemented with classification accuracy and performance safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: missing  |  Confidence: 0.47

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