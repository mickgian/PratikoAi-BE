# RAG STEP 58 — Select cheaper provider or fail (RAG.providers.select.cheaper.provider.or.fail)

**Type:** process  
**Category:** providers  
**Node ID:** `CheaperProvider`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CheaperProvider` (Select cheaper provider or fail).

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
  `RAG STEP 58 (RAG.providers.select.cheaper.provider.or.fail): Select cheaper provider or fail | attrs={...}`
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
1) app/core/llm/factory.py:298 — app.core.llm.factory.LLMFactory._route_failover (score 0.47)
   Evidence: Score 0.47, Route with failover logic - primary provider with fallbacks.

Args:
    provider...
2) app/core/llm/factory.py:367 — app.core.llm.factory.get_llm_provider (score 0.43)
   Evidence: Score 0.43, Convenience function to get an optimal LLM provider.

Args:
    messages: List o...
3) app/core/llm/base.py:61 — app.core.llm.base.LLMProvider.__init__ (score 0.43)
   Evidence: Score 0.43, Initialize the LLM provider.

Args:
    api_key: API key for the provider
    mo...
4) app/core/llm/cost_calculator.py:141 — app.core.llm.cost_calculator.CostCalculator.calculate_cost_estimate (score 0.43)
   Evidence: Score 0.43, Calculate cost estimate for a query with a specific provider.

Args:
    provide...
5) app/core/llm/factory.py:59 — app.core.llm.factory.LLMFactory.create_provider (score 0.43)
   Evidence: Score 0.43, Create an LLM provider instance.

Args:
    provider_type: Type of provider to c...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->