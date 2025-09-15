# RAG STEP 49 — LLMFactory.get_optimal_provider Apply routing strategy (RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy)

**Type:** process  
**Category:** facts  
**Node ID:** `RouteStrategy`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `RouteStrategy` (LLMFactory.get_optimal_provider Apply routing strategy).

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
  `RAG STEP 49 (RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy): LLMFactory.get_optimal_provider Apply routing strategy | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.35

Top candidates:
1) app/core/llm/factory.py:127 — app.core.llm.factory.LLMFactory.get_optimal_provider (score 0.35)
   Evidence: Score 0.35, Get the optimal provider based on routing strategy.

Args:
    messages: List of...
2) app/core/llm/factory.py:27 — app.core.llm.factory.LLMFactory.__init__ (score 0.31)
   Evidence: Score 0.31, Initialize the LLM factory.
3) app/core/llm/factory.py:33 — app.core.llm.factory.LLMFactory._get_provider_configs (score 0.31)
   Evidence: Score 0.31, Get provider configurations from settings.

Returns:
    Dictionary of provider ...
4) app/core/llm/factory.py:59 — app.core.llm.factory.LLMFactory.create_provider (score 0.31)
   Evidence: Score 0.31, Create an LLM provider instance.

Args:
    provider_type: Type of provider to c...
5) app/core/llm/factory.py:105 — app.core.llm.factory.LLMFactory.get_available_providers (score 0.31)
   Evidence: Score 0.31, Get all available configured providers.

Returns:
    List of available provider...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->