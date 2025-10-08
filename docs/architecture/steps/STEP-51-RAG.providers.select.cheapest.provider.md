# RAG STEP 51 — Select cheapest provider (RAG.providers.select.cheapest.provider)

**Type:** process  
**Category:** providers  
**Node ID:** `CheapProvider`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CheapProvider` (Select cheapest provider).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/providers.py:128` - `step_51__cheap_provider()`
- **Status:** 🔌
- **Behavior notes:** Orchestrator selecting the cheapest available LLM provider based on cost analysis. Optimizes for minimal API costs while maintaining acceptable quality thresholds.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing provider infrastructure

## TDD Task List
- [x] Unit tests (provider selection, cost calculation, failover logic)
- [x] Integration tests (provider routing and failover handling)
- [x] Implementation changes (async orchestrator with provider selection, cost calculation, failover logic)
- [x] Observability: add structured log line
  `RAG STEP 51 (...): ... | attrs={provider_name, cost_estimate, routing_strategy}`
- [x] Feature flag / config if needed (provider settings and cost thresholds)
- [x] Rollout plan (implemented with provider reliability and cost optimization safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_51
- Incoming edges: [50]
- Outgoing edges: [55]

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->