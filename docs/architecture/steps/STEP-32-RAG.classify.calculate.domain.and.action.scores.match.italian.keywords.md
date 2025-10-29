# RAG STEP 32 — Calculate domain and action scores Match Italian keywords (RAG.classify.calculate.domain.and.action.scores.match.italian.keywords)

**Type:** process  
**Category:** classify  
**Node ID:** `CalcScores`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CalcScores` (Calculate domain and action scores Match Italian keywords).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/classify.py:317` - `step_32__calc_scores()`
- **Role:** Internal
- **Status:** 🔌
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing classification infrastructure

## TDD Task List
- [x] Unit tests (classification logic, domain/action scoring, Italian keywords)
- [x] Integration tests (classification flow and domain routing)
- [x] Implementation changes (async orchestrator with classification logic, domain/action scoring, Italian keywords)
- [x] Observability: add structured log line
  `RAG STEP 32 (...): ... | attrs={domain, action, confidence_score}`
- [x] Feature flag / config if needed (classification thresholds and keyword mappings)
- [x] Rollout plan (implemented with classification accuracy and performance safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->