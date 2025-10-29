# RAG STEP 73 — Retry same provider (RAG.providers.retry.same.provider)

**Type:** process  
**Category:** providers  
**Node ID:** `RetrySame`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `RetrySame` (Retry same provider).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/providers.py:1343` - `step_73__retry_same()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator retrying with the same provider after transient failure. Implements retry logic with backoff for resilience.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing provider infrastructure

## TDD Task List
- [x] Unit tests (provider selection, cost calculation, failover logic)
- [x] Integration tests (provider routing and failover handling)
- [x] Implementation changes (async orchestrator with provider selection, cost calculation, failover logic)
- [x] Observability: add structured log line
  `RAG STEP 73 (...): ... | attrs={provider_name, cost_estimate, routing_strategy}`
- [x] Feature flag / config if needed (provider settings and cost thresholds)
- [x] Rollout plan (implemented with provider reliability and cost optimization safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_73
- Incoming edges: [70]
- Outgoing edges: [64]

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->