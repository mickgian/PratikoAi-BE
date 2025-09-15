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
Status: ❌  |  Confidence: 0.22

Top candidates:
1) app/core/langgraph/graph.py:463 — app.core.langgraph.graph.LangGraphAgent._get_optimal_provider (score 0.22)
   Evidence: Score 0.22, Get the optimal LLM provider for the given messages.

Args:
    messages: List o...
2) app/core/llm/cost_calculator.py:176 — app.core.llm.cost_calculator.CostCalculator.find_optimal_provider (score 0.20)
   Evidence: Score 0.20, Find the optimal provider based on cost and capability requirements.

Args:
    ...
3) failure-recovery-system/decision_tree_engine.py:207 — failure-recovery-system.decision_tree_engine.RecoveryStrategy.__post_init__ (score 0.20)
   Evidence: Score 0.20, method: __post_init__
4) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.19)
   Evidence: Score 0.19, Convert internal SearchResponse to API model.
5) app/api/v1/data_export.py:69 — app.api.v1.data_export.CreateExportRequest.validate_future_dates (score 0.19)
   Evidence: Score 0.19, method: validate_future_dates

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for RouteStrategy
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->