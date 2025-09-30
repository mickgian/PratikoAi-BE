# RAG STEP 36 — LLM better than rule-based? (RAG.llm.llm.better.than.rule.based)

**Type:** decision  
**Category:** llm  
**Node ID:** `LLMBetter`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `LLMBetter` (LLM better than rule-based?).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/llm.py:14` - `step_36__llmbetter()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator comparing LLM vs rule-based classification performance and confidence scores. Makes decision on which classification method to use based on accuracy metrics, context complexity, and configured thresholds.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing LLM infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 36 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.29

Top candidates:
1) app/orchestrators/llm.py:14 — app.orchestrators.llm.step_36__llmbetter (score 0.29)
   Evidence: Score 0.29, RAG STEP 36 — LLM better than rule-based?
ID: RAG.llm.llm.better.than.rule.based...
2) app/orchestrators/platform.py:1062 — app.orchestrators.platform.step_38__use_rule_based (score 0.28)
   Evidence: Score 0.28, RAG STEP 38 — Use rule-based classification
ID: RAG.platform.use.rule.based.clas...
3) app/core/llm/factory.py:355 — app.core.llm.factory.get_llm_factory (score 0.26)
   Evidence: Score 0.26, Get the global LLM factory instance.

Returns:
    LLM factory instance
4) app/orchestrators/llm.py:179 — app.orchestrators.llm.step_37__use_llm (score 0.26)
   Evidence: Score 0.26, RAG STEP 37 — Use LLM classification
ID: RAG.llm.use.llm.classification
Type: pr...
5) app/orchestrators/llm.py:320 — app.orchestrators.llm.step_67__llmsuccess (score 0.26)
   Evidence: Score 0.26, RAG STEP 67 — LLM call successful?
ID: RAG.llm.llm.call.successful
Type: decisio...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for LLMBetter
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->