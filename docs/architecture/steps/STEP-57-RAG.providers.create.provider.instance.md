# RAG STEP 57 — Create provider instance (RAG.providers.create.provider.instance)

**Type:** process  
**Category:** providers  
**Node ID:** `CreateProvider`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CreateProvider` (Create provider instance).

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
  `RAG STEP 57 (RAG.providers.create.provider.instance): Create provider instance | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.50

Top candidates:
1) app/core/llm/factory.py:298 — app.core.llm.factory.LLMFactory._route_failover (score 0.50)
   Evidence: Score 0.50, Route with failover logic - primary provider with fallbacks.

Args:
    provider...
2) app/services/enhanced_query_router.py:213 — app.services.enhanced_query_router.EnhancedQueryRouter._select_llm_provider (score 0.49)
   Evidence: Score 0.49, Select optimal LLM provider based on domain-action requirements
3) app/services/enhanced_query_router.py:46 — app.services.enhanced_query_router.EnhancedQueryRouter (score 0.46)
   Evidence: Score 0.46, Main query router that integrates classification, prompt templates,
context enri...
4) app/ragsteps/providers/step_48_rag_providers_langgraphagent_get_optimal_provider_select_llm_provider.py:54 — app.ragsteps.providers.step_48_rag_providers_langgraphagent_get_optimal_provider_select_llm_provider.select_optimal_provider (score 0.45)
   Evidence: Score 0.45, Select optimal LLM provider based on context and constraints (STEP 48).
5) app/ragsteps/providers/step_48_rag_providers_langgraphagent_get_optimal_provider_select_llm_provider.py:29 — app.ragsteps.providers.step_48_rag_providers_langgraphagent_get_optimal_provider_select_llm_provider.run (score 0.45)
   Evidence: Score 0.45, Adapter for RAG STEP 48: Select LLM provider.

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->