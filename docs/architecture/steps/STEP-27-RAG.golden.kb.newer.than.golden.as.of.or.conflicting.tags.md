# RAG STEP 27 — KB newer than Golden as of or conflicting tags? (RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags)

**Type:** process  
**Category:** golden  
**Node ID:** `KBDelta`

## Intent (Blueprint)
Evaluates whether KB has newer content or conflicting tags compared to the Golden Set match. Routes to ServeGolden (Step 28) if no conflict, or to PreContextFromGolden (Step 29) if KB has updates that should be merged.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/core/langgraph/nodes/step_027__kb_delta.py` - `node_step_27`, `app/orchestrators/golden.py:320` - `step_27__kbdelta()`
- **Status:** 🔌
- **Behavior notes:** Node orchestrator that evaluates KB delta/conflict using dual-check logic: (1) timestamp comparison for newer KB content, (2) tag-based conflict detection for supersedes/obsoletes/replaces/updated indicators. Routes to Step 28 (ServeGolden) if no delta, or Step 29 (PreContextFromGolden) if conflict detected. Preserves all context from Step 26.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - graceful degradation on missing timestamps/metadata

## TDD Task List
- [x] Unit tests (no changes→serve, newer KB→merge, conflicting tags→merge, context preservation, delta metadata, logging, missing timestamps, supersedes tag)
- [x] Parity tests (delta logic verification)
- [x] Integration tests (Step 26→27→28/29 flow, Step 27→28 context preparation)
- [x] Implementation changes (async orchestrator with timestamp + tag conflict checks)
- [x] Observability: add structured log line
  `RAG STEP 27 (RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags): KB newer than Golden as of or conflicting tags? | attrs={kb_has_delta, conflict_reason, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - uses Step 26 output)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_27
- Incoming edges: [26]
- Outgoing edges: [28]

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->