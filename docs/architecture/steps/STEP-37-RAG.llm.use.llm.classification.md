# RAG STEP 37 — Use LLM classification (RAG.llm.use.llm.classification)

**Type:** process  
**Category:** llm  
**Node ID:** `UseLLM`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `UseLLM` (Use LLM classification).

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
  `RAG STEP 37 (RAG.llm.use.llm.classification): Use LLM classification | attrs={...}`
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
1) app/orchestrators/llm.py:179 — app.orchestrators.llm.step_37__use_llm (score 0.32)
   Evidence: Score 0.32, RAG STEP 37 — Use LLM classification
ID: RAG.llm.use.llm.classification
Type: pr...
2) app/core/llm/cost_calculator.py:281 — app.core.llm.cost_calculator.CostCalculator.should_use_cache (score 0.29)
   Evidence: Score 0.29, Determine if caching would be beneficial for this query.

Args:
    cost_estimat...
3) app/core/llm/factory.py:355 — app.core.llm.factory.get_llm_factory (score 0.27)
   Evidence: Score 0.27, Get the global LLM factory instance.

Returns:
    LLM factory instance
4) app/orchestrators/llm.py:14 — app.orchestrators.llm.step_36__llmbetter (score 0.27)
   Evidence: Score 0.27, RAG STEP 36 — LLM better than rule-based?
ID: RAG.llm.llm.better.than.rule.based...
5) app/orchestrators/llm.py:320 — app.orchestrators.llm.step_67__llmsuccess (score 0.27)
   Evidence: Score 0.27, RAG STEP 67 — LLM call successful?
ID: RAG.llm.llm.call.successful
Type: decisio...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->