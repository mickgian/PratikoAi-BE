# RAG STEP 54 — Use primary provider (RAG.providers.use.primary.provider)

**Type:** process  
**Category:** providers  
**Node ID:** `PrimaryProvider`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PrimaryProvider` (Use primary provider).

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
  `RAG STEP 54 (RAG.providers.use.primary.provider): Use primary provider | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/core/llm/providers/anthropic_provider.py:29 — app.core.llm.providers.anthropic_provider.AnthropicProvider.__init__ (score 0.31)
   Evidence: Score 0.31, Initialize Anthropic provider.

Args:
    api_key: Anthropic API key
    model: ...
2) app/core/llm/providers/anthropic_provider.py:46 — app.core.llm.providers.anthropic_provider.AnthropicProvider.client (score 0.31)
   Evidence: Score 0.31, Get the Anthropic async client.
3) app/core/llm/providers/anthropic_provider.py:53 — app.core.llm.providers.anthropic_provider.AnthropicProvider.provider_type (score 0.31)
   Evidence: Score 0.31, Get the provider type.
4) app/core/llm/providers/anthropic_provider.py:58 — app.core.llm.providers.anthropic_provider.AnthropicProvider.supported_models (score 0.31)
   Evidence: Score 0.31, Get supported Anthropic models and their cost information.

Costs are in EUR per...
5) app/core/llm/providers/anthropic_provider.py:85 — app.core.llm.providers.anthropic_provider.AnthropicProvider._convert_messages_to_anthropic (score 0.31)
   Evidence: Score 0.31, Convert messages to Anthropic format.

Args:
    messages: List of Message objec...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->