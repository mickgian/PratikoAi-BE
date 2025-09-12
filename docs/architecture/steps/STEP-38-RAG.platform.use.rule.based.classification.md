# RAG STEP 38 — Use rule-based classification (RAG.platform.use.rule.based.classification)

**Type:** process  
**Category:** platform  
**Node ID:** `UseRuleBased`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `UseRuleBased` (Use rule-based classification).

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
  `RAG STEP 38 (RAG.platform.use.rule.based.classification): Use rule-based classification | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.26

Top candidates:
1) app/core/llm/base.py:61 — app.core.llm.base.LLMProvider.__init__ (score 0.26)
   Evidence: Score 0.26, Initialize the LLM provider.

Args:
    api_key: API key for the provider
    mo...
2) app/core/llm/base.py:75 — app.core.llm.base.LLMProvider.provider_type (score 0.26)
   Evidence: Score 0.26, Get the provider type.
3) app/core/llm/base.py:81 — app.core.llm.base.LLMProvider.supported_models (score 0.26)
   Evidence: Score 0.26, Get supported models and their cost information.
4) app/core/llm/base.py:132 — app.core.llm.base.LLMProvider.estimate_tokens (score 0.26)
   Evidence: Score 0.26, Estimate token count for a list of messages.

Args:
    messages: List of conver...
5) app/core/llm/base.py:144 — app.core.llm.base.LLMProvider.estimate_cost (score 0.26)
   Evidence: Score 0.26, Estimate cost for given token counts.

Args:
    input_tokens: Number of input t...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for UseRuleBased
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->