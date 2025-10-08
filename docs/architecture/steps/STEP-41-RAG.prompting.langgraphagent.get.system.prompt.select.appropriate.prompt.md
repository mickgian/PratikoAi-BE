# RAG STEP 41 — LangGraphAgent._get_system_prompt Select appropriate prompt (RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt)

**Type:** process  
**Category:** prompting  
**Node ID:** `SelectPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `SelectPrompt` (LangGraphAgent._get_system_prompt Select appropriate prompt).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/prompting.py:211` - `step_41__select_prompt()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator selecting appropriate system prompt using PromptTemplateManager. Routes to Step 42 (ClassConfidence) to check classification confidence for domain-specific prompts.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing prompting infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 41 (...): ... | attrs={request_id, user_id, endpoint}`
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