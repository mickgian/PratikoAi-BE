# RAG STEP 55 — CostCalculator.estimate_cost Calculate query cost (RAG.providers.costcalculator.estimate.cost.calculate.query.cost)

**Type:** process  
**Category:** providers  
**Node ID:** `EstimateCost`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `EstimateCost` (CostCalculator.estimate_cost Calculate query cost).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/providers.py:635` - `step_55__estimate_cost()`
- **Status:** ✅
- **Behavior notes:** Orchestrator calculating estimated query costs for LLM providers. Analyzes token counts, provider pricing, and query complexity to provide cost estimates before execution.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing provider infrastructure

## TDD Task List
- [x] Unit tests (provider selection, cost calculation, failover logic)
- [x] Integration tests (provider routing and failover handling)
- [x] Implementation changes (async orchestrator with provider selection, cost calculation, failover logic)
- [x] Observability: add structured log line
  `RAG STEP 55 (...): ... | attrs={provider_name, cost_estimate, routing_strategy}`
- [x] Feature flag / config if needed (provider settings and cost thresholds)
- [x] Rollout plan (implemented with provider reliability and cost optimization safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_55
- Incoming edges: [51, 52, 53, 54, 58]
- Outgoing edges: [56]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->