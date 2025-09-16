# RAG STEP 76 — Convert to AIMessage with tool_calls (RAG.platform.convert.to.aimessage.with.tool.calls)

**Type:** process  
**Category:** platform  
**Node ID:** `ConvertAIMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConvertAIMsg` (Convert to AIMessage with tool_calls).

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
  `RAG STEP 76 (RAG.platform.convert.to.aimessage.with.tool.calls): Convert to AIMessage with tool_calls | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.25

Top candidates:
1) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.25)
   Evidence: Score 0.25, Convert internal SearchResponse to API model.
2) app/models/subscription.py:127 — app.models.subscription.SubscriptionPlan.price_with_iva (score 0.25)
   Evidence: Score 0.25, Total price including 22% IVA
3) app/ragsteps/routing/step_79_rag_routing_tool_type.py:64 — app.ragsteps.routing.step_79_rag_routing_tool_type.step_79_rag_routing_tool_type (score 0.25)
   Evidence: Score 0.25, Canonical symbol for auditor: STEP 79 — Tool type? (RAG.routing.tool.type)

Dele...
4) app/services/ccnl_service.py:334 — app.services.ccnl_service.CCNLService._convert_to_db_model (score 0.25)
   Evidence: Score 0.25, Convert domain CCNL model to database model.
5) app/services/context_builder_merge.py:557 — app.services.context_builder_merge.ContextBuilderMerge._convert_to_dict (score 0.25)
   Evidence: Score 0.25, Convert MergedContext to dictionary.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ConvertAIMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->