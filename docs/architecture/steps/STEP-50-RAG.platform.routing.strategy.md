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
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/platform.py:1201 — app.orchestrators.platform.step_50__strategy_type (score 0.31)
   Evidence: Score 0.31, RAG STEP 50 — Routing strategy?
ID: RAG.platform.routing.strategy
Type: decision...
2) app/orchestrators/routing.py:14 — app.orchestrators.routing.step_79__tool_type (score 0.31)
   Evidence: Score 0.31, RAG STEP 79 — Tool type?
ID: RAG.routing.tool.type
Type: decision | Category: ro...
3) app/core/langgraph/graph.py:343 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.28)
   Evidence: Score 0.28, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
4) app/api/v1/data_sources.py:256 — app.api.v1.data_sources.get_sources_by_type (score 0.26)
   Evidence: Score 0.26, Get all data sources of a specific type.

Available types:
- government: Officia...
5) app/orchestrators/docs.py:313 — app.orchestrators.docs.step_89__doc_type (score 0.26)
   Evidence: Score 0.26, RAG STEP 89 — Document type?
ID: RAG.docs.document.type
Type: decision | Categor...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->