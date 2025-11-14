# RAG STEP 46 — Replace system message (RAG.prompting.replace.system.message)

**Type:** process  
**Category:** prompting  
**Node ID:** `ReplaceMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ReplaceMsg` (Replace system message).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/prompting.py:669` - `step_46__replace_msg()`
- **Status:** 🔌
- **Behavior notes:** Orchestrator function replaces existing system message with domain-specific prompt when classification is available

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing prompting infrastructure

## TDD Task List
- [x] Unit tests (`tests/test_rag_step_46_replace_system_message.py`)
- [x] Integration tests (parity tests proving identical behavior)
- [x] Implementation changes (orchestrator function implemented and wired)
- [x] Observability: add structured log line
  `RAG STEP 46 (RAG.prompting.replace.system.message): Replace system message | attrs={...}`
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