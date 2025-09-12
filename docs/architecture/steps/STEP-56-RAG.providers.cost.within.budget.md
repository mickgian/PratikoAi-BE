# RAG STEP 56 — Cost within budget? (RAG.providers.cost.within.budget)

**Type:** decision  
**Category:** providers  
**Node ID:** `CostCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CostCheck` (Cost within budget?).

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
  `RAG STEP 56 (RAG.providers.cost.within.budget): Cost within budget? | attrs={...}`
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
1) app/core/llm/cost_calculator.py:34 — app.core.llm.cost_calculator.CostCalculator.__init__ (score 0.26)
   Evidence: Score 0.26, Initialize cost calculator.
2) app/core/llm/cost_calculator.py:51 — app.core.llm.cost_calculator.CostCalculator.classify_query_complexity (score 0.26)
   Evidence: Score 0.26, Classify the complexity of a query based on content analysis.

Args:
    message...
3) app/core/llm/cost_calculator.py:106 — app.core.llm.cost_calculator.CostCalculator.estimate_output_tokens (score 0.26)
   Evidence: Score 0.26, Estimate output tokens based on input and complexity.

Args:
    input_tokens: N...
4) app/core/llm/cost_calculator.py:141 — app.core.llm.cost_calculator.CostCalculator.calculate_cost_estimate (score 0.26)
   Evidence: Score 0.26, Calculate cost estimate for a query with a specific provider.

Args:
    provide...
5) app/core/llm/cost_calculator.py:176 — app.core.llm.cost_calculator.CostCalculator.find_optimal_provider (score 0.26)
   Evidence: Score 0.26, Find the optimal provider based on cost and capability requirements.

Args:
    ...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for CostCheck
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->