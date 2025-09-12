# RAG STEP 36 — LLM better than rule-based? (RAG.llm.llm.better.than.rule.based)

**Type:** decision  
**Category:** llm  
**Node ID:** `LLMBetter`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `LLMBetter` (LLM better than rule-based?).

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
  `RAG STEP 36 (RAG.llm.llm.better.than.rule.based): LLM better than rule-based? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/core/llm/factory.py:355 — app.core.llm.factory.get_llm_factory (score 0.30)
   Evidence: Score 0.30, Get the global LLM factory instance.

Returns:
    LLM factory instance
2) app/core/llm/factory.py:367 — app.core.llm.factory.get_llm_provider (score 0.30)
   Evidence: Score 0.30, Convenience function to get an optimal LLM provider.

Args:
    messages: List o...
3) app/core/llm/base.py:61 — app.core.llm.base.LLMProvider.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the LLM provider.

Args:
    api_key: API key for the provider
    mo...
4) app/core/llm/base.py:75 — app.core.llm.base.LLMProvider.provider_type (score 0.30)
   Evidence: Score 0.30, Get the provider type.
5) app/core/llm/base.py:81 — app.core.llm.base.LLMProvider.supported_models (score 0.30)
   Evidence: Score 0.30, Get supported models and their cost information.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for LLMBetter
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->