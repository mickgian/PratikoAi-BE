# RAG STEP 36 — LLM better than rule-based? (RAG.llm.llm.better.than.rule.based)

**Type:** decision  
**Category:** llm  
**Node ID:** `LLMBetter`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `LLMBetter` (LLM better than rule-based?).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/llm.py:14` - `step_36__llmbetter()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator comparing LLM vs rule-based classification performance and confidence scores. Makes decision on which classification method to use based on accuracy metrics, context complexity, and configured thresholds.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing LLM infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 36 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->