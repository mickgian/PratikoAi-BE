# RAG STEP 73 — Retry same provider (RAG.providers.retry.same.provider)

**Type:** process  
**Category:** providers  
**Node ID:** `RetrySame`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `RetrySame` (Retry same provider).

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
  `RAG STEP 73 (RAG.providers.retry.same.provider): Retry same provider | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.39

Top candidates:
1) app/core/llm/base.py:61 — app.core.llm.base.LLMProvider.__init__ (score 0.39)
   Evidence: Score 0.39, Initialize the LLM provider.

Args:
    api_key: API key for the provider
    mo...
2) app/core/llm/cost_calculator.py:141 — app.core.llm.cost_calculator.CostCalculator.calculate_cost_estimate (score 0.39)
   Evidence: Score 0.39, Calculate cost estimate for a query with a specific provider.

Args:
    provide...
3) app/core/llm/providers/anthropic_provider.py:29 — app.core.llm.providers.anthropic_provider.AnthropicProvider.__init__ (score 0.39)
   Evidence: Score 0.39, Initialize Anthropic provider.

Args:
    api_key: Anthropic API key
    model: ...
4) app/core/llm/providers/anthropic_provider.py:53 — app.core.llm.providers.anthropic_provider.AnthropicProvider.provider_type (score 0.39)
   Evidence: Score 0.39, Get the provider type.
5) app/core/llm/providers/openai_provider.py:31 — app.core.llm.providers.openai_provider.OpenAIProvider.__init__ (score 0.39)
   Evidence: Score 0.39, Initialize OpenAI provider.

Args:
    api_key: OpenAI API key
    model: Model ...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->