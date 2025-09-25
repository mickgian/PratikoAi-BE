# RAG STEP 72 — Get FAILOVER provider (RAG.providers.get.failover.provider)

**Type:** process  
**Category:** providers  
**Node ID:** `FailoverProvider`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FailoverProvider` (Get FAILOVER provider).

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
  `RAG STEP 72 (RAG.providers.get.failover.provider): Get FAILOVER provider | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.51

Top candidates:
1) app/core/llm/factory.py:298 — app.core.llm.factory.LLMFactory._route_failover (score 0.51)
   Evidence: Score 0.51, Route with failover logic - primary provider with fallbacks.

Args:
    provider...
2) app/orchestrators/providers.py:1201 — app.orchestrators.providers.step_72__get_failover_provider (score 0.51)
   Evidence: Score 0.51, RAG STEP 72 — Get FAILOVER provider
ID: RAG.providers.get.failover.provider
Type...
3) app/services/enhanced_query_router.py:213 — app.services.enhanced_query_router.EnhancedQueryRouter._select_llm_provider (score 0.50)
   Evidence: Score 0.50, Select optimal LLM provider based on domain-action requirements
4) app/core/llm/factory.py:367 — app.core.llm.factory.get_llm_provider (score 0.47)
   Evidence: Score 0.47, Convenience function to get an optimal LLM provider.

Args:
    messages: List o...
5) app/services/enhanced_query_router.py:46 — app.services.enhanced_query_router.EnhancedQueryRouter (score 0.47)
   Evidence: Score 0.47, Main query router that integrates classification, prompt templates,
context enri...

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->