# RAG STEP 37 — Use LLM classification (RAG.llm.use.llm.classification)

**Type:** process  
**Category:** llm  
**Node ID:** `UseLLM`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `UseLLM` (Use LLM classification).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/llm.py:179` - `step_37__use_llm()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator using LLM-based classification when rule-based methods are insufficient. Employs advanced language models to analyze user queries and determine appropriate domain-action classifications with higher accuracy than rule-based approaches.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing LLM infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 37 (...): ... | attrs={request_id, user_id, endpoint}`
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