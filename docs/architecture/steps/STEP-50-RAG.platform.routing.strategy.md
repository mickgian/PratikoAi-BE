# RAG STEP 50 — Routing strategy? (RAG.platform.routing.strategy)

**Type:** decision  
**Category:** platform  
**Node ID:** `StrategyType`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `StrategyType` (Routing strategy?).

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
  `RAG STEP 50 (RAG.platform.routing.strategy): Routing strategy? | attrs={...}`
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
1) app/ragsteps/routing/step_79_rag_routing_tool_type.py:64 — app.ragsteps.routing.step_79_rag_routing_tool_type.step_79_rag_routing_tool_type (score 0.30)
   Evidence: Score 0.30, Canonical symbol for auditor: STEP 79 — Tool type? (RAG.routing.tool.type)

Dele...
2) app/ragsteps/routing/step_79_rag_routing_tool_type.py:35 — app.ragsteps.routing.step_79_rag_routing_tool_type.run (score 0.29)
   Evidence: Score 0.29, Adapter for RAG STEP 79: Tool type?

Expected behavior is defined in:
docs/archi...
3) app/core/langgraph/graph.py:343 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.28)
   Evidence: Score 0.28, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
4) app/schemas/privacy.py:191 — app.schemas.privacy.validate_consent_type (score 0.26)
   Evidence: Score 0.26, Validate consent type string.
5) app/schemas/privacy.py:221 — app.schemas.privacy.validate_pii_type (score 0.26)
   Evidence: Score 0.26, Validate PII type string.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for StrategyType
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->