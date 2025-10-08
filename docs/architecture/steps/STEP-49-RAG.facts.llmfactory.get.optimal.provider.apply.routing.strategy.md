
# RAG STEP 49 — LLMFactory.get_optimal_provider Apply routing strategy (RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy)

**Type:** process  
**Category:** facts  
**Node ID:** `RouteStrategy`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `RouteStrategy` (LLMFactory.get_optimal_provider Apply routing strategy).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/facts.py:427` - `step_49__route_strategy()`
- **Status:** 🔌
- **Behavior notes:** Orchestrator applying routing strategy to select optimal LLM provider. Balances cost, quality, and availability for provider selection.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (fact extraction, atomic facts processing, context building)
- [x] Integration tests (fact processing flow and context integration)
- [x] Implementation changes (async orchestrator with fact extraction, atomic facts processing, context building)
- [x] Observability: add structured log line
  `RAG STEP 49 (...): ... | attrs={fact_count, extraction_confidence, context_size}`
- [x] Feature flag / config if needed (fact extraction settings and confidence thresholds)
- [x] Rollout plan (implemented with fact extraction accuracy and context quality safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_49
- Incoming edges: [48]
- Outgoing edges: [50]

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->