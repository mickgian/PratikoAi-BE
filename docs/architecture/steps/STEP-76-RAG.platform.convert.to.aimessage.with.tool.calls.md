# RAG STEP 76 — Convert to AIMessage with tool_calls (RAG.platform.convert.to.aimessage.with.tool.calls)

**Type:** process  
**Category:** platform  
**Node ID:** `ConvertAIMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConvertAIMsg` (Convert to AIMessage with tool_calls).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/platform.py:1784` - `step_76__convert_aimsg()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator converting responses to AIMessage format with tool calls. Handles LLM responses with tool invocations for multi-step interactions.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 76 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

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