# RAG STEP 47 — Insert system message (RAG.prompting.insert.system.message)

**Type:** process  
**Category:** prompting  
**Node ID:** `InsertMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `InsertMsg` (Insert system message).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/prompting.py:768` - `step_47__insert_msg()`
- **Status:** 🔌
- **Behavior notes:** Orchestrator function inserts system message at position 0 when no system message exists and system prompt is provided

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing prompting infrastructure

## TDD Task List
- [x] Unit tests (`tests/test_rag_step_47_insert_system_message.py`)
- [x] Integration tests (parity tests proving identical behavior)
- [x] Implementation changes (orchestrator function implemented and wired)
- [x] Observability: add structured log line
  `RAG STEP 47 (RAG.prompting.insert.system.message): Insert system message | attrs={...}`
- [x] Feature flag / config if needed (none required)
- [x] Rollout plan (direct deployment - no breaking changes)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->